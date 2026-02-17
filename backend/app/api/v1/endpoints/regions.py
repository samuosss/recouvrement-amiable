from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.schemas.region import RegionCreate, RegionUpdate, RegionResponse
from app.crud import region as crud_region

router = APIRouter()

@router.get("/", response_model=List[RegionResponse])
def get_regions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Récupérer toutes les régions"""
    return crud_region.get_regions(db, skip=skip, limit=limit)

@router.get("/{region_id}", response_model=RegionResponse)
def get_region(region_id: int, db: Session = Depends(get_db)):
    """Récupérer une région par ID"""
    db_region = crud_region.get_region(db, region_id)
    if not db_region:
        raise HTTPException(status_code=404, detail="Région non trouvée")
    return db_region

@router.post("/", response_model=RegionResponse, status_code=status.HTTP_201_CREATED)
def create_region(region: RegionCreate, db: Session = Depends(get_db)):
    """Créer une nouvelle région"""
    # Vérifier si le code existe déjà
    existing = crud_region.get_region_by_code(db, region.code_region)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Une région avec ce code existe déjà"
        )
    return crud_region.create_region(db, region)

@router.put("/{region_id}", response_model=RegionResponse)
def update_region(
    region_id: int,
    region_update: RegionUpdate,
    db: Session = Depends(get_db)
):
    """Mettre à jour une région"""
    db_region = crud_region.update_region(db, region_id, region_update)
    if not db_region:
        raise HTTPException(status_code=404, detail="Région non trouvée")
    return db_region

@router.delete("/{region_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_region(region_id: int, db: Session = Depends(get_db)):
    """Supprimer une région"""
    success = crud_region.delete_region(db, region_id)
    if not success:
        raise HTTPException(status_code=404, detail="Région non trouvée")
    return None