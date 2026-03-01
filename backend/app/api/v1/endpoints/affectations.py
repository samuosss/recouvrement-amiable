from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import (
    check_dossier_access,
    filter_dossiers_by_role,
    require_manager
)
from app.models.affectation_dossier import AffectationDossier
from app.models.dossier_client import DossierClient
from app.models.utilisateur import Utilisateur, RoleEnum
from app.schemas.affectation import (
    AffectationCreate,
    AffectationUpdate,
    AffectationResponse,
    ReaffectationRequest
)
from app.crud import affectation as crud_affectation

router = APIRouter()

@router.get("/", response_model=List[AffectationResponse])
def get_affectations(
    skip: int = 0,
    limit: int = 100,
    dossier_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    actif: Optional[bool] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer les affectations selon les permissions
    
    Filtrées selon l'accès aux dossiers
    """
    # Récupérer les dossiers accessibles
    dossiers_query = db.query(DossierClient.id_dossier)
    dossiers_query = filter_dossiers_by_role(dossiers_query, current_user, db)
    dossiers_accessibles = [d.id_dossier for d in dossiers_query.all()]
    
    # Query affectations
    query = db.query(AffectationDossier).filter(
        AffectationDossier.id_dossier.in_(dossiers_accessibles)
    )
    
    if dossier_id:
        query = query.filter(AffectationDossier.id_dossier == dossier_id)
    if agent_id:
        query = query.filter(AffectationDossier.id_agent == agent_id)
    if actif is not None:
        query = query.filter(AffectationDossier.actif == actif)
    
    query = query.order_by(AffectationDossier.date_affectation.desc())
    
    return query.offset(skip).limit(limit).all()

@router.get("/{affectation_id}", response_model=AffectationResponse)
def get_affectation(
    affectation_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer une affectation par ID"""
    affectation = crud_affectation.get_affectation(db, affectation_id)
    
    if not affectation:
        raise HTTPException(status_code=404, detail="Affectation non trouvée")
    
    # Vérifier l'accès au dossier
    check_dossier_access(affectation.id_dossier, current_user, db)
    
    return affectation

@router.post("/", response_model=AffectationResponse, status_code=status.HTTP_201_CREATED)
def create_affectation(
    affectation: AffectationCreate,
    current_user: Utilisateur = Depends(require_manager),  # Minimum Chef d'Agence
    db: Session = Depends(get_db)
):
    """
    Créer une nouvelle affectation
    
    Permissions: Chef d'Agence et au-dessus
    """
    # Vérifier l'accès au dossier
    check_dossier_access(affectation.id_dossier, current_user, db)
    
    # Vérifier qu'il n'y a pas déjà une affectation active
    affectation_active = crud_affectation.get_affectation_active(
        db, affectation.id_dossier
    )
    
    if affectation_active:
        raise HTTPException(
            status_code=400,
            detail="Ce dossier a déjà une affectation active. Utilisez la réaffectation."
        )
    
    return crud_affectation.create_affectation(db, affectation)

@router.put("/{affectation_id}", response_model=AffectationResponse)
def update_affectation(
    affectation_id: int,
    affectation_update: AffectationUpdate,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Mettre à jour une affectation"""
    db_affectation = crud_affectation.get_affectation(db, affectation_id)
    
    if not db_affectation:
        raise HTTPException(status_code=404, detail="Affectation non trouvée")
    
    # Vérifier l'accès au dossier
    check_dossier_access(db_affectation.id_dossier, current_user, db)
    
    return crud_affectation.update_affectation(db, affectation_id, affectation_update)

@router.post("/reaffecter", response_model=AffectationResponse)
def reaffecter_dossier(
    reaffectation: ReaffectationRequest,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Réaffecter un dossier à un nouvel agent
    
    Permissions: Chef d'Agence et au-dessus
    """
    # Vérifier l'accès au dossier
    check_dossier_access(reaffectation.id_dossier, current_user, db)
    
    return crud_affectation.reaffecter_dossier(db, reaffectation)

@router.get("/dossier/{dossier_id}/historique")
def get_historique_affectations(
    dossier_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer l'historique des affectations d'un dossier"""
    # Vérifier l'accès
    check_dossier_access(dossier_id, current_user, db)
    
    historique = crud_affectation.get_historique_affectations(db, dossier_id)
    
    return {
        "dossier_id": dossier_id,
        "total_affectations": len(historique),
        "historique": historique
    }

@router.get("/agent/{agent_id}/stats")
def get_stats_agent(
    agent_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Statistiques d'un agent"""
    # Un agent ne peut voir que ses propres stats
    # Les managers peuvent voir les stats de leurs subordonnés
    if current_user.role == RoleEnum.AGENT:
        if agent_id != current_user.id_utilisateur:
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez voir que vos propres statistiques"
            )
    
    return crud_affectation.get_stats_agent(db, agent_id)
