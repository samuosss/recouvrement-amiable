from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.campagne import TypeCampagneEnum, StatutCampagneEnum

class CampagneBase(BaseModel):
    nom_campagne: str
    description: Optional[str] = None
    type: TypeCampagneEnum
    id_template: Optional[int] = None
    date_debut: datetime
    date_fin: Optional[datetime] = None
    criteres_segmentation: dict  # JSON avec critères

class CampagneCreate(CampagneBase):
    pass

class CampagneUpdate(BaseModel):
    nom_campagne: Optional[str] = None
    description: Optional[str] = None
    type: Optional[TypeCampagneEnum] = None
    id_template: Optional[int] = None
    date_debut: Optional[datetime] = None
    date_fin: Optional[datetime] = None
    criteres_segmentation: Optional[dict] = None
    statut: Optional[StatutCampagneEnum] = None

class CampagneResponse(CampagneBase):
    id_campagne: int
    statut: StatutCampagneEnum
    nombre_cibles: int
    nombre_envoyes: int
    nombre_delivres: int
    nombre_ouverts: int
    nombre_cliques: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class CampagneStats(BaseModel):
    id_campagne: int
    nom_campagne: str
    total_cibles: int
    envoyes: int
    delivres: int
    ouverts: int
    cliques: int
    taux_delivrance: float
    taux_ouverture: float
    taux_clic: float
