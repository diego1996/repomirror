import boto3
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from ftplib import FTP
import logging
from models import db, Backup
import json
import pickle
import tempfile
import shutil
from datetime import datetime, timedelta

class StorageService:
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.s3_client = None
        self.gdrive_service = None
        self.ftp_client = None
        self._initialize_clients()

    def _initialize_clients(self):
        """
        Inicializa los clientes de almacenamiento según la configuración.
        """
        # Inicializar S3
        if 's3' in self.config:
            try:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=self.config['s3']['access_key'],
                    aws_secret_access_key=self.config['s3']['secret_key'],
                    region_name=self.config['s3']['region']
                )
            except Exception as e:
                self.logger.warning(f'No se pudo inicializar el cliente S3: {e}. Se omite inicialización de S3.')
                self.s3_client = None

        # Inicializar Google Drive
        if 'gdrive' in self.config:
            self._initialize_gdrive()

        # Inicializar FTP
        if 'ftp' in self.config:
            try:
                self.ftp_client = FTP()
                self.ftp_client.connect(
                    host=self.config['ftp']['host'],
                    port=self.config['ftp'].get('port', 21)
                )
                self.ftp_client.login(
                    user=self.config['ftp']['username'],
                    passwd=self.config['ftp']['password']
                )
            except Exception as e:
                self.logger.warning(f'No se pudo inicializar el cliente FTP: {e}. Se omite inicialización de FTP.')
                self.ftp_client = None

    def _initialize_gdrive(self):
        """
        Inicializa el cliente de Google Drive, pero ignora si faltan credenciales.
        """
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        creds = None
        cred_file = self.config['gdrive'].get('credentials_file', 'credentials.json')
        token_file = self.config['gdrive'].get('token_file', 'token.json')

        # Verificar existencia de archivos
        if not os.path.exists(cred_file):
            self.logger.warning(f'Archivo de credenciales de Google Drive no encontrado: {cred_file}. Se omite inicialización de Google Drive.')
            return
        if not os.path.exists(token_file):
            self.logger.warning(f'Archivo de token de Google Drive no encontrado: {token_file}. Se intentará obtener uno nuevo si es posible.')

        # Cargar credenciales existentes
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)

        # Si no hay credenciales válidas, obtener nuevas
        if not creds or not creds.valid:
            try:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    from google_auth_oauthlib.flow import InstalledAppFlow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        cred_file,
                        SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Guardar credenciales
                with open(token_file, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                self.logger.warning(f'No se pudo obtener credenciales de Google Drive: {e}. Se omite inicialización de Google Drive.')
                return

        try:
            self.gdrive_service = build('drive', 'v3', credentials=creds)
        except Exception as e:
            self.logger.warning(f'No se pudo inicializar el cliente de Google Drive: {e}. Se omite inicialización de Google Drive.')
            self.gdrive_service = None

    def upload_backup(self, backup_id, storage_type):
        """
        Sube un backup al almacenamiento especificado.
        
        Args:
            backup_id: ID del backup
            storage_type: Tipo de almacenamiento (s3, gdrive, ftp)
        """
        backup = Backup.query.get(backup_id)
        if not backup:
            raise ValueError(f'Backup {backup_id} no encontrado')

        try:
            if storage_type == 's3':
                self._upload_to_s3(backup)
            elif storage_type == 'gdrive':
                self._upload_to_gdrive(backup)
            elif storage_type == 'ftp':
                self._upload_to_ftp(backup)
            else:
                raise ValueError(f'Tipo de almacenamiento no soportado: {storage_type}')

            backup.status = 'completed'
            backup.storage_path = self._get_storage_path(backup, storage_type)
            db.session.commit()

        except Exception as e:
            self.logger.error(f'Error uploading backup {backup_id}: {str(e)}')
            backup.status = 'error'
            backup.error_message = str(e)
            db.session.commit()
            raise

    def _upload_to_s3(self, backup):
        """
        Sube un backup a Amazon S3.
        
        Args:
            backup: Objeto Backup
        """
        if not self.s3_client:
            raise ValueError('Cliente S3 no inicializado')

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Comprimir el backup
            shutil.make_archive(temp_file.name, 'zip', backup.local_path)
            
            # Subir a S3
            self.s3_client.upload_file(
                f'{temp_file.name}.zip',
                self.config['s3']['bucket'],
                f'backups/{backup.id}.zip'
            )

        # Limpiar archivos temporales
        os.unlink(temp_file.name)
        os.unlink(f'{temp_file.name}.zip')

    def _upload_to_gdrive(self, backup):
        """
        Sube un backup a Google Drive.
        
        Args:
            backup: Objeto Backup
        """
        if not self.gdrive_service:
            raise ValueError('Cliente Google Drive no inicializado')

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Comprimir el backup
            shutil.make_archive(temp_file.name, 'zip', backup.local_path)
            
            # Crear metadatos del archivo
            file_metadata = {
                'name': f'backup_{backup.id}.zip',
                'mimeType': 'application/zip'
            }
            
            # Subir a Google Drive
            media = MediaFileUpload(
                f'{temp_file.name}.zip',
                mimetype='application/zip',
                resumable=True
            )
            
            file = self.gdrive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

        # Limpiar archivos temporales
        os.unlink(temp_file.name)
        os.unlink(f'{temp_file.name}.zip')

    def _upload_to_ftp(self, backup):
        """
        Sube un backup a un servidor FTP.
        
        Args:
            backup: Objeto Backup
        """
        if not self.ftp_client:
            raise ValueError('Cliente FTP no inicializado')

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Comprimir el backup
            shutil.make_archive(temp_file.name, 'zip', backup.local_path)
            
            # Subir a FTP
            with open(f'{temp_file.name}.zip', 'rb') as file:
                self.ftp_client.storbinary(
                    f'STOR {self.config["ftp"]["path"]}/backup_{backup.id}.zip',
                    file
                )

        # Limpiar archivos temporales
        os.unlink(temp_file.name)
        os.unlink(f'{temp_file.name}.zip')

    def _get_storage_path(self, backup, storage_type):
        """
        Obtiene la ruta de almacenamiento para un backup.
        
        Args:
            backup: Objeto Backup
            storage_type: Tipo de almacenamiento
        """
        if storage_type == 's3':
            return f's3://{self.config["s3"]["bucket"]}/backups/{backup.id}.zip'
        elif storage_type == 'gdrive':
            return f'gdrive://backup_{backup.id}.zip'
        elif storage_type == 'ftp':
            return f'ftp://{self.config["ftp"]["host"]}{self.config["ftp"]["path"]}/backup_{backup.id}.zip'
        return None

    def get_total_storage_used(self, user_id):
        """
        Obtiene el total de almacenamiento usado por un usuario.
        
        Args:
            user_id: ID del usuario
        """
        total_size = 0
        
        # Obtener todos los backups del usuario
        backups = Backup.query.join(Repository).filter(
            Repository.user_id == user_id,
            Backup.status == 'completed'
        ).all()
        
        for backup in backups:
            if backup.storage_type == 's3':
                try:
                    response = self.s3_client.head_object(
                        Bucket=self.config['s3']['bucket'],
                        Key=f'backups/{backup.id}.zip'
                    )
                    total_size += response['ContentLength']
                except:
                    continue
            elif backup.storage_type == 'gdrive':
                try:
                    file = self.gdrive_service.files().get(
                        fileId=backup.storage_path.split('/')[-1],
                        fields='size'
                    ).execute()
                    total_size += int(file.get('size', 0))
                except:
                    continue
            elif backup.storage_type == 'ftp':
                try:
                    size = self.ftp_client.size(
                        f'{self.config["ftp"]["path"]}/backup_{backup.id}.zip'
                    )
                    total_size += int(size)
                except:
                    continue
        
        return total_size

    def cleanup_old_backups(self, days=30):
        """
        Limpia los backups antiguos.
        
        Args:
            days: Número de días después de los cuales eliminar backups
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        old_backups = Backup.query.filter(
            Backup.created_at < cutoff_date
        ).all()
        
        for backup in old_backups:
            try:
                if backup.storage_type == 's3':
                    self.s3_client.delete_object(
                        Bucket=self.config['s3']['bucket'],
                        Key=f'backups/{backup.id}.zip'
                    )
                elif backup.storage_type == 'gdrive':
                    self.gdrive_service.files().delete(
                        fileId=backup.storage_path.split('/')[-1]
                    ).execute()
                elif backup.storage_type == 'ftp':
                    self.ftp_client.delete(
                        f'{self.config["ftp"]["path"]}/backup_{backup.id}.zip'
                    )
                
                # Eliminar backup de la base de datos
                db.session.delete(backup)
            except Exception as e:
                self.logger.error(f'Error cleaning up backup {backup.id}: {str(e)}')
        
        db.session.commit() 