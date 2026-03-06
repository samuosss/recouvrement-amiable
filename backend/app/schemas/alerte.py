from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.alerte import TypeAlerteEnum, NiveauAlerteEnum

class AlerteBase(BaseModel):
    id_dossier: Optional[int] = None
    id_utilisateur: Optional[int] = None
    type: TypeAlerteEnum
    niveau: NiveauAlerteEnum
    titre: str
    message: str

class AlerteCreate(AlerteBase):
    pass

class AlerteUpdate(BaseModel):
    lue: Optional[bool] = None
    traitee: Optional[bool] = None

class AlerteResponse(AlerteBase):
    id_alerte: int
    date_creation: datetime
    lue: bool
    date_lecture: Optional[datetime] = None
    traitee: bool
    date_traitement: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AlerteStats(BaseModel):
    """Statistiques des alertes"""
    total_alertes: int
    non_lues: int
    non_traitees: int
    par_niveau: dict
    par_type: dict
