from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional

class ClientBase(BaseModel):
    cin: str = Field(..., min_length=8, max_length=20)
    nom: str = Field(..., min_length=2, max_length=100)
    prenom: str = Field(..., min_length=2, max_length=100)
    telephone: str = Field(..., min_length=8, max_length=20)
    email: Optional[EmailStr] = None
    adresse: Optional[str] = None
    ville: Optional[str] = None
    code_postal: Optional[str] = None
    date_naissance: Optional[date] = None
    profession: Optional[str] = None
    situation_familiale: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[EmailStr] = None
    adresse: Optional[str] = None
    ville: Optional[str] = None
    profession: Optional[str] = None

class ClientResponse(ClientBase):
    id_client: int
    
    class Config:
        from_attributes = True
