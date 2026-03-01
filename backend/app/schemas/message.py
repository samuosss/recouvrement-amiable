from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.message import TypeMessageEnum, StatutMessageEnum

class MessageBase(BaseModel):
    id_campagne_client: Optional[int] = None
    id_dossier: int
    type: TypeMessageEnum
    destinataire: str
    sujet: Optional[str] = None
    contenu: str
    id_agent_auto: Optional[int] = None

class MessageCreate(MessageBase):
    pass

class MessageUpdate(BaseModel):
    statut: Optional[StatutMessageEnum] = None
    date_envoi: Optional[datetime] = None
    date_delivre: Optional[datetime] = None
    code_erreur: Optional[str] = None
    message_erreur: Optional[str] = None

class MessageResponse(MessageBase):
    id_message: int
    statut: StatutMessageEnum
    date_envoi: Optional[datetime] = None
    date_delivre: Optional[datetime] = None
    code_erreur: Optional[str] = None
    message_erreur: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
