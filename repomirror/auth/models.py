from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Modelo base para usuarios."""
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False

class UserCreate(UserBase):
    """Modelo para crear usuarios."""
    password: str

class UserUpdate(UserBase):
    """Modelo para actualizar usuarios."""
    password: Optional[str] = None

class UserInDB(UserBase):
    """Modelo para usuarios en la base de datos."""
    id: int
    hashed_password: str
    created_at: datetime
    updated_at: datetime

class User(UserBase):
    """Modelo para usuarios en la API."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class Token(BaseModel):
    """Modelo para tokens de acceso."""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """Modelo para datos del token."""
    email: Optional[str] = None 