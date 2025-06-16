from typing import Dict, Any
from .base import StorageBackend
from .s3 import S3Storage
from .gdrive import GoogleDriveStorage
from .ftp import FTPStorage

class StorageFactory:
    """Factory para crear instancias de backends de almacenamiento."""
    
    @staticmethod
    def create_storage(storage_type: str, config: Dict[str, Any]) -> StorageBackend:
        """Crea una instancia del backend de almacenamiento especificado.
        
        Args:
            storage_type: Tipo de almacenamiento ('s3', 'gdrive', 'ftp')
            config: Configuración del backend
            
        Returns:
            StorageBackend: Instancia del backend de almacenamiento
            
        Raises:
            ValueError: Si el tipo de almacenamiento no es válido
        """
        storage_map = {
            's3': S3Storage,
            'gdrive': GoogleDriveStorage,
            'ftp': FTPStorage
        }
        
        if storage_type not in storage_map:
            raise ValueError(f"Tipo de almacenamiento no válido: {storage_type}")
        
        return storage_map[storage_type](config) 