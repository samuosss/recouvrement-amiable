from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import require_manager, require_dga_or_admin
from app.models.utilisateur import Utilisateur
from app.schemas.agence import AgenceCreate, AgenceUpdate, AgenceResponse, AgenceWithStats
from app.crud import agence as crud_agence

router = APIRouter()

@router.get("/", response_model=List[AgenceResponse])
def get_agences(
    skip: int = 0,
    limit: int = 100,
    region_id: Optional[int] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les agences (accessible à tous)"""
    return crud_agence.get_agences(db, skip=skip, limit=limit, region_id=region_id)

@router.get("/{agence_id}", response_model=AgenceWithStats)
def get_agence(
    agence_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer une agence avec ses stats"""
    db_agence = crud_agence.get_agence(db, agence_id)
    if not db_agence:
        raise HTTPException(status_code=404, detail="Agence non trouvée")
    
    stats = crud_agence.get_agence_stats(db, agence_id)
    return {**db_agence.__dict__, **stats}

@router.post("/", response_model=AgenceResponse, status_code=status.HTTP_201_CREATED)
def create_agence(
    agence: AgenceCreate,
    current_user: Utilisateur = Depends(require_dga_or_admin),
    db: Session = Depends(get_db)
):
    """Créer une agence (DGA/Admin uniquement)"""
    existing = crud_agence.get_agence_by_code(db, agence.code_agence)
    if existing:
        raise HTTPException(status_code=400, detail="Code agence déjà utilisé")
    return crud_agence.create_agence(db, agence)

@router.put("/{agence_id}", response_model=AgenceResponse)
def update_agence(
    agence_id: int,
    agence_update: AgenceUpdate,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Mettre à jour une agence (Managers)"""
    db_agence = crud_agence.update_agence(db, agence_id, agence_update)
    if not db_agence:
        raise HTTPException(status_code=404, detail="Agence non trouvée")
    return db_agence

@router.delete("/{agence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agence(
    agence_id: int,
    current_user: Utilisateur = Depends(require_dga_or_admin),
    db: Session = Depends(get_db)
):
    """Supprimer une agence (DGA/Admin uniquement)"""
    success = crud_agence.delete_agence(db, agence_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agence non trouvée")
    return None
