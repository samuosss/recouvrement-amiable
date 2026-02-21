from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.utilisateur import RoleEnum

class Token(BaseModel):
    """Réponse contenant les tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Données extraites du token"""
    user_id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[RoleEnum] = None

class LoginRequest(BaseModel):
    """Requête de connexion"""
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    """Requête de rafraîchissement du token"""
    refresh_token: str

class UserProfile(BaseModel):
    """Profil utilisateur retourné après login"""
    id_utilisateur: int
    nom: str
    prenom: str
    email: EmailStr
    role: RoleEnum
    id_agence: Optional[int] = None
    actif: bool
    
    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    """Réponse complète du login"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserProfile