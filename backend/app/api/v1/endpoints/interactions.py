from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.crud.interaction import interaction as crud_interaction
from app.schemas.interaction import (
    InteractionCreate, 
    InteractionUpdate, 
    InteractionResponse,
    InteractionStats,
    TypeInteractionEnum  # CHANGÉ: TypeInteraction → TypeInteractionEnum
)

router = APIRouter()

@router.get("/", response_model=List[InteractionResponse])
def list_interactions(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    type_interaction: Optional[TypeInteractionEnum] = None,  # CHANGÉ
    id_dossier: Optional[int] = None,
    id_agent: Optional[int] = None
):
    """Liste toutes les interactions avec filtres"""
    return crud_interaction.get_multi(
        db, skip=skip, limit=limit,
        type_interaction=type_interaction,
        id_dossier=id_dossier, id_agent=id_agent
    )

@router.post("/", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
def create_interaction(
    *,
    db: Session = Depends(get_db),
    interaction_in: InteractionCreate
):
    """Créer une nouvelle interaction"""
    return crud_interaction.create(db, obj_in=interaction_in)

@router.get("/{interaction_id}", response_model=InteractionResponse)
def get_interaction(
    *,
    db: Session = Depends(get_db),
    interaction_id: int
):
    """Obtenir une interaction par ID"""
    interaction = crud_interaction.get(db, interaction_id=interaction_id)
    if not interaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interaction non trouvée"
        )
    return interaction

@router.put("/{interaction_id}", response_model=InteractionResponse)
def update_interaction(
    *,
    db: Session = Depends(get_db),
    interaction_id: int,
    interaction_in: InteractionUpdate
):
    """Mettre à jour une interaction"""
    interaction = crud_interaction.get(db, interaction_id=interaction_id)
    if not interaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interaction non trouvée"
        )
    return crud_interaction.update(db, db_obj=interaction, obj_in=interaction_in)

@router.delete("/{interaction_id}", response_model=InteractionResponse)
def delete_interaction(
    *,
    db: Session = Depends(get_db),
    interaction_id: int
):
    """Supprimer une interaction"""
    interaction = crud_interaction.get(db, interaction_id=interaction_id)
    if not interaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interaction non trouvée"
        )
    crud_interaction.delete(db, interaction_id=interaction_id)
    return interaction

@router.get("/dossier/{id_dossier}", response_model=List[InteractionResponse])
def get_interactions_by_dossier(
    *,
    db: Session = Depends(get_db),
    id_dossier: int
):
    """Historique des interactions d'un dossier"""
    return crud_interaction.get_by_dossier(db, id_dossier=id_dossier)

@router.get("/recent/dernieres")
def get_recent_interactions(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=50)
):
    """Dernières interactions"""
    return crud_interaction.get_recent(db, limit=limit)

@router.post("/{interaction_id}/promesse")
def register_promesse(
    *,
    db: Session = Depends(get_db),
    interaction_id: int,
    montant: float = Query(..., gt=0),
    date_promesse: Optional[str] = None
):
    """Enregistrer une promesse de paiement"""
    from datetime import datetime
    
    interaction = crud_interaction.get(db, interaction_id=interaction_id)
    if not interaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interaction non trouvée"
        )
    
    update_data = {
        "promesse_paiement": True,
        "montant_promis": montant
    }
    
    if date_promesse:
        update_data["date_promesse"] = datetime.fromisoformat(date_promesse)
    
    from app.schemas.interaction import InteractionUpdate
    interaction = crud_interaction.update(
        db, db_obj=interaction, obj_in=InteractionUpdate(**update_data)
    )
    
    return {
        "message": "Promesse enregistrée",
        "montant_promis": montant,
        "date_promesse": date_promesse
    }

@router.get("/stats/performance", response_model=InteractionStats)
def get_interaction_stats(
    db: Session = Depends(get_db),
    id_agent: Optional[int] = None
):
    """Stats de performance"""
    return crud_interaction.get_stats(db, id_agent=id_agent)