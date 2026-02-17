from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class AgenceBase(BaseModel):
    nom_agence: str
    code_agence: str
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[EmailStr] = None
    id_region: int

class AgenceCreate(AgenceBase):
    pass

class AgenceUpdate(BaseModel):
    nom_agence: Optional[str] = None
    code_agence: Optional[str] = None
    adresse: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[EmailStr] = None
    id_region: Optional[int] = None

class AgenceResponse(AgenceBase):
    id_agence: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AgenceWithStats(AgenceResponse):
    nombre_utilisateurs: int
    nombre_dossiers: int