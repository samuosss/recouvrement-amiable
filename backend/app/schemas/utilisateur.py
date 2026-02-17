from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.utilisateur import RoleEnum

class UtilisateurBase(BaseModel):
    nom: str
    prenom: str
    email: EmailStr
    role: RoleEnum
    telephone: Optional[str] = None
    id_agence: Optional[int] = None
    actif: bool = True

class UtilisateurCreate(UtilisateurBase):
    mot_de_passe: str

class UtilisateurUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[EmailStr] = None
    telephone: Optional[str] = None
    role: Optional[RoleEnum] = None
    id_agence: Optional[int] = None
    actif: Optional[bool] = None
    mot_de_passe: Optional[str] = None

class UtilisateurResponse(UtilisateurBase):
    id_utilisateur: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class UtilisateurLogin(BaseModel):
    email: EmailStr
    mot_de_passe: str