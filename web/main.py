from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="RepoMirror Web",
    description="Interfaz web para gestionar respaldos de repositorios de GitHub",
    version="1.0.0"
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class Repository(BaseModel):
    name: str
    url: str
    last_backup: Optional[str] = None
    status: str = "pending"

class BackupConfig(BaseModel):
    storage_type: str
    destination: str
    schedule: Optional[str] = None

# Rutas API
@app.get("/")
async def root():
    return {"message": "Bienvenido a RepoMirror Web"}

@app.get("/repositories", response_model=List[Repository])
async def get_repositories():
    # TODO: Implementar obtención de repositorios
    return [
        Repository(
            name="ejemplo-repo",
            url="https://github.com/usuario/ejemplo-repo",
            status="active"
        )
    ]

@app.post("/backup")
async def create_backup(repo_url: str, config: BackupConfig):
    # TODO: Implementar lógica de respaldo
    return {"message": "Respaldo iniciado", "repo": repo_url}

@app.get("/status/{backup_id}")
async def get_backup_status(backup_id: str):
    # TODO: Implementar verificación de estado
    return {"status": "in_progress", "progress": 50}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 