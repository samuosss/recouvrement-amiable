from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class ScoreResult(BaseModel):
    """Résultat d'un scoring individuel (ad-hoc, non persisté)."""
    id_dossier: int
    score_risque: int  # 0-100
    niveau_risque: str  # "Faible" | "Moyen" | "Eleve" | "Critique"
    probabilite_recouvrement: float
    facteurs_cles: dict[str, Any]


class DossierScoreOut(BaseModel):
    """Ligne de dossier enrichie de son dernier score, pour le tableau de bord."""
    id_dossier: int
    numero_dossier: str
    nom_client: str
    montant_du: float
    jours_retard: int
    score_risque: Optional[int] = None
    niveau_risque: Optional[str] = None
    probabilite_recouvrement: Optional[float] = None
    date_calcul: Optional[datetime] = None

    class Config:
        from_attributes = True


class DossierScoreListResponse(BaseModel):
    items: list[DossierScoreOut]
    total: int
    page: int
    page_size: int


class DashboardStats(BaseModel):
    score_moyen_global: float
    montant_sous_risque: float
    profils_critiques: int
    recouvrement_predit_pct: float
    total_dossiers: int
    modele: str
    seuil_decision: float


class RecalculateResponse(BaseModel):
    dossiers_scores: int
    duree_secondes: float