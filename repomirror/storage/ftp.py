from ftplib import FTP
from pathlib import Path
from typing import Dict, Any, Optional, List
import aiofiles
import asyncio
from datetime import datetime
import os

from .base import StorageBackend

class FTPStorage(StorageBackend):
    """Implementación del backend de almacenamiento para FTP."""
    
    def _validate_config(self) -> None:
        """Valida la configuración de FTP."""
        required_keys = ['host', 'username', 'password', 'port', 'path']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Falta la configuración requerida: {key}")
        
        self.host = self.config['host']
        self.username = self.config['username']
        self.password = self.config['password']
        self.port = self.config['port']
        self.base_path = self.config['path']
    
    def _get_ftp_connection(self) -> FTP:
        """Obtiene una conexión FTP."""
        ftp = FTP()
        ftp.connect(self.host, self.port)
        ftp.login(self.username, self.password)
        return ftp
    
    async def upload_file(self, file_path: Path, destination: str) -> str:
        """Sube un archivo al servidor FTP."""
        try:
            # Construir la ruta completa
            remote_path = os.path.join(self.base_path, destination)
            remote_dir = os.path.dirname(remote_path)
            
            loop = asyncio.get_event_loop()
            ftp = await loop.run_in_executor(None, self._get_ftp_connection)
            
            # Crear directorios si no existen
            try:
                await loop.run_in_executor(None, lambda: ftp.mkd(remote_dir))
            except:
                pass  # El directorio ya existe
            
            # Cambiar al directorio
            await loop.run_in_executor(None, lambda: ftp.cwd(remote_dir))
            
            # Subir el archivo
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
                
            await loop.run_in_executor(
                None,
                lambda: ftp.storbinary(f'STOR {os.path.basename(remote_path)}', io.BytesIO(content))
            )
            
            # Cerrar la conexión
            await loop.run_in_executor(None, ftp.quit)
            
            return remote_path
        except Exception as e:
            raise Exception(f"Error al subir archivo a FTP: {str(e)}")
    
    async def download_file(self, file_id: str, destination: Path) -> Path:
        """Descarga un archivo del servidor FTP."""
        try:
            # Crear el directorio de destino si no existe
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            loop = asyncio.get_event_loop()
            ftp = await loop.run_in_executor(None, self._get_ftp_connection)
            
            # Cambiar al directorio del archivo
            remote_dir = os.path.dirname(file_id)
            await loop.run_in_executor(None, lambda: ftp.cwd(remote_dir))
            
            # Descargar el archivo
            with open(destination, 'wb') as f:
                await loop.run_in_executor(
                    None,
                    lambda: ftp.retrbinary(f'RETR {os.path.basename(file_id)}', f.write)
                )
            
            # Cerrar la conexión
            await loop.run_in_executor(None, ftp.quit)
            
            return destination
        except Exception as e:
            raise Exception(f"Error al descargar archivo de FTP: {str(e)}")
    
    async def delete_file(self, file_id: str) -> bool:
        """Elimina un archivo del servidor FTP."""
        try:
            loop = asyncio.get_event_loop()
            ftp = await loop.run_in_executor(None, self._get_ftp_connection)
            
            # Cambiar al directorio del archivo
            remote_dir = os.path.dirname(file_id)
            await loop.run_in_executor(None, lambda: ftp.cwd(remote_dir))
            
            # Eliminar el archivo
            await loop.run_in_executor(
                None,
                lambda: ftp.delete(os.path.basename(file_id))
            )
            
            # Cerrar la conexión
            await loop.run_in_executor(None, ftp.quit)
            
            return True
        except Exception as e:
            raise Exception(f"Error al eliminar archivo de FTP: {str(e)}")
    
    async def list_files(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista los archivos en el servidor FTP."""
        try:
            loop = asyncio.get_event_loop()
            ftp = await loop.run_in_executor(None, self._get_ftp_connection)
            
            # Cambiar al directorio base
            await loop.run_in_executor(None, lambda: ftp.cwd(self.base_path))
            
            # Obtener lista de archivos
            files = []
            def process_line(line):
                parts = line.split()
                if len(parts) >= 9:
                    filename = ' '.join(parts[8:])
                    if not prefix or filename.startswith(prefix):
                        files.append({
                            'name': filename,
                            'size': int(parts[4]),
                            'modified_time': f"{parts[5]} {parts[6]} {parts[7]}",
                            'url': f"ftp://{self.host}{os.path.join(self.base_path, filename)}"
                        })
            
            await loop.run_in_executor(
                None,
                lambda: ftp.retrlines('LIST', process_line)
            )
            
            # Cerrar la conexión
            await loop.run_in_executor(None, ftp.quit)
            
            return files
        except Exception as e:
            raise Exception(f"Error al listar archivos de FTP: {str(e)}")
    
    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Obtiene información de un archivo en el servidor FTP."""
        try:
            loop = asyncio.get_event_loop()
            ftp = await loop.run_in_executor(None, self._get_ftp_connection)
            
            # Cambiar al directorio del archivo
            remote_dir = os.path.dirname(file_id)
            await loop.run_in_executor(None, lambda: ftp.cwd(remote_dir))
            
            # Obtener información del archivo
            filename = os.path.basename(file_id)
            size = await loop.run_in_executor(
                None,
                lambda: ftp.size(filename)
            )
            
            # Obtener fecha de modificación
            mdtm = await loop.run_in_executor(
                None,
                lambda: ftp.sendcmd(f'MDTM {filename}')
            )
            modified_time = mdtm.split()[1]
            
            # Cerrar la conexión
            await loop.run_in_executor(None, ftp.quit)
            
            return {
                'name': filename,
                'size': size,
                'modified_time': modified_time,
                'url': f"ftp://{self.host}{file_id}"
            }
        except Exception as e:
            raise Exception(f"Error al obtener información del archivo de FTP: {str(e)}") 