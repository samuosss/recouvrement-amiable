"""
affectations.py — Router affectations avec ordre de routes corrigé

FIX PRINCIPAL :
  FastAPI résout les routes dans l'ordre de déclaration.
  GET /{affectation_id} capturait /agent/{id}/stats avant d'y arriver.
  Solution : toutes les routes statiques/préfixées AVANT les routes /{id}.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import (
    check_dossier_access,
    filter_dossiers_by_role,
    require_manager,
)
from app.models.affectation_dossier import AffectationDossier
from app.models.dossier_client import DossierClient, StatutDossierEnum
from app.models.utilisateur import Utilisateur, RoleEnum
from app.schemas.affectation import (
    AffectationCreate,
    AffectationUpdate,
    AffectationResponse,
    AssignationRequest,
    ReaffectationRequest,
)
from app.crud import affectation as crud_affectation

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS INTERNES
# ═══════════════════════════════════════════════════════════════════════════════

def _get_agent_or_404(db: Session, agent_id: int) -> Utilisateur:
    agent = db.query(Utilisateur).filter(
        Utilisateur.id_utilisateur == agent_id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent introuvable")
    return agent


def _create_notification(
    db: Session,
    *,
    destinataire_id: int,
    titre: str,
    message: str,
    type_notif: str = "affectation",
    reference_id: Optional[int] = None,
) -> None:
    try:
        from app.models.notification import Notification
        notif = Notification(
            id_destinataire=destinataire_id,
            titre=titre,
            message=message,
            type_notif=type_notif,
            id_reference=reference_id,
            lue=False,
            date_creation=datetime.now(timezone.utc),
        )
        db.add(notif)
    except ImportError:
        pass
        

# ═══════════════════════════════════════════════════════════════════════════════
# BLOC 1 — ROUTES STATIQUES ET PRÉFIXÉES  (TOUJOURS AVANT /{affectation_id})
# ═══════════════════════════════════════════════════════════════════════════════

# ── Liste ──────────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[AffectationResponse])
def get_affectations(
    skip: int = 0,
    limit: int = 100,
    dossier_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    actif: Optional[bool] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Récupérer les affectations selon les permissions."""
    dossiers_query = db.query(DossierClient.id_dossier)
    dossiers_query = filter_dossiers_by_role(dossiers_query, current_user, db)
    dossiers_accessibles = [d.id_dossier for d in dossiers_query.all()]

    query = db.query(AffectationDossier).filter(
        AffectationDossier.id_dossier.in_(dossiers_accessibles)
    )
    if dossier_id:
        query = query.filter(AffectationDossier.id_dossier == dossier_id)
    if agent_id:
        query = query.filter(AffectationDossier.id_agent == agent_id)
    if actif is not None:
        query = query.filter(AffectationDossier.actif == actif)

    return query.order_by(
        AffectationDossier.date_affectation.desc()
    ).offset(skip).limit(limit).all()


# ── Agent : dossiers ───────────────────────────────────────────────────────────
#   DOIT être déclaré avant GET /{affectation_id}

@router.get("/agent/{agent_id}/dossiers", response_model=List[AffectationResponse])
def get_dossiers_agent(
    agent_id: int,
    actif: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Dossiers actifs/historiques d'un agent."""
    if current_user.role == RoleEnum.AGENT and agent_id != current_user.id_utilisateur:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez consulter que vos propres dossiers.",
        )
    _get_agent_or_404(db, agent_id)

    query = db.query(AffectationDossier).filter(
        AffectationDossier.id_agent == agent_id
    )
    if actif is not None:
        query = query.filter(AffectationDossier.actif == actif)

    return query.order_by(
        AffectationDossier.date_affectation.desc()
    ).offset(skip).limit(limit).all()


