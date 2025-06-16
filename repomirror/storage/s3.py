import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Dict, Any, Optional, List
import aiofiles
import asyncio
from datetime import datetime

from .base import StorageBackend

class S3Storage(StorageBackend):
    """Implementación del backend de almacenamiento para Amazon S3."""
    
    def _validate_config(self) -> None:
        """Valida la configuración de S3."""
        required_keys = ['access_key', 'secret_key', 'bucket', 'region']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Falta la configuración requerida: {key}")
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.config['access_key'],
            aws_secret_access_key=self.config['secret_key'],
            region_name=self.config['region']
        )
        self.bucket = self.config['bucket']
    
    async def upload_file(self, file_path: Path, destination: str) -> str:
        """Sube un archivo a S3."""
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
                
            # Ejecutar la subida en un thread pool para no bloquear
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.put_object(
                    Bucket=self.bucket,
                    Key=destination,
                    Body=content
                )
            )
            
            return f"s3://{self.bucket}/{destination}"
        except Exception as e:
            raise Exception(f"Error al subir archivo a S3: {str(e)}")
    
    async def download_file(self, file_id: str, destination: Path) -> Path:
        """Descarga un archivo de S3."""
        try:
            # Extraer la clave del archivo de la URL S3
            key = file_id.replace(f"s3://{self.bucket}/", "")
            
            # Crear el directorio de destino si no existe
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Descargar el archivo
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.download_file(
                    self.bucket,
                    key,
                    str(destination)
                )
            )
            
            return destination
        except Exception as e:
            raise Exception(f"Error al descargar archivo de S3: {str(e)}")
    
    async def delete_file(self, file_id: str) -> bool:
        """Elimina un archivo de S3."""
        try:
            key = file_id.replace(f"s3://{self.bucket}/", "")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.s3_client.delete_object(
                    Bucket=self.bucket,
                    Key=key
                )
            )
            return True
        except Exception as e:
            raise Exception(f"Error al eliminar archivo de S3: {str(e)}")
    
    async def list_files(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista los archivos en S3."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.list_objects_v2(
                    Bucket=self.bucket,
                    Prefix=prefix
                )
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'url': f"s3://{self.bucket}/{obj['Key']}"
                })
            
            return files
        except Exception as e:
            raise Exception(f"Error al listar archivos de S3: {str(e)}")
    
    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Obtiene información de un archivo en S3."""
        try:
            key = file_id.replace(f"s3://{self.bucket}/", "")
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.s3_client.head_object(
                    Bucket=self.bucket,
                    Key=key
                )
            )
            
            return {
                'key': key,
                'size': response['ContentLength'],
                'last_modified': response['LastModified'].isoformat(),
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'url': f"s3://{self.bucket}/{key}"
            }
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundError(f"Archivo no encontrado: {file_id}")
            raise Exception(f"Error al obtener información del archivo de S3: {str(e)}") 