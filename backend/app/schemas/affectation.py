from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AffectationBase(BaseModel):
    id_dossier: int
    id_agent: int
    id_assigneur: int
    motif: Optional[str] = None
    actif: bool = True

class AffectationCreate(AffectationBase):
    date_affectation: datetime = None
    
    def __init__(self, **data):
        if 'date_affectation' not in data:
            data['date_affectation'] = datetime.now()
        super().__init__(**data)

class AffectationUpdate(BaseModel):
    motif: Optional[str] = None
    actif: Optional[bool] = None
    date_fin: Optional[datetime] = None

class AffectationResponse(AffectationBase):
    id_affectation: int
    date_affectation: datetime
    date_fin: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AffectationDetailResponse(AffectationResponse):
    """Réponse détaillée avec infos agent et dossier"""
    agent_nom: Optional[str] = None
    agent_prenom: Optional[str] = None
    assigneur_nom: Optional[str] = None
    assigneur_prenom: Optional[str] = None
    dossier_numero: Optional[str] = None
    client_nom: Optional[str] = None

class ReaffectationRequest(BaseModel):
    """Requête de réaffectation d'un dossier"""
    id_dossier: int
    id_nouvel_agent: int
    id_assigneur: int
    motif: str