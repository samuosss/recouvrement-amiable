from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Enums qui correspondent EXACTEMENT à vos données DB
class StatutDossier(str, Enum):
    ACTIF = "Actif"
    EN_COURS = "En cours"
    CLOTURE = "Clôturé"
    ARCHIVE = "Archivé"

class PrioriteDossier(str, Enum):
    CRITIQUE = "Critique"
    HAUTE = "Haute"
    NORMALE = "Normale"
    BASSE = "Basse"

class DossierBase(BaseModel):
    numero_dossier: str
    statut: StatutDossier
    priorite: PrioriteDossier
    montant_total_du: Optional[float] = None  # CHANGÉ: montant_total → montant_total_du
    notes: Optional[str] = None
    id_client: int  # CHANGÉ: client_id → id_client
    # agent_id n'existe pas dans votre DB apparemment

class DossierCreate(DossierBase):
    pass

class DossierUpdate(BaseModel):
    numero_dossier: Optional[str] = None
    statut: Optional[StatutDossier] = None
    priorite: Optional[PrioriteDossier] = None
    montant_total_du: Optional[float] = None
    notes: Optional[str] = None
    date_derniere_action: Optional[datetime] = None

class DossierInDB(DossierBase):
    id_dossier: int  # CHANGÉ: id → id_dossier
    date_ouverture: datetime
    date_derniere_action: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DossierResponse(DossierInDB):
    pass

class DossierStats(BaseModel):
    dossier_id: int
    nombre_creances: int
    nombre_interactions: int
    montant_total_creances: float
    montant_total_paye: float
    solde_restant: float
    taux_recouvrement: float