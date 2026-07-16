from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import csv
import io

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.utilisateur import Utilisateur
from app.models.dossier_client import DossierClient
from app.models.client import Client
from app.models.scoring import Scoring, NiveauRisqueEnum
from app.schemas.Scoring import (
    ScoreResult,
    DossierScoreOut,
    DossierScoreListResponse,
    DashboardStats,
    RecalculateResponse,
)
from app.services import scoring_service

router = APIRouter()


def _latest_scoring_subquery(db: Session):
    """Sous-requête : date_calcul la plus récente par dossier."""
    return (
        db.query(
            Scoring.id_dossier,
            func.max(Scoring.date_calcul).label("latest_date"),
        )
        .group_by(Scoring.id_dossier)
        .subquery()
    )


def _latest_scorings_query(db: Session):
    """Query retournant, pour chaque dossier scoré, uniquement son Scoring le plus récent."""
    latest = _latest_scoring_subquery(db)
    return db.query(Scoring).join(
        latest,
        (Scoring.id_dossier == latest.c.id_dossier) & (Scoring.date_calcul == latest.c.latest_date),
    )


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Statistiques agrégées pour les 4 cartes du tableau de bord scoring."""
    latest_scorings = _latest_scorings_query(db).all()
    total = len(latest_scorings)
    meta = scoring_service.get_model_meta()

    if total == 0:
        return DashboardStats(
            score_moyen_global=0,
            montant_sous_risque=0,
            profils_critiques=0,
            recouvrement_predit_pct=0,
            total_dossiers=0,
            modele=meta["nom"],
            seuil_decision=meta["seuil"],
        )

    score_moyen = sum(s.score_risque for s in latest_scorings) / total
    critiques = [s for s in latest_scorings if s.niveau_risque == NiveauRisqueEnum.CRITIQUE]

    montant_sous_risque = 0.0
    for s in critiques:
        dossier = db.query(DossierClient).filter(DossierClient.id_dossier == s.id_dossier).first()
        if dossier:
            montant_sous_risque += float(dossier.montant_total_du or 0)

    recouvrement_predit = sum(s.probabilite_recouvrement for s in latest_scorings) / total * 100

    return DashboardStats(
        score_moyen_global=round(score_moyen, 1),
        montant_sous_risque=round(montant_sous_risque, 2),
        profils_critiques=len(critiques),
        recouvrement_predit_pct=round(recouvrement_predit, 1),
        total_dossiers=total,
        modele=meta["nom"],
        seuil_decision=meta["seuil"],
    )


@router.get("/dossiers", response_model=DossierScoreListResponse)
def get_dossiers_scores(
    niveau: Optional[str] = Query(None, description="Faible | Moyen | Eleve | Critique"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Liste paginée des dossiers avec leur dernier score, filtrable par niveau de risque."""
    query = _latest_scorings_query(db)

    if niveau:
        try:
            niveau_enum = NiveauRisqueEnum(niveau)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Niveau invalide: {niveau}")
        query = query.filter(Scoring.niveau_risque == niveau_enum)

    total = query.count()
    scorings = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for s in scorings:
        dossier = db.query(DossierClient).filter(DossierClient.id_dossier == s.id_dossier).first()
        if not dossier:
            continue
        client = db.query(Client).filter(Client.id_client == dossier.id_client).first()
        creance = max(dossier.creances, key=lambda c: c.jours_retard or 0) if dossier.creances else None

        items.append(
            DossierScoreOut(
                id_dossier=dossier.id_dossier,
                numero_dossier=dossier.numero_dossier,
                nom_client=f"{client.nom} {client.prenom}" if client else "—",
                montant_du=float(dossier.montant_total_du or 0),
                jours_retard=int(creance.jours_retard) if creance and creance.jours_retard else 0,
                score_risque=s.score_risque,
                niveau_risque=s.niveau_risque.value,
                probabilite_recouvrement=s.probabilite_recouvrement,
                date_calcul=s.date_calcul,
            )
        )

    return DossierScoreListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/recalculate", response_model=RecalculateResponse)
def recalculate_scores(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Recalcule le score de tous les dossiers actifs — crée un nouvel enregistrement Scoring par dossier."""
    count, duration = scoring_service.recalculate_all(db)
    return RecalculateResponse(dossiers_scores=count, duree_secondes=duration)


@router.get("/dossiers/{dossier_id}/predict", response_model=ScoreResult)
def predict_dossier(
    dossier_id: int,
    persist: bool = Query(False, description="Si true, enregistre le résultat dans scorings"),
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Score un dossier précis à la demande."""
    dossier = db.query(DossierClient).filter(DossierClient.id_dossier == dossier_id).first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    result = scoring_service.score_dossier(db, dossier, persist=persist)
    if result is None:
        raise HTTPException(status_code=422, detail="Aucune créance active sur ce dossier — rien à scorer")

    if persist:
        db.commit()

    return ScoreResult(
        id_dossier=result["id_dossier"],
        score_risque=result["score_risque"],
        niveau_risque=result["niveau_risque"].value,
        probabilite_recouvrement=result["probabilite_recouvrement"],
        facteurs_cles=result["facteurs_cles"],
    )


@router.get("/export")
def export_scores_csv(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Export CSV du dernier score de chaque dossier."""
    scorings = _latest_scorings_query(db).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "id_dossier", "numero_dossier", "score_risque", "niveau_risque",
        "probabilite_recouvrement", "date_calcul",
    ])
    for s in scorings:
        dossier = db.query(DossierClient).filter(DossierClient.id_dossier == s.id_dossier).first()
        writer.writerow([
            s.id_dossier,
            dossier.numero_dossier if dossier else "",
            s.score_risque,
            s.niveau_risque.value,
            s.probabilite_recouvrement,
            s.date_calcul,
        ])
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=scoring_export.csv"},
    )