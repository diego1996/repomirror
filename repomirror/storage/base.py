from abc import ABC, abstractmethod
from typing import BinaryIO, Optional, Dict, Any
from pathlib import Path

class StorageBackend(ABC):
    """Clase base abstracta para todos los backends de almacenamiento."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._validate_config()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Valida la configuración del backend."""
        pass
    
    @abstractmethod
    async def upload_file(self, file_path: Path, destination: str) -> str:
        """Sube un archivo al almacenamiento.
        
        Args:
            file_path: Ruta local del archivo a subir
            destination: Ruta de destino en el almacenamiento
            
        Returns:
            str: URL o identificador del archivo subido
        """
        pass
    
    @abstractmethod
    async def download_file(self, file_id: str, destination: Path) -> Path:
        """Descarga un archivo del almacenamiento.
        
        Args:
            file_id: Identificador del archivo en el almacenamiento
            destination: Ruta local donde guardar el archivo
            
        Returns:
            Path: Ruta del archivo descargado
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """Elimina un archivo del almacenamiento.
        
        Args:
            file_id: Identificador del archivo a eliminar
            
        Returns:
            bool: True si se eliminó correctamente
        """
        pass
    
    @abstractmethod
    async def list_files(self, prefix: Optional[str] = None) -> list:
        """Lista los archivos en el almacenamiento.
        
        Args:
            prefix: Prefijo opcional para filtrar archivos
            
        Returns:
            list: Lista de archivos encontrados
        """
        pass
    
    @abstractmethod
    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """Obtiene información de un archivo.
        
        Args:
            file_id: Identificador del archivo
            
        Returns:
            Dict[str, Any]: Información del archivo
        """
        pass 