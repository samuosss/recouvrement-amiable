from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from datetime import datetime

from app.models.affectation_dossier import AffectationDossier
from app.models.utilisateur import Utilisateur
from app.models.dossier_client import DossierClient
from app.models.client import Client
from app.schemas.affectation import (
    AffectationCreate,
    AffectationUpdate,
    ReaffectationRequest
)

def get_affectation(
    db: Session,
    affectation_id: int
) -> Optional[AffectationDossier]:
    return db.query(AffectationDossier).filter(
        AffectationDossier.id_affectation == affectation_id
    ).first()

def get_affectations(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    dossier_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    actif: Optional[bool] = None
) -> List[AffectationDossier]:
    query = db.query(AffectationDossier)
    
    if dossier_id:
        query = query.filter(AffectationDossier.id_dossier == dossier_id)
    if agent_id:
        query = query.filter(AffectationDossier.id_agent == agent_id)
    if actif is not None:
        query = query.filter(AffectationDossier.actif == actif)
    
    return query.order_by(
        AffectationDossier.date_affectation.desc()
    ).offset(skip).limit(limit).all()

def get_affectation_active(
    db: Session,
    dossier_id: int
) -> Optional[AffectationDossier]:
    """Récupérer l'affectation active d'un dossier"""
    return db.query(AffectationDossier).filter(
        and_(
            AffectationDossier.id_dossier == dossier_id,
            AffectationDossier.actif == True
        )
    ).first()

def get_dossiers_par_agent(
    db: Session,
    agent_id: int,
    actif_only: bool = True
) -> List[AffectationDossier]:
    """Récupérer tous les dossiers d'un agent"""
    query = db.query(AffectationDossier).filter(
        AffectationDossier.id_agent == agent_id
    )
    if actif_only:
        query = query.filter(AffectationDossier.actif == True)
    return query.all()

def create_affectation(
    db: Session,
    affectation: AffectationCreate
) -> AffectationDossier:
    db_affectation = AffectationDossier(
        **affectation.dict(),
        date_affectation=datetime.now()
    )
    db.add(db_affectation)
    db.commit()
    db.refresh(db_affectation)
    return db_affectation

def update_affectation(
    db: Session,
    affectation_id: int,
    affectation_update: AffectationUpdate
) -> Optional[AffectationDossier]:
    db_affectation = get_affectation(db, affectation_id)
    if not db_affectation:
        return None
    
    for field, value in affectation_update.dict(exclude_unset=True).items():
        setattr(db_affectation, field, value)
    
    db.commit()
    db.refresh(db_affectation)
    return db_affectation

def reaffecter_dossier(
    db: Session,
    reaffectation: ReaffectationRequest
) -> AffectationDossier:
    """
    Réaffecter un dossier à un nouvel agent
    1. Désactiver l'affectation active
    2. Créer une nouvelle affectation
    3. Tracer dans la tracabilité
    """
    # 1. Désactiver l'affectation active
    affectation_active = get_affectation_active(db, reaffectation.id_dossier)
    if affectation_active:
        affectation_active.actif = False
        affectation_active.date_fin = datetime.now()
        db.commit()
    
    # 2. Créer nouvelle affectation
    nouvelle_affectation = AffectationDossier(
        id_dossier=reaffectation.id_dossier,
        id_agent=reaffectation.id_nouvel_agent,
        id_assigneur=reaffectation.id_assigneur,
        date_affectation=datetime.now(),
        motif=reaffectation.motif,
        actif=True
    )
    db.add(nouvelle_affectation)
    
    # 3. Tracer dans tracabilité
    from app.models.tracabilite import Tracabilite
    from app.models.tracabilite import ActionEnum
    
    trace = Tracabilite(
        table_cible="affectations_dossiers",
        id_enregistrement=reaffectation.id_dossier,
        action=ActionEnum.REASSIGNATION,
        id_utilisateur=reaffectation.id_assigneur,
        date_action=datetime.now(),
        anciennes_valeurs={
            "id_agent": affectation_active.id_agent if affectation_active else None
        },
        nouvelles_valeurs={
            "id_agent": reaffectation.id_nouvel_agent,
            "motif": reaffectation.motif
        },
        description=f"Réaffectation dossier {reaffectation.id_dossier}: motif={reaffectation.motif}"
    )
    db.add(trace)
    
    db.commit()
    db.refresh(nouvelle_affectation)
    return nouvelle_affectation

def get_historique_affectations(
    db: Session,
    dossier_id: int
) -> List[dict]:
    """Récupérer l'historique complet des affectations d'un dossier"""
    affectations = db.query(
        AffectationDossier,
        Utilisateur.nom.label('agent_nom'),
        Utilisateur.prenom.label('agent_prenom')
    ).join(
        Utilisateur, AffectationDossier.id_agent == Utilisateur.id_utilisateur
    ).filter(
        AffectationDossier.id_dossier == dossier_id
    ).order_by(
        AffectationDossier.date_affectation.desc()
    ).all()
    
    return [
        {
            "id_affectation": a.AffectationDossier.id_affectation,
            "agent": f"{a.agent_prenom} {a.agent_nom}",
            "date_affectation": a.AffectationDossier.date_affectation,
            "date_fin": a.AffectationDossier.date_fin,
            "motif": a.AffectationDossier.motif,
            "actif": a.AffectationDossier.actif,
            "duree_jours": (
                (a.AffectationDossier.date_fin or datetime.now()) -
                a.AffectationDossier.date_affectation
            ).days
        }
        for a in affectations
    ]

def get_stats_agent(
    db: Session,
    agent_id: int
) -> dict:
    """Statistiques d'un agent"""
    from sqlalchemy import func
    
    total_dossiers = db.query(func.count(AffectationDossier.id_affectation)).filter(
        AffectationDossier.id_agent == agent_id
    ).scalar()
    
    dossiers_actifs = db.query(func.count(AffectationDossier.id_affectation)).filter(
        and_(
            AffectationDossier.id_agent == agent_id,
            AffectationDossier.actif == True
        )
    ).scalar()
    
    return {
        "total_dossiers_traites": total_dossiers or 0,
        "dossiers_actifs": dossiers_actifs or 0,
        "dossiers_termines": (total_dossiers or 0) - (dossiers_actifs or 0)
    }