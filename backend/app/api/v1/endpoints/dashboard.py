from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from typing import List

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import filter_dossiers_by_role
from app.models.dossier_client import DossierClient, StatutDossierEnum
from app.models.creance import Creance, StatutCreanceEnum
from app.models.client import Client
from app.models.utilisateur import Utilisateur
from app.schemas.dashboard import DashboardStats, MonthlyPerformance, StatutDistribution

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    KPIs + charts data for the dashboard.
    All figures are scoped to what the current user can access.
    """

    # ── Dossiers accessibles ──────────────────────────────────────────────────
    dossiers_q = db.query(DossierClient)
    dossiers_q = filter_dossiers_by_role(dossiers_q, current_user, db)

    accessible_ids = [d.id_dossier for d in dossiers_q.with_entities(DossierClient.id_dossier).all()]

    # ── KPI: dossiers ─────────────────────────────────────────────────────────
    total_dossiers  = len(accessible_ids)
    dossiers_actifs = dossiers_q.filter(DossierClient.statut == StatutDossierEnum.ACTIF).count()

    # ── KPI: créances ─────────────────────────────────────────────────────────
    creances_q = db.query(Creance).filter(Creance.id_dossier.in_(accessible_ids))

    montant_total_du = db.query(
        func.coalesce(func.sum(Creance.montant_restant), 0)
    ).filter(Creance.id_dossier.in_(accessible_ids)).scalar() or 0

    montant_recouvre = db.query(
        func.coalesce(func.sum(Creance.montant_paye), 0)
    ).filter(Creance.id_dossier.in_(accessible_ids)).scalar() or 0

    taux_recouvrement = (
        float(montant_recouvre) / float(montant_recouvre + montant_total_du) * 100
        if (montant_recouvre + montant_total_du) > 0 else 0
    )

    # ── KPI: clients ──────────────────────────────────────────────────────────
    total_clients = db.query(
        func.count(func.distinct(DossierClient.id_client))
    ).filter(DossierClient.id_dossier.in_(accessible_ids)).scalar() or 0

    # ── Monthly performance (last 6 months) ───────────────────────────────────
    monthly: List[MonthlyPerformance] = []
    now = datetime.now()
    month_names = ["Jan","Fév","Mar","Avr","Mai","Juin","Juil","Aoû","Sep","Oct","Nov","Déc"]

    for i in range(5, -1, -1):
        target_date = now - timedelta(days=30 * i)
        m = target_date.month
        y = target_date.year

        recouvre = db.query(
            func.coalesce(func.sum(Creance.montant_paye), 0)
        ).join(DossierClient, Creance.id_dossier == DossierClient.id_dossier).filter(
            Creance.id_dossier.in_(accessible_ids),
            extract("month", DossierClient.date_ouverture) == m,
            extract("year",  DossierClient.date_ouverture) == y,
        ).scalar() or 0

        # Simple target: total_du / 6 per month — adjust to your own logic
        objectif = float(montant_total_du + montant_recouvre) / 6

        monthly.append(MonthlyPerformance(
            month=month_names[m - 1],
            recouvre=float(recouvre),
            objectif=round(objectif, 2),
        ))

    # ── Status distribution ───────────────────────────────────────────────────
    statut_counts = db.query(
        DossierClient.statut,
        func.count(DossierClient.id_dossier).label("count")
    ).filter(
        DossierClient.id_dossier.in_(accessible_ids)
    ).group_by(DossierClient.statut).all()

    COLOR_MAP = {
        StatutDossierEnum.ACTIF:      "#a4c639",
        StatutDossierEnum.CLOTURE:    "#7cc49c",
        StatutDossierEnum.SUSPENDU:   "#f59e0b",
        StatutDossierEnum.EN_LITIGE:  "#dc2626",
    }
    LABEL_MAP = {
        StatutDossierEnum.ACTIF:      "Actif",
        StatutDossierEnum.CLOTURE:    "Clôturé",
        StatutDossierEnum.SUSPENDU:   "Suspendu",
        StatutDossierEnum.EN_LITIGE:  "En litige",
    }

    status_distribution = [
        StatutDistribution(
            name=LABEL_MAP.get(row.statut, row.statut),
            value=row.count,
            color=COLOR_MAP.get(row.statut, "#94a3b8"),
        )
        for row in statut_counts
    ]

    return DashboardStats(
        total_dossiers=total_dossiers,
        dossiers_actifs=dossiers_actifs,
        total_clients=total_clients,
        montant_total_du=float(montant_total_du),
        montant_recouvre=float(montant_recouvre),
        taux_recouvrement=round(taux_recouvrement, 1),
        monthly_performance=monthly,
        status_distribution=status_distribution,
    )