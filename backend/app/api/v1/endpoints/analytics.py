"""
routers/analytics.py — Endpoints analytiques pour le dashboard Analyses

GET /analytics/portefeuille/secteur  ← répartition par type_credit (créances)
GET /analytics/portefeuille/region   ← répartition par région (agences)
GET /analytics/portefeuille/aging    ← ancienneté des créances (jours_retard)
GET /analytics/portefeuille/summary  ← KPI globaux (en-cours, taux, débiteurs)
"""

from __future__ import annotations

from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import filter_dossiers_by_role
from app.models.creance import Creance, StatutCreanceEnum
from app.models.dossier_client import DossierClient, StatutDossierEnum
from app.models.client import Client
from app.models.agence import Agence
from app.models.region import Region
from app.models.utilisateur import Utilisateur
from app.models.affectation_dossier import AffectationDossier

router = APIRouter()


# ─── Helper : IDs dossiers accessibles ───────────────────────────────────────

def _dossier_ids(db: Session, current_user: Utilisateur) -> List[int]:
    q = db.query(DossierClient.id_dossier)
    q = filter_dossiers_by_role(q, current_user, db)
    return [row[0] for row in q.distinct().all()]


# ═══════════════════════════════════════════════════════════════════════════════
# KPI GLOBAUX
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/portefeuille/summary")
def get_portefeuille_summary(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    KPI globaux du portefeuille accessible à l'utilisateur.
    Retourne : total_encours, taux_recouvrement, nb_debiteurs_actifs, risque_moyen.
    """
    ids = _dossier_ids(db, current_user)
    if not ids:
        return {
            "total_encours": 0,
            "montant_recouvre": 0,
            "taux_recouvrement": 0,
            "nb_debiteurs_actifs": 0,
            "risque_moyen": "Faible",
        }

    # Montants créances
    agg = (
        db.query(
            func.sum(Creance.montant_initial).label("initial"),
            func.sum(Creance.montant_paye).label("paye"),
            func.sum(Creance.montant_restant).label("restant"),
        )
        .filter(Creance.id_dossier.in_(ids))
        .first()
    )
    total_initial = float(agg.initial or 0)
    total_paye    = float(agg.paye    or 0)
    total_restant = float(agg.restant or 0)

    taux = round((total_paye / total_initial * 100), 1) if total_initial > 0 else 0

    # Débiteurs actifs = dossiers ACTIF
    nb_actifs = (
        db.query(func.count(DossierClient.id_dossier))
        .filter(
            DossierClient.id_dossier.in_(ids),
            DossierClient.statut == StatutDossierEnum.ACTIF,
        )
        .scalar() or 0
    )

    # Risque moyen : basé sur % créances en retard
    nb_total = (
        db.query(func.count(Creance.id_creance))
        .filter(Creance.id_dossier.in_(ids))
        .scalar() or 1
    )
    nb_retard = (
        db.query(func.count(Creance.id_creance))
        .filter(
            Creance.id_dossier.in_(ids),
            Creance.jours_retard > 0,
        )
        .scalar() or 0
    )
    taux_retard = nb_retard / nb_total
    if taux_retard < 0.20:
        risque = "Faible"
    elif taux_retard < 0.45:
        risque = "Modéré"
    else:
        risque = "Élevé"

    return {
        "total_encours":       total_restant,
        "montant_recouvre":    total_paye,
        "taux_recouvrement":   taux,
        "nb_debiteurs_actifs": nb_actifs,
        "risque_moyen":        risque,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RÉPARTITION PAR SECTEUR (= type_credit des créances)
# ═══════════════════════════════════════════════════════════════════════════════

# Mapping type_credit DB → libellé lisible
TYPE_CREDIT_LABELS: Dict[str, str] = {
    "PretPersonnel":      "Prêt Personnel",
    "CreditAuto":         "Crédit Auto",
    "CreditImmobilier":   "Immobilier",
    "CreditConsommation": "Consommation",
    "Autre":              "Autres",
}

# Couleurs dans l'ordre de la charte graphique
TYPE_CREDIT_COLORS: Dict[str, str] = {
    "CreditImmobilier":   "#004d3a",
    "CreditConsommation": "#006747",
    "PretPersonnel":      "#3a8b60",
    "CreditAuto":         "#5ba97e",
    "Autre":              "#a4c639",
}


@router.get("/portefeuille/secteur")
def get_portefeuille_secteur(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Répartition du portefeuille par type de crédit (secteur).
    Retourne la liste triée par montant_restant décroissant.
    """
    ids = _dossier_ids(db, current_user)
    if not ids:
        return {"secteurs": [], "total": 0}

    rows = (
        db.query(
            Creance.type_credit,
            func.sum(Creance.montant_restant).label("montant_restant"),
            func.sum(Creance.montant_initial).label("montant_initial"),
            func.sum(Creance.montant_paye).label("montant_paye"),
            func.count(Creance.id_creance).label("nb_creances"),
        )
        .filter(Creance.id_dossier.in_(ids))
        .group_by(Creance.type_credit)
        .order_by(func.sum(Creance.montant_restant).desc())
        .all()
    )

    total_restant = sum(float(r.montant_restant or 0) for r in rows)

    secteurs = []
    for r in rows:
        tc           = r.type_credit or "Autre"
        montant      = float(r.montant_restant or 0)
        montant_init = float(r.montant_initial or 0)
        montant_paye = float(r.montant_paye or 0)
        pct          = round(montant / total_restant * 100, 1) if total_restant > 0 else 0
        taux_rec     = round(montant_paye / montant_init * 100, 1) if montant_init > 0 else 0

        secteurs.append({
            "type_credit":       tc,
            "secteur":           TYPE_CREDIT_LABELS.get(tc, tc),
            "montant":           round(montant / 1_000_000, 2),       # en millions
            "montant_raw":       montant,
            "montant_initial":   round(montant_init / 1_000_000, 2),
            "taux_recouvrement": taux_rec,
            "nb_creances":       r.nb_creances,
            "pourcentage":       pct,
            "color":             TYPE_CREDIT_COLORS.get(tc, "#7cc49c"),
        })

    return {
        "secteurs": secteurs,
        "total":    round(total_restant / 1_000_000, 2),  # en millions
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RÉPARTITION PAR RÉGION
# ═══════════════════════════════════════════════════════════════════════════════

REGION_COLORS = ["#006747", "#3a8b60", "#7cc49c", "#a4c639", "#5ba97e", "#9dd9ba"]


@router.get("/portefeuille/region")
def get_portefeuille_region(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Répartition du portefeuille par région.
    Joint : Creance → DossierClient → Client → (ville) + AffectationDossier → Utilisateur → Agence → Region.
    Retourne la liste triée par montant_restant décroissant.
    """
    ids = _dossier_ids(db, current_user)
    if not ids:
        return {"regions": [], "total": 0}

    # Jointure : Créance → Dossier → Affectation active → Agent → Agence → Région
    rows = (
        db.query(
            Region.id_region,
            Region.nom_region,
            func.sum(Creance.montant_restant).label("montant_restant"),
            func.sum(Creance.montant_initial).label("montant_initial"),
            func.sum(Creance.montant_paye).label("montant_paye"),
            func.count(Creance.id_creance).label("nb_creances"),
            func.count(func.distinct(DossierClient.id_dossier)).label("nb_dossiers"),
        )
        .join(DossierClient, Creance.id_dossier == DossierClient.id_dossier)
        .join(
            AffectationDossier,
            (AffectationDossier.id_dossier == DossierClient.id_dossier)
            & (AffectationDossier.actif == True),
        )
        .join(Utilisateur, AffectationDossier.id_agent == Utilisateur.id_utilisateur)
        .join(Agence, Utilisateur.id_agence == Agence.id_agence)
        .join(Region, Agence.id_region == Region.id_region)
        .filter(Creance.id_dossier.in_(ids))
        .group_by(Region.id_region, Region.nom_region)
        .order_by(func.sum(Creance.montant_restant).desc())
        .all()
    )

    total_restant = sum(float(r.montant_restant or 0) for r in rows)

    regions = []
    for i, r in enumerate(rows):
        montant      = float(r.montant_restant or 0)
        montant_init = float(r.montant_initial or 0)
        montant_paye = float(r.montant_paye    or 0)
        pct          = round(montant / total_restant * 100, 1) if total_restant > 0 else 0
        taux_rec     = round(montant_paye / montant_init * 100, 1) if montant_init > 0 else 0

        regions.append({
            "id_region":         r.id_region,
            "region":            r.nom_region,
            "montant":           round(montant / 1_000_000, 2),
            "montant_raw":       montant,
            "taux_recouvrement": taux_rec,
            "nb_creances":       r.nb_creances,
            "nb_dossiers":       r.nb_dossiers,
            "pourcentage":       pct,
            "color":             REGION_COLORS[i % len(REGION_COLORS)],
        })

    return {
        "regions": regions,
        "total":   round(total_restant / 1_000_000, 2),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# AGING BALANCE (ancienneté des créances)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/portefeuille/aging")
def get_portefeuille_aging(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Répartition des créances par tranche d'ancienneté (jours_retard).
    Tranches : 0-30j, 31-60j, 61-90j, 91-180j, >180j
    """
    ids = _dossier_ids(db, current_user)
    if not ids:
        return {"tranches": []}

    tranches_def = [
        ("0-30 jours",   0,   30),
        ("31-60 jours",  31,  60),
        ("61-90 jours",  61,  90),
        ("91-180 jours", 91, 180),
        ("> 180 jours", 181, 99999),
    ]
    colors = ["#006747", "#3a8b60", "#a4c639", "#f59e0b", "#e24b4a"]

    tranches = []
    for (label, low, high), color in zip(tranches_def, colors):
        agg = (
            db.query(
                func.count(Creance.id_creance).label("nb"),
                func.sum(Creance.montant_restant).label("montant"),
            )
            .filter(
                Creance.id_dossier.in_(ids),
                Creance.jours_retard >= low,
                Creance.jours_retard <= high,
            )
            .first()
        )
        tranches.append({
            "label":   label,
            "nb":      agg.nb      or 0,
            "montant": round(float(agg.montant or 0) / 1_000_000, 2),
            "color":   color,
        })

    return {"tranches": tranches}