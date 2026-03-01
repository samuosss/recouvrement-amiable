from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db  # adaptez le chemin
from app.crud.dossier import dossier as crud_dossier
from app.schemas.dossier import (
    DossierCreate, 
    DossierUpdate, 
    DossierResponse,
    StatutDossier,
    PrioriteDossier
)

router = APIRouter()

@router.get("/", response_model=List[DossierResponse])
def list_dossiers(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    statut: Optional[StatutDossier] = None,
    id_client: Optional[int] = None,  # CHANGÉ
):
    """Liste tous les dossiers"""
    return crud_dossier.get_multi(
        db, skip=skip, limit=limit, statut=statut, id_client=id_client
    )

@router.post("/", response_model=DossierResponse, status_code=status.HTTP_201_CREATED)
def create_dossier(*, db: Session = Depends(get_db), dossier_in: DossierCreate):
    """Créer un dossier"""
    return crud_dossier.create(db, obj_in=dossier_in)

@router.get("/{dossier_id}", response_model=DossierResponse)
def get_dossier(*, db: Session = Depends(get_db), dossier_id: int):
    """Obtenir un dossier"""
    dossier = crud_dossier.get(db, dossier_id=dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    return dossier

@router.put("/{dossier_id}", response_model=DossierResponse)
def update_dossier(*, db: Session = Depends(get_db), dossier_id: int, dossier_in: DossierUpdate):
    """Modifier un dossier"""
    dossier = crud_dossier.get(db, dossier_id=dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    return crud_dossier.update(db, db_obj=dossier, obj_in=dossier_in)

@router.delete("/{dossier_id}", response_model=DossierResponse)
def delete_dossier(*, db: Session = Depends(get_db), dossier_id: int):
    """Supprimer un dossier"""
    dossier = crud_dossier.get(db, dossier_id=dossier_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier non trouvé")
    crud_dossier.delete(db, dossier_id=dossier_id)
    return dossier