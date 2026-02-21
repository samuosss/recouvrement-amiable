from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.affectation import (
    AffectationCreate,
    AffectationUpdate,
    AffectationResponse,
    AffectationDetailResponse,
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
    db: Session = Depends(get_db)
):
    """
    Récupérer les affectations avec filtres optionnels
    - **dossier_id**: Filtrer par dossier
    - **agent_id**: Filtrer par agent
    - **actif**: Filtrer par statut actif/inactif
    """
    return crud_affectation.get_affectations(
        db=db,
        skip=skip,
        limit=limit,
        dossier_id=dossier_id,
        agent_id=agent_id,
        actif=actif
    )

@router.get("/{affectation_id}", response_model=AffectationResponse)
def get_affectation(
    affectation_id: int,
    db: Session = Depends(get_db)
):
    """Récupérer une affectation par ID"""
    db_affectation = crud_affectation.get_affectation(db, affectation_id)
    if not db_affectation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affectation non trouvée"
        )
    return db_affectation

@router.post("/", response_model=AffectationResponse, status_code=status.HTTP_201_CREATED)
def create_affectation(
    affectation: AffectationCreate,
    db: Session = Depends(get_db)
):
    """Créer une nouvelle affectation"""
    # Vérifier s'il existe déjà une affectation active
    affectation_active = crud_affectation.get_affectation_active(
        db, affectation.id_dossier
    )
    if affectation_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce dossier a déjà une affectation active. Utilisez la réaffectation."
        )
    
    return crud_affectation.create_affectation(db, affectation)

@router.put("/{affectation_id}", response_model=AffectationResponse)
def update_affectation(
    affectation_id: int,
    affectation_update: AffectationUpdate,
    db: Session = Depends(get_db)
):
    """Mettre à jour une affectation"""
    db_affectation = crud_affectation.update_affectation(
        db, affectation_id, affectation_update
    )
    if not db_affectation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Affectation non trouvée"
        )
    return db_affectation

@router.post("/reaffecter", response_model=AffectationResponse)
def reaffecter_dossier(
    reaffectation: ReaffectationRequest,
    db: Session = Depends(get_db)
):
    """
    Réaffecter un dossier à un nouvel agent

    - Désactive l'affectation précédente
    - Crée une nouvelle affectation
    - Trace l'action dans la traçabilité
    - Enregistre le motif de réaffectation
    """
    return crud_affectation.reaffecter_dossier(db, reaffectation)

@router.get("/dossier/{dossier_id}/active", response_model=AffectationResponse)
def get_affectation_active(
    dossier_id: int,
    db: Session = Depends(get_db)
):
    """Récupérer l'affectation active d'un dossier"""
    affectation = crud_affectation.get_affectation_active(db, dossier_id)
    if not affectation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune affectation active pour ce dossier"
        )
    return affectation

@router.get("/dossier/{dossier_id}/historique")
def get_historique_affectations(
    dossier_id: int,
    db: Session = Depends(get_db)
):
    """
    Récupérer l'historique complet des affectations d'un dossier
    
    - Liste toutes les affectations passées et actuelle
    - Indique la durée de chaque affectation
    - Montre les agents successifs
    """
    historique = crud_affectation.get_historique_affectations(db, dossier_id)
    return {
        "dossier_id": dossier_id,
        "total_affectations": len(historique),
        "historique": historique
    }

@router.get("/agent/{agent_id}/dossiers", response_model=List[AffectationResponse])
def get_dossiers_agent(
    agent_id: int,
    actifs_only: bool = True,
    db: Session = Depends(get_db)
):
    """Récupérer tous les dossiers assignés à un agent"""
    return crud_affectation.get_dossiers_par_agent(
        db, agent_id, actif_only=actifs_only
    )

@router.get("/agent/{agent_id}/stats")
def get_stats_agent(
    agent_id: int,
    db: Session = Depends(get_db)
):
    """Statistiques d'un agent (dossiers actifs, traités, terminés)"""
    return crud_affectation.get_stats_agent(db, agent_id)