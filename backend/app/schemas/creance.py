from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

# Enums qui correspondent EXACTEMENT à la DB
class StatutCreanceEnum(str, Enum):
    EN_COURS = "EnCours"
    REGLE = "Regle"
    PARTIELLEMENT_REGLE = "PartiellementRegle"
    EN_LITIGE = "EnLitige"
    IRRECUPERABLE = "Irrecuperable"

class TypeCreditEnum(str, Enum):
    PRET_PERSONNEL = "PretPersonnel"
    CREDIT_AUTO = "CreditAuto"
    CREDIT_IMMOBILIER = "CreditImmobilier"
    CREDIT_CONSOMMATION = "CreditConsommation"
    AUTRE = "Autre"

class CreanceBase(BaseModel):
    numero_contrat: str  # CHANGÉ: reference → numero_contrat
    type_credit: str  # CHANGÉ: type_creance → type_credit
    montant_initial: float  # CHANGÉ: montant → montant_initial
    montant_restant: float  # NOUVEAU
    montant_paye: float = 0.0
    date_echeance: date
    date_debut_retard: Optional[date] = None  # NOUVEAU
    jours_retard: int = 0  # NOUVEAU
    taux_interet: Optional[float] = None
    penalites: float = 0.0  # NOUVEAU
    statut: StatutCreanceEnum = StatutCreanceEnum.EN_COURS  # CHANGÉ: valeurs des enums
    id_dossier: int  # CHANGÉ: dossier_id → id_dossier

class CreanceCreate(CreanceBase):
    pass

class CreanceUpdate(BaseModel):
    numero_contrat: Optional[str] = None
    type_credit: Optional[str] = None
    montant_initial: Optional[float] = None
    montant_restant: Optional[float] = None
    montant_paye: Optional[float] = None
    date_echeance: Optional[date] = None
    date_debut_retard: Optional[date] = None
    jours_retard: Optional[int] = None
    taux_interet: Optional[float] = None
    penalites: Optional[float] = None
    statut: Optional[StatutCreanceEnum] = None

class CreanceInDB(CreanceBase):
    id_creance: int  # CHANGÉ: id → id_creance
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CreanceResponse(CreanceInDB):
    pass

class CreanceSummary(BaseModel):
    nombre_creances: int
    total_impayees: float
    total_payees: float
    total_en_retard: float