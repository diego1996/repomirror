import os
import tempfile
import shutil
import logging
from git import Repo
from github import Github
from models import db, Backup
import subprocess
import json

class GitHubService:
    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.github_client = Github(config.get('token'))
        self.temp_dir = tempfile.mkdtemp()

    def clone_repository(self, repo_url, backup_id):
        """
        Clona un repositorio de GitHub.
        
        Args:
            repo_url: URL del repositorio
            backup_id: ID del backup
        """
        backup = Backup.query.get(backup_id)
        if not backup:
            raise ValueError(f'Backup {backup_id} no encontrado')

        try:
            # Crear directorio para el backup
            backup_dir = os.path.join(self.temp_dir, str(backup_id))
            os.makedirs(backup_dir, exist_ok=True)

            # Clonar repositorio
            if 'github.com' in repo_url:
                # Repositorio público
                repo = Repo.clone_from(repo_url, backup_dir)
            else:
                # Repositorio privado
                repo = Repo.clone_from(
                    repo_url.replace('https://', f'https://{self.config["token"]}@'),
                    backup_dir
                )

            # Obtener información del repositorio
            repo_info = self._get_repo_info(repo_url)
            
            # Actualizar backup
            backup.local_path = backup_dir
            backup.repo_info = json.dumps(repo_info)
            backup.status = 'cloned'
            db.session.commit()

            return backup_dir

        except Exception as e:
            self.logger.error(f'Error cloning repository {repo_url}: {str(e)}')
            backup.status = 'error'
            backup.error_message = str(e)
            db.session.commit()
            raise

    def _get_repo_info(self, repo_url):
        """
        Obtiene información de un repositorio de GitHub.
        
        Args:
            repo_url: URL del repositorio
        """
        try:
            # Extraer owner y repo de la URL
            parts = repo_url.rstrip('/').split('/')
            owner = parts[-2]
            repo_name = parts[-1].replace('.git', '')

            # Obtener información del repositorio
            repo = self.github_client.get_repo(f'{owner}/{repo_name}')
            
            return {
                'name': repo.name,
                'full_name': repo.full_name,
                'description': repo.description,
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'language': repo.language,
                'size': repo.size,
                'default_branch': repo.default_branch,
                'created_at': repo.created_at.isoformat(),
                'updated_at': repo.updated_at.isoformat()
            }
        except Exception as e:
            self.logger.warning(f'Error getting repo info: {str(e)}')
            return {}

    def cleanup_temp_files(self):
        """
        Limpia los archivos temporales.
        """
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            self.logger.error(f'Error cleaning up temp files: {str(e)}')

    def __del__(self):
        """
        Limpia los archivos temporales al destruir el objeto.
        """
        self.cleanup_temp_files() 