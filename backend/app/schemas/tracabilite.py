from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.tracabilite import ActionEnum

class TracabiliteBase(BaseModel):
    table_cible: str
    id_enregistrement: int
    action: ActionEnum
    id_utilisateur: int
    date_action: datetime
    anciennes_valeurs: Optional[dict] = None
    nouvelles_valeurs: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    description: Optional[str] = None

class TracabiliteCreate(TracabiliteBase):
    pass

class TracabiliteResponse(TracabiliteBase):
    id_trace: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TracabiliteFilter(BaseModel):
    """Filtres pour recherche dans les logs"""
    table_cible: Optional[str] = None
    id_enregistrement: Optional[int] = None
    action: Optional[ActionEnum] = None
    id_utilisateur: Optional[int] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
