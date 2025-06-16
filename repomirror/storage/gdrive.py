from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from pathlib import Path
from typing import Dict, Any, Optional, List
import io
import os
import pickle
import aiofiles
import asyncio

from .base import StorageBackend

class GoogleDriveStorage(StorageBackend):
    """Implementación del backend de almacenamiento para Google Drive."""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def _validate_config(self) -> None:
        """Valida la configuración de Google Drive."""
        required_keys = ['credentials_file', 'token_file']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Falta la configuración requerida: {key}")
        
        self.credentials_file = self.config['credentials_file']
        self.token_file = self.config['token_file']
        self.service = self._get_service()
    
    def _get_service(self):
        """Obtiene el servicio de Google Drive."""
        creds = None
        
        # Cargar credenciales existentes
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # Si no hay credenciales válidas, obtener nuevas
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Guardar las credenciales
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)
    
    async def upload_file(self, file_path: Path, destination: str) -> str:
        """Sube un archivo a Google Drive."""
        try:
            file_metadata = {
                'name': destination,
                'mimeType': 'application/zip'
            }
            
            media = MediaFileUpload(
                str(file_path),
                mimetype='application/zip',
                resumable=True
            )
            
            loop = asyncio.get_event_loop()
            file = await loop.run_in_executor(
                None,
                lambda: self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
            )
            
            return file.get('id')
        except Exception as e:
            raise Exception(f"Error al subir archivo a Google Drive: {str(e)}")
    
    async def download_file(self, file_id: str, destination: Path) -> Path:
        """Descarga un archivo de Google Drive."""
        try:
            request = self.service.files().get_media(fileId=file_id)
            
            # Crear el directorio de destino si no existe
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            loop = asyncio.get_event_loop()
            done = False
            while not done:
                status, done = await loop.run_in_executor(
                    None,
                    lambda: downloader.next_chunk()
                )
            
            # Guardar el archivo
            fh.seek(0)
            async with aiofiles.open(destination, 'wb') as f:
                await f.write(fh.read())
            
            return destination
        except Exception as e:
            raise Exception(f"Error al descargar archivo de Google Drive: {str(e)}")
    
    async def delete_file(self, file_id: str) -> bool:
        """Elimina un archivo de Google Drive."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.service.files().delete(fileId=file_id).execute()
            )
            return True
        except Exception as e:
            raise Exception(f"Error al eliminar archivo de Google Drive: {str(e)}")
    
    async def list_files(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista los archivos en Google Drive."""
        try:
            query = f"name contains '{prefix}'" if prefix else None
            
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.service.files().list(
                    q=query,
                    pageSize=100,
                    fields="nextPageToken, files(id, name, size, modifiedTime)"
                ).execute()
            )
            
            files = []
            for item in results.get('files', []):
                files.append({
                    'id': item['id'],
                    'name': item['name'],
                    'size': item.get('size', 0),
                    'modified_time': item.get('modifiedTime'),
                    'url': f"https://drive.google.com/file/d/{item['id']}/view"
                })
            
            return files
        except Exception as e:
            raise Exception(f"Error al listar archivos de Google Drive: {str(e)}")
    
    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Obtiene información de un archivo en Google Drive."""
        try:
            loop = asyncio.get_event_loop()
            file = await loop.run_in_executor(
                None,
                lambda: self.service.files().get(
                    fileId=file_id,
                    fields="id, name, size, mimeType, modifiedTime"
                ).execute()
            )
            
            return {
                'id': file['id'],
                'name': file['name'],
                'size': file.get('size', 0),
                'mime_type': file.get('mimeType', 'application/octet-stream'),
                'modified_time': file.get('modifiedTime'),
                'url': f"https://drive.google.com/file/d/{file['id']}/view"
            }
        except Exception as e:
            raise Exception(f"Error al obtener información del archivo de Google Drive: {str(e)}") 