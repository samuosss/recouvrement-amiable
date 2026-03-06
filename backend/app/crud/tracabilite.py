from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.tracabilite import Tracabilite, ActionEnum
from app.schemas.tracabilite import TracabiliteCreate, TracabiliteFilter

def get_trace(db: Session, trace_id: int) -> Optional[Tracabilite]:
    return db.query(Tracabilite).filter(Tracabilite.id_trace == trace_id).first()

def get_traces(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[TracabiliteFilter] = None
) -> List[Tracabilite]:
    """Récupérer les traces avec filtres optionnels"""
    query = db.query(Tracabilite)
    
    if filters:
        if filters.table_cible:
            query = query.filter(Tracabilite.table_cible == filters.table_cible)
        if filters.id_enregistrement:
            query = query.filter(Tracabilite.id_enregistrement == filters.id_enregistrement)
        if filters.action:
            query = query.filter(Tracabilite.action == filters.action)
        if filters.id_utilisateur:
            query = query.filter(Tracabilite.id_utilisateur == filters.id_utilisateur)
        if filters.date_debut:
            query = query.filter(Tracabilite.date_action >= filters.date_debut)
        if filters.date_fin:
            query = query.filter(Tracabilite.date_action <= filters.date_fin)
    
    return query.order_by(Tracabilite.date_action.desc()).offset(skip).limit(limit).all()

def create_trace(db: Session, trace: TracabiliteCreate) -> Tracabilite:
    """Créer une entrée de traçabilité"""
    db_trace = Tracabilite(**trace.dict())
    db.add(db_trace)
    db.commit()
    db.refresh(db_trace)
    return db_trace

def get_traces_utilisateur(
    db: Session,
    utilisateur_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Tracabilite]:
    """Récupérer toutes les actions d'un utilisateur"""
    return db.query(Tracabilite).filter(
        Tracabilite.id_utilisateur == utilisateur_id
    ).order_by(
        Tracabilite.date_action.desc()
    ).offset(skip).limit(limit).all()

def get_traces_enregistrement(
    db: Session,
    table: str,
    enregistrement_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Tracabilite]:
    """Récupérer l'historique complet d'un enregistrement"""
    return db.query(Tracabilite).filter(
        Tracabilite.table_cible == table,
        Tracabilite.id_enregistrement == enregistrement_id
    ).order_by(
        Tracabilite.date_action.desc()
    ).offset(skip).limit(limit).all()

def get_stats_actions(db: Session) -> dict:
    """Statistiques des actions par type"""
    from sqlalchemy import func
    
    stats = db.query(
        Tracabilite.action,
        func.count(Tracabilite.id_trace).label('count')
    ).group_by(Tracabilite.action).all()
    
    return {stat.action.value: stat.count for stat in stats}
