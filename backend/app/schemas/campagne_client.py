from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.campagne_client import StatutEnvoiEnum

class CampagneClientBase(BaseModel):
    id_campagne: int
    id_dossier: int
    canal: Optional[str] = None

class CampagneClientCreate(CampagneClientBase):
    pass

class CampagneClientUpdate(BaseModel):
    statut: Optional[StatutEnvoiEnum] = None
    date_envoi: Optional[datetime] = None
    date_delivre: Optional[datetime] = None
    date_ouvert: Optional[datetime] = None
    date_clique: Optional[datetime] = None
    canal: Optional[str] = None

class CampagneClientResponse(CampagneClientBase):
    id: int
    statut: StatutEnvoiEnum
    date_envoi: Optional[datetime] = None
    date_delivre: Optional[datetime] = None
    date_ouvert: Optional[datetime] = None
    date_clique: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
