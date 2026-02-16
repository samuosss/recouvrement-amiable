from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TypeInteractionEnum(str, Enum):
    APPEL = "Appel"
    EMAIL = "Email"
    SMS = "SMS"
    VISITE = "Visite"
    COURRIER = "Courrier"
    AUTRE = "Autre"

class InteractionBase(BaseModel):
    type: TypeInteractionEnum
    date_interaction: datetime
    duree_minutes: Optional[int] = None
    resultat: Optional[str] = None
    notes: Optional[str] = None
    promesse_paiement: bool = False
    montant_promis: Optional[float] = None
    date_promesse: Optional[datetime] = None
    id_dossier: int
    id_agent: int

class InteractionCreate(InteractionBase):
    pass

class InteractionUpdate(BaseModel):
    type: Optional[TypeInteractionEnum] = None
    date_interaction: Optional[datetime] = None
    duree_minutes: Optional[int] = None
    resultat: Optional[str] = None
    notes: Optional[str] = None
    promesse_paiement: Optional[bool] = None
    montant_promis: Optional[float] = None
    date_promesse: Optional[datetime] = None

class InteractionInDB(InteractionBase):
    id_interaction: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class InteractionResponse(InteractionInDB):
    pass

class InteractionStats(BaseModel):
    total_interactions: int
    interactions_succes: int
    taux_succes: float
    promesses_paiement: int
    montant_total_promis: float