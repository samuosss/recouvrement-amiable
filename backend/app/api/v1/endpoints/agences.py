from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.agence import AgenceCreate, AgenceUpdate, AgenceResponse, AgenceWithStats
from app.crud import agence as crud_agence

router = APIRouter()

@router.get("/", response_model=List[AgenceResponse])
def get_agences(
    skip: int = 0,
    limit: int = 100,
    region_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Récupérer toutes les agences, optionnellement filtrées par région"""
    return crud_agence.get_agences(db, skip=skip, limit=limit, region_id=region_id)

@router.get("/{agence_id}", response_model=AgenceWithStats)
def get_agence(agence_id: int, db: Session = Depends(get_db)):
    """Récupérer une agence par ID avec statistiques"""
    db_agence = crud_agence.get_agence(db, agence_id)
    if not db_agence:
        raise HTTPException(status_code=404, detail="Agence non trouvée")
    
    stats = crud_agence.get_agence_stats(db, agence_id)
    return {**db_agence.__dict__, **stats}

@router.post("/", response_model=AgenceResponse, status_code=status.HTTP_201_CREATED)
def create_agence(agence: AgenceCreate, db: Session = Depends(get_db)):
    """Créer une nouvelle agence"""
    existing = crud_agence.get_agence_by_code(db, agence.code_agence)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Une agence avec ce code existe déjà"
        )
    return crud_agence.create_agence(db, agence)

@router.put("/{agence_id}", response_model=AgenceResponse)
def update_agence(
    agence_id: int,
    agence_update: AgenceUpdate,
    db: Session = Depends(get_db)
):
    """Mettre à jour une agence"""
    db_agence = crud_agence.update_agence(db, agence_id, agence_update)
    if not db_agence:
        raise HTTPException(status_code=404, detail="Agence non trouvée")
    return db_agence

@router.delete("/{agence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agence(agence_id: int, db: Session = Depends(get_db)):
    """Supprimer une agence"""
    success = crud_agence.delete_agence(db, agence_id)
    if not success:
        raise HTTPException(status_code=404, detail="Agence non trouvée")
    return None
