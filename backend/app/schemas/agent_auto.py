from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.agent_auto import TypeAgentEnum, StatutAgentEnum

class AgentAutoBase(BaseModel):
    nom_agent: str
    type: TypeAgentEnum
    capacite_max: int = 100
    configuration: Optional[dict] = None

class AgentAutoCreate(AgentAutoBase):
    pass

class AgentAutoUpdate(BaseModel):
    nom_agent: Optional[str] = None
    type: Optional[TypeAgentEnum] = None
    statut: Optional[StatutAgentEnum] = None
    capacite_max: Optional[int] = None
    configuration: Optional[dict] = None

class AgentAutoResponse(AgentAutoBase):
    id_agent: int
    statut: StatutAgentEnum
    messages_traites: int
    date_dernier_run: Optional[datetime] = None
    date_prochain_run: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AgentAutoStats(BaseModel):
    """Statistiques d'un agent"""
    id_agent: int
    nom_agent: str
    type: str
    statut: str
    messages_traites: int
    capacite_max: int
    taux_utilisation: float
    date_dernier_run: Optional[datetime] = None
