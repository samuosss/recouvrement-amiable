from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import require_dga_or_admin
from app.models.utilisateur import Utilisateur
from app.schemas.region import RegionCreate, RegionUpdate, RegionResponse
from app.crud import region as crud_region

router = APIRouter()

@router.get("/", response_model=List[RegionResponse])
def get_regions(
    skip: int = 0,
    limit: int = 100,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les régions (accessible à tous)"""
    return crud_region.get_regions(db, skip=skip, limit=limit)

@router.get("/{region_id}", response_model=RegionResponse)
def get_region(
    region_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer une région par ID"""
    db_region = crud_region.get_region(db, region_id)
    if not db_region:
        raise HTTPException(status_code=404, detail="Région non trouvée")
    return db_region

@router.post("/", response_model=RegionResponse, status_code=status.HTTP_201_CREATED)
def create_region(
    region: RegionCreate,
    current_user: Utilisateur = Depends(require_dga_or_admin),
    db: Session = Depends(get_db)
):
    """Créer une région (DGA/Admin uniquement)"""
    existing = crud_region.get_region_by_code(db, region.code_region)
    if existing:
        raise HTTPException(status_code=400, detail="Code région déjà utilisé")
    return crud_region.create_region(db, region)

@router.put("/{region_id}", response_model=RegionResponse)
def update_region(
    region_id: int,
    region_update: RegionUpdate,
    current_user: Utilisateur = Depends(require_dga_or_admin),
    db: Session = Depends(get_db)
):
    """Mettre à jour une région (DGA/Admin uniquement)"""
    db_region = crud_region.update_region(db, region_id, region_update)
    if not db_region:
        raise HTTPException(status_code=404, detail="Région non trouvée")
    return db_region

@router.delete("/{region_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_region(
    region_id: int,
    current_user: Utilisateur = Depends(require_dga_or_admin),
    db: Session = Depends(get_db)
):
    """Supprimer une région (DGA/Admin uniquement)"""
    success = crud_region.delete_region(db, region_id)
    if not success:
        raise HTTPException(status_code=404, detail="Région non trouvée")
    return None