# ── Agent : stats ──────────────────────────────────────────────────────────────
#   DOIT être déclaré avant GET /{affectation_id}
@router.get("/agent/{agent_id}/stats")
def get_stats_agent(
    agent_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Statistiques complètes d'un agent.
    """
    from sqlalchemy import func
    
    # Vérifier les permissions
    if current_user.role == RoleEnum.AGENT and agent_id != current_user.id_utilisateur:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez voir que vos propres statistiques.",
        )
    
    # Vérifier que l'agent existe
    agent = db.query(Utilisateur).filter(
        Utilisateur.id_utilisateur == agent_id
    ).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent introuvable")
    
    # ============================================================
    # 1. Toutes les affectations de l'agent
    # ============================================================
    all_affectations = db.query(AffectationDossier).filter(
        AffectationDossier.id_agent == agent_id
    ).all()
    
    total_dossiers = len(all_affectations)
    dossiers_actifs = sum(1 for a in all_affectations if a.actif)
    dossier_ids = [a.id_dossier for a in all_affectations]
    
    # ============================================================
    # 2. Dossiers résolus
    # Note: D'après votre CSV, les statuts sont "ACTIF" et "SUSPENDU"
    # Un dossier est "résolu" quand il n'est plus actif
    # ============================================================
    dossiers_resolus = 0
    if dossier_ids:
        try:
            # Compter les dossiers qui ne sont PAS "ACTIF"
            dossiers_resolus = db.query(func.count(DossierClient.id_dossier)).filter(
                DossierClient.id_dossier.in_(dossier_ids),
                DossierClient.statut != "ACTIF"  # Tout ce qui n'est plus actif
            ).scalar() or 0
        except Exception as e:
            print(f"Erreur comptage résolus: {e}")
            dossiers_resolus = 0
    
    # ============================================================
    # 3. Taux de résolution
    # ============================================================
    taux_resolution = round((dossiers_resolus / total_dossiers * 100) if total_dossiers > 0 else 0)
    
    # ============================================================
    # 4. Objectif mensuel (paramétrable)
    # ============================================================
    objectif_mensuel = 20
    
    # ============================================================
    # 5. Progression
    # ============================================================
    progression_objectif = round((dossiers_resolus / objectif_mensuel * 100) if objectif_mensuel > 0 else 0)
    progression_objectif = min(progression_objectif, 100)
    
    # ============================================================
    # 6. Retour
    # ============================================================
    return {
        "total_dossiers": total_dossiers,
        "dossiers_actifs": dossiers_actifs,
        "dossiers_resolus": dossiers_resolus,
        "taux_resolution": taux_resolution,
        "objectif_mensuel": objectif_mensuel,        # ✅ corrigé
        "progression_objectif": progression_objectif,
        "capacite_max": 20,
    }
# ── Historique dossier ─────────────────────────────────────────────────────────
#   DOIT être déclaré avant GET /{affectation_id}

@router.get("/dossier/{dossier_id}/historique")
def get_historique_affectations(
    dossier_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    check_dossier_access(dossier_id, current_user, db)
    historique = crud_affectation.get_historique_affectations(db, dossier_id)
    return {
        "dossier_id":        dossier_id,
        "total_affectations": len(historique),
        "historique":        historique,
    }


# ── Assigner ───────────────────────────────────────────────────────────────────

@router.post("/assigner", response_model=AffectationResponse, status_code=status.HTTP_201_CREATED)
def assigner_dossier(
    payload: AssignationRequest,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """
    Assigner un dossier libre à un agent.
    Bloque si une affectation active existe déjà (utiliser /reaffecter dans ce cas).
    """
    check_dossier_access(payload.id_dossier, current_user, db)

    if crud_affectation.get_affectation_active(db, payload.id_dossier):
        raise HTTPException(
            status_code=400,
            detail="Ce dossier a déjà une affectation active. Utilisez /reaffecter.",
        )

    dossier = db.query(DossierClient).filter(
        DossierClient.id_dossier == payload.id_dossier
    ).first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable.")

    new_affectation = AffectationDossier(
        id_dossier=payload.id_dossier,
        id_agent=payload.id_agent,
        id_assigneur=current_user.id_utilisateur,
        date_affectation=datetime.now(timezone.utc),
        motif=payload.motif,
        actif=True,
    )
    db.add(new_affectation)
    db.flush()

    _create_notification(
        db,
        destinataire_id=payload.id_agent,
        titre="Nouveau dossier affecté",
        message=(
            f"Le dossier {dossier.numero_dossier} vous a été affecté"
            f"{f' — {payload.motif}' if payload.motif else ''}."
        ),
        type_notif="affectation",
        reference_id=new_affectation.id_affectation,
    )

    try:
        from app.models.tracabilite import Tracabilite, ActionEnum
        db.add(Tracabilite(
            table_cible="affectations_dossiers",
            id_enregistrement=new_affectation.id_affectation,
            action=ActionEnum.CREATION,
            id_utilisateur=current_user.id_utilisateur,
            date_action=datetime.now(timezone.utc),
            nouvelles_valeurs={
                "id_dossier": payload.id_dossier,
                "id_agent":   payload.id_agent,
                "motif":      payload.motif,
            },
            description=f"Affectation dossier {dossier.numero_dossier} → agent #{payload.id_agent}",
        ))
    except ImportError:
        pass

    db.commit()
    db.refresh(new_affectation)
    return new_affectation


# ── Réaffecter ─────────────────────────────────────────────────────────────────

@router.post("/reaffecter", response_model=AffectationResponse)
def reaffecter_dossier(
    reaffectation: ReaffectationRequest,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db),
):
    """
    Réaffecter un dossier à un nouvel agent.
    Clôture l'ancienne affectation, crée la nouvelle, alerte les deux agents.
    """
    check_dossier_access(reaffectation.id_dossier, current_user, db)

    dossier = db.query(DossierClient).filter(
        DossierClient.id_dossier == reaffectation.id_dossier
    ).first()
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier introuvable.")

    ancienne        = crud_affectation.get_affectation_active(db, reaffectation.id_dossier)
    ancien_agent_id = None

    if ancienne:
        ancien_agent_id  = ancienne.id_agent
        ancienne.actif   = False
        ancienne.date_fin = datetime.now(timezone.utc)
        db.flush()

    nouvelle = AffectationDossier(
        id_dossier=reaffectation.id_dossier,
        id_agent=reaffectation.id_nouvel_agent,
        id_assigneur=current_user.id_utilisateur,
        date_affectation=datetime.now(timezone.utc),
        motif=reaffectation.motif,
        actif=True,
    )
    db.add(nouvelle)
    db.flush()

    _create_notification(
        db,
        destinataire_id=reaffectation.id_nouvel_agent,
        titre="Dossier réaffecté — prise en charge",
        message=(
            f"Le dossier {dossier.numero_dossier} vous a été réaffecté"
            f"{f' — {reaffectation.motif}' if reaffectation.motif else ''}."
        ),
        type_notif="reaffectation",
        reference_id=nouvelle.id_affectation,
    )

    if ancien_agent_id and ancien_agent_id != reaffectation.id_nouvel_agent:
        _create_notification(
            db,
            destinataire_id=ancien_agent_id,
            titre="Dossier retiré de votre charge",
            message=(
                f"Le dossier {dossier.numero_dossier} a été réaffecté à un autre agent"
                f"{f' — {reaffectation.motif}' if reaffectation.motif else ''}."
            ),
            type_notif="reaffectation",
            reference_id=nouvelle.id_affectation,
        )

    try:
        from app.models.tracabilite import Tracabilite, ActionEnum
        db.add(Tracabilite(
            table_cible="affectations_dossiers",
            id_enregistrement=nouvelle.id_affectation,
            action=ActionEnum.MODIFICATION,
            id_utilisateur=current_user.id_utilisateur,
            date_action=datetime.now(timezone.utc),
            anciennes_valeurs={"id_agent": ancien_agent_id} if ancien_agent_id else None,
            nouvelles_valeurs={
                "id_dossier": reaffectation.id_dossier,
                "id_agent":   reaffectation.id_nouvel_agent,
                "motif":      reaffectation.motif,
            },
            description=(
                f"Réaffectation dossier {dossier.numero_dossier} "
                f"agent #{ancien_agent_id} → #{reaffectation.id_nouvel_agent}"
            ),
        ))
    except ImportError:
        pass

    db.commit()
    db.refresh(nouvelle)
    return nouvelle


# ── Créer (générique) ──────────────────────────────────────────────────────────

@router.post("/", response_model=AffectationResponse, status_code=status.HTTP_201_CREATED)
def create_affectation(
    affectation: AffectationCreate,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db),
):
    check_dossier_access(affectation.id_dossier, current_user, db)
    if crud_affectation.get_affectation_active(db, affectation.id_dossier):
        raise HTTPException(
            status_code=400,
            detail="Ce dossier a déjà une affectation active. Utilisez /reaffecter.",
        )
    return crud_affectation.create_affectation(db, affectation)


# ═══════════════════════════════════════════════════════════════════════════════
# BLOC 2 — ROUTES DYNAMIQUES /{affectation_id}  (TOUJOURS EN DERNIER)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{affectation_id}", response_model=AffectationResponse)
def get_affectation(
    affectation_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    affectation = crud_affectation.get_affectation(db, affectation_id)
    if not affectation:
        raise HTTPException(status_code=404, detail="Affectation non trouvée")
    check_dossier_access(affectation.id_dossier, current_user, db)
    return affectation


@router.put("/{affectation_id}", response_model=AffectationResponse)
def update_affectation(
    affectation_id: int,
    affectation_update: AffectationUpdate,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db),
):
    db_affectation = crud_affectation.get_affectation(db, affectation_id)
    if not db_affectation:
        raise HTTPException(status_code=404, detail="Affectation non trouvée")
    check_dossier_access(db_affectation.id_dossier, current_user, db)
    return crud_affectation.update_affectation(db, affectation_id, affectation_update)