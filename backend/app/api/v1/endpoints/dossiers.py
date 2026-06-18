from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import (
    filter_dossiers_by_role,
    check_dossier_access,
    require_manager,
    get_user_scope_summary
)
from app.models.dossier_client import DossierClient, StatutDossierEnum, PrioriteEnum
from app.models.utilisateur import Utilisateur
from app.schemas.dossier import (
    DossierCreate,
    DossierUpdate,
    DossierResponse
)

router = APIRouter()

# ========================
# ENDPOINTS LECTURE
# ========================

@router.get("/", response_model=List[DossierResponse])
def get_dossiers(
    skip: int = 0,
    limit: int = 100,
    statut: Optional[StatutDossierEnum] = None,
    priorite: Optional[PrioriteEnum] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(DossierClient)
    query = filter_dossiers_by_role(query, current_user, db)

    if statut:
        query = query.filter(DossierClient.statut == statut)
    if priorite:
        query = query.filter(DossierClient.priorite == priorite)

    query = query.distinct()
    query = query.order_by(DossierClient.date_ouverture.desc())
    return query.offset(skip).limit(limit).all()


@router.get("/me/scope", response_model=dict)
def get_my_scope(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return get_user_scope_summary(current_user, db)


@router.get("/stats/summary", response_model=dict)
def get_dossiers_stats(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import func

    query = db.query(DossierClient)
    query = filter_dossiers_by_role(query, current_user, db)
    query = query.distinct()

    total = query.count()

    stats_statut = db.query(
        DossierClient.statut,
        func.count(DossierClient.id_dossier).label('count')
    ).select_from(query.subquery()).group_by(DossierClient.statut).all()

    stats_priorite = db.query(
        DossierClient.priorite,
        func.count(DossierClient.id_dossier).label('count')
    ).select_from(query.subquery()).group_by(DossierClient.priorite).all()

    montant_total = query.with_entities(
        func.sum(DossierClient.montant_total_du)
    ).scalar() or 0

    return {
        "total_dossiers":  total,
        "montant_total_du": float(montant_total),
        "par_statut":   {s.statut.value:   s.count for s in stats_statut},
        "par_priorite": {s.priorite.value: s.count for s in stats_priorite},
        "scope": get_user_scope_summary(current_user, db)
    }


@router.get("/{id_dossier}", response_model=DossierResponse)
def get_dossier(
    id_dossier: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    check_dossier_access(id_dossier, current_user, db)

    dossier = db.query(DossierClient).filter(
        DossierClient.id_dossier == id_dossier
    ).first()

    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    return dossier


# ========================
# ENDPOINTS ÉCRITURE
# ========================

@router.post("/", response_model=DossierResponse, status_code=status.HTTP_201_CREATED)
def create_dossier(
    dossier: DossierCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    from app.models.client import Client
    from app.models.tracabilite import Tracabilite, ActionEnum

    # Vérifier que le client existe
    client = db.query(Client).filter(Client.id_client == dossier.id_client).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")

    # ── Construire le dict en forçant les valeurs d'enum (pas les noms) ──────
    data = {}
    for field, value in dossier:
        if hasattr(value, "value"):          # c'est un enum Pydantic → prendre .value
            data[field] = value.value
        else:
            data[field] = value

    # ── date_ouverture est NOT NULL → la fournir si absente ──────────────────
    if not data.get("date_ouverture"):
        data["date_ouverture"] = datetime.now(timezone.utc)

    # ── Resynchroniser la séquence PostgreSQL avant l'insert ─────────────────
    # Évite l'erreur "duplicate key" quand la séquence est désynchronisée
    try:
        db.execute(text(
            "SELECT setval('dossiers_clients_id_dossier_seq', "
            "(SELECT COALESCE(MAX(id_dossier), 0) FROM dossiers_clients))"
        ))
    except Exception:
        pass  # ignore si la séquence n'existe pas (autre DB)

    # ── Créer le dossier + tracabilité en un seul commit ─────────────────────
    db_dossier = DossierClient(**data)
    db.add(db_dossier)

    try:
        db.flush()   # obtient l'id_dossier sans committer
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur création dossier : {str(e)}")

    try:
        trace = Tracabilite(
            table_cible="dossiers_clients",
            id_enregistrement=db_dossier.id_dossier,
            action=ActionEnum.CREATION,
            id_utilisateur=current_user.id_utilisateur,
            date_action=datetime.now(timezone.utc),
            nouvelles_valeurs={k: str(v) for k, v in data.items()},
            description=f"Création dossier {db_dossier.numero_dossier}"
        )
        db.add(trace)
        db.commit()
        db.refresh(db_dossier)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur tracabilité : {str(e)}")

    return db_dossier


@router.put("/{id_dossier}", response_model=DossierResponse)
def update_dossier(
    id_dossier: int,
    dossier_update: DossierUpdate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    from app.models.tracabilite import Tracabilite, ActionEnum

    check_dossier_access(id_dossier, current_user, db)

    db_dossier = db.query(DossierClient).filter(
        DossierClient.id_dossier == id_dossier
    ).first()

    if not db_dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    old_values = {
        "statut":          db_dossier.statut.value   if db_dossier.statut   else None,
        "priorite":        db_dossier.priorite.value if db_dossier.priorite else None,
        "montant_total_du": float(db_dossier.montant_total_du) if db_dossier.montant_total_du else None,
    }

    for field, value in dossier_update.dict(exclude_unset=True).items():
        # Forcer la valeur string pour les enums
        if hasattr(value, "value"):
            value = value.value
        setattr(db_dossier, field, value)

    trace = Tracabilite(
        table_cible="dossiers_clients",
        id_enregistrement=id_dossier,
        action=ActionEnum.MODIFICATION,
        id_utilisateur=current_user.id_utilisateur,
        date_action=datetime.now(timezone.utc),
        anciennes_valeurs=old_values,
        nouvelles_valeurs={
            k: v.value if hasattr(v, "value") else str(v)
            for k, v in dossier_update.dict(exclude_unset=True).items()
        },
        description=f"Modification dossier {db_dossier.numero_dossier}"
    )
    db.add(trace)
    db.commit()
    db.refresh(db_dossier)

    return db_dossier


@router.delete("/{id_dossier}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dossier(
    id_dossier: int,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    from app.models.tracabilite import Tracabilite, ActionEnum

    check_dossier_access(id_dossier, current_user, db)

    db_dossier = db.query(DossierClient).filter(
        DossierClient.id_dossier == id_dossier
    ).first()

    if not db_dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")

    trace = Tracabilite(
        table_cible="dossiers_clients",
        id_enregistrement=id_dossier,
        action=ActionEnum.SUPPRESSION,
        id_utilisateur=current_user.id_utilisateur,
        date_action=datetime.now(timezone.utc),
        anciennes_valeurs={
            "numero_dossier": db_dossier.numero_dossier,
            "statut": db_dossier.statut.value if db_dossier.statut else None,
        },
        description=f"Suppression dossier {db_dossier.numero_dossier}"
    )
    db.add(trace)
    db.delete(db_dossier)
    db.commit()

    return None