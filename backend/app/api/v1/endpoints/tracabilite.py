from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import require_manager
from app.models.utilisateur import Utilisateur
from app.models.tracabilite import ActionEnum
from app.schemas.tracabilite import TracabiliteResponse, TracabiliteFilter
from app.crud import tracabilite as crud_trace

router = APIRouter()

@router.get("/", response_model=List[TracabiliteResponse])
def get_traces(
    skip: int = 0,
    limit: int = 100,
    table_cible: Optional[str] = None,
    id_enregistrement: Optional[int] = None,
    action: Optional[ActionEnum] = None,
    id_utilisateur: Optional[int] = None,
    date_debut: Optional[datetime] = None,
    date_fin: Optional[datetime] = None,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Récupérer les traces d'audit avec filtres
    
    Permissions: Managers uniquement (Chef/DGA/Admin)
    
    Exemples de filtres:
    - table_cible: "dossiers_clients", "creances", etc.
    - action: "Creation", "Modification", "Suppression"
    - date_debut/date_fin: filtrage par période
    """
    filters = TracabiliteFilter(
        table_cible=table_cible,
        id_enregistrement=id_enregistrement,
        action=action,
        id_utilisateur=id_utilisateur,
        date_debut=date_debut,
        date_fin=date_fin
    )
    
    return crud_trace.get_traces(db, skip=skip, limit=limit, filters=filters)

@router.get("/{trace_id}", response_model=TracabiliteResponse)
def get_trace(
    trace_id: int,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Récupérer une trace spécifique"""
    trace = crud_trace.get_trace(db, trace_id)
    
    if not trace:
        raise HTTPException(status_code=404, detail="Trace non trouvée")
    
    return trace

@router.get("/utilisateur/{utilisateur_id}", response_model=List[TracabiliteResponse])
def get_traces_utilisateur(
    utilisateur_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les actions d'un utilisateur"""
    return crud_trace.get_traces_utilisateur(db, utilisateur_id, skip, limit)

@router.get("/enregistrement/{table}/{enregistrement_id}", response_model=List[TracabiliteResponse])
def get_traces_enregistrement(
    table: str,
    enregistrement_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer l'historique complet d'un enregistrement
    
    Exemple: /tracabilite/enregistrement/dossiers_clients/123
    Retourne toutes les modifications du dossier 123
    """
    return crud_trace.get_traces_enregistrement(db, table, enregistrement_id, skip, limit)

@router.get("/stats/actions")
def get_stats_actions(
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Statistiques des actions par type"""
    return crud_trace.get_stats_actions(db)
