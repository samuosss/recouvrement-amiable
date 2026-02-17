from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.crud.creance import creance as crud_creance
from app.schemas.creance import (
    CreanceCreate, 
    CreanceUpdate, 
    CreanceResponse,
    CreanceSummary,
    StatutCreanceEnum  # CHANGÉ: StatutCreance → StatutCreanceEnum
)

router = APIRouter()

@router.get("/", response_model=List[CreanceResponse])
def list_creances(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    statut: Optional[StatutCreanceEnum] = None,  # CHANGÉ
    id_dossier: Optional[int] = None,
    min_montant: Optional[float] = None,
    max_montant: Optional[float] = None
):
    """Liste toutes les créances avec filtres"""
    return crud_creance.get_multi(
        db, skip=skip, limit=limit, statut=statut,
        id_dossier=id_dossier, min_montant=min_montant, 
        max_montant=max_montant
    )

@router.post("/", response_model=CreanceResponse, status_code=status.HTTP_201_CREATED)
def create_creance(
    *,
    db: Session = Depends(get_db),
    creance_in: CreanceCreate
):
    """Créer une nouvelle créance"""
    existing = crud_creance.get_by_numero_contrat(db, numero_contrat=creance_in.numero_contrat)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une créance avec ce numéro de contrat existe déjà"
        )
    return crud_creance.create(db, obj_in=creance_in)

@router.get("/{creance_id}", response_model=CreanceResponse)
def get_creance(
    *,
    db: Session = Depends(get_db),
    creance_id: int
):
    """Obtenir une créance par ID"""
    creance = crud_creance.get(db, creance_id=creance_id)
    if not creance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Créance non trouvée"
        )
    return creance

@router.put("/{creance_id}", response_model=CreanceResponse)
def update_creance(
    *,
    db: Session = Depends(get_db),
    creance_id: int,
    creance_in: CreanceUpdate
):
    """Mettre à jour une créance"""
    creance = crud_creance.get(db, creance_id=creance_id)
    if not creance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Créance non trouvée"
        )
    return crud_creance.update(db, db_obj=creance, obj_in=creance_in)

@router.delete("/{creance_id}", response_model=CreanceResponse)
def delete_creance(
    *,
    db: Session = Depends(get_db),
    creance_id: int
):
    """Supprimer une créance"""
    creance = crud_creance.get(db, creance_id=creance_id)
    if not creance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Créance non trouvée"
        )
    crud_creance.delete(db, creance_id=creance_id)
    return creance

@router.post("/{creance_id}/paiement")
def register_payment(
    *,
    db: Session = Depends(get_db),
    creance_id: int,
    montant: float = Query(..., gt=0, description="Montant du paiement")
):
    """Enregistrer un paiement sur une créance"""
    creance = crud_creance.get(db, creance_id=creance_id)
    if not creance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Créance non trouvée"
        )
    
    nouveau_montant_paye = creance.montant_paye + montant
    
    if nouveau_montant_paye > creance.montant_initial:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le montant payé dépasse le montant initial de la créance"
        )
    
    update_data = {
        "montant_paye": nouveau_montant_paye,
        "montant_restant": creance.montant_initial - nouveau_montant_paye,
        "statut": "Regle" if nouveau_montant_paye >= creance.montant_initial else "PartiellementRegle"
    }
    
    from app.schemas.creance import CreanceUpdate
    creance = crud_creance.update(db, db_obj=creance, obj_in=CreanceUpdate(**update_data))
    
    return {
        "message": "Paiement enregistré",
        "montant_paye": montant,
        "total_paye": nouveau_montant_paye,
        "solde_restant": creance.montant_restant,
        "statut": creance.statut
    }

@router.get("/stats/summary", response_model=CreanceSummary)
def get_creances_summary(db: Session = Depends(get_db)):
    """Résumé global des créances"""
    return crud_creance.get_summary(db)

@router.get("/retard/en-retard")
def get_creances_en_retard(
    db: Session = Depends(get_db),
    jours: int = Query(30, ge=0)
):
    """Créances en retard"""
    return crud_creance.get_creances_en_retard(db, jours=jours)