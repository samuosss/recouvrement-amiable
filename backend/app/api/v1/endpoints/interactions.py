from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import check_dossier_access, filter_dossiers_by_role
from app.models.interaction import Interaction, TypeInteractionEnum
from app.models.dossier_client import DossierClient
from app.models.utilisateur import Utilisateur
from app.schemas.interaction import InteractionCreate, InteractionUpdate, InteractionResponse

router = APIRouter()

@router.get("/", response_model=List[InteractionResponse])
def get_interactions(
    skip: int = 0,
    limit: int = 100,
    dossier_id: Optional[int] = None,
    type_interaction: Optional[TypeInteractionEnum] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer les interactions selon les permissions
    
    Filtrées selon l'accès aux dossiers parents
    """
    # Filtrer les dossiers accessibles
    dossiers_query = db.query(DossierClient.id_dossier)
    dossiers_query = filter_dossiers_by_role(dossiers_query, current_user, db)
    dossiers_accessibles = [d.id_dossier for d in dossiers_query.all()]
    
    # Query interactions
    query = db.query(Interaction).filter(
        Interaction.id_dossier.in_(dossiers_accessibles)
    )
    
    if dossier_id:
        query = query.filter(Interaction.id_dossier == dossier_id)
    if type_interaction:
        query = query.filter(Interaction.type_interaction == type_interaction)
    
    query = query.order_by(Interaction.date_interaction.desc())
    
    return query.offset(skip).limit(limit).all()

@router.get("/{id_interaction}", response_model=InteractionResponse)
def get_interaction(
    id_interaction: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer une interaction par ID"""
    interaction = db.query(Interaction).filter(
        Interaction.id_interaction == id_interaction
    ).first()
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction non trouvée")
    
    # Vérifier l'accès au dossier parent
    check_dossier_access(interaction.id_dossier, current_user, db)
    
    return interaction

@router.post("/", response_model=InteractionResponse, status_code=status.HTTP_201_CREATED)
def create_interaction(
    interaction: InteractionCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Créer une nouvelle interaction"""
    # Vérifier l'accès au dossier
    check_dossier_access(interaction.id_dossier, current_user, db)
    
    # Ajouter l'utilisateur qui crée l'interaction
    db_interaction = Interaction(
        **interaction.dict(),
        id_utilisateur=current_user.id_utilisateur,
        date_interaction=datetime.now()
    )
    
    db.add(db_interaction)
    db.commit()
    db.refresh(db_interaction)
    
    return db_interaction

@router.put("/{id_interaction}", response_model=InteractionResponse)
def update_interaction(
    id_interaction: int,
    interaction_update: InteractionUpdate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mettre à jour une interaction"""
    db_interaction = db.query(Interaction).filter(
        Interaction.id_interaction == id_interaction
    ).first()
    
    if not db_interaction:
        raise HTTPException(status_code=404, detail="Interaction non trouvée")
    
    # Vérifier l'accès au dossier parent
    check_dossier_access(db_interaction.id_dossier, current_user, db)
    
    for field, value in interaction_update.dict(exclude_unset=True).items():
        setattr(db_interaction, field, value)
    
    db.commit()
    db.refresh(db_interaction)
    
    return db_interaction

@router.delete("/{id_interaction}", status_code=status.HTTP_204_NO_CONTENT)
def delete_interaction(
    id_interaction: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Supprimer une interaction"""
    db_interaction = db.query(Interaction).filter(
        Interaction.id_interaction == id_interaction
    ).first()
    
    if not db_interaction:
        raise HTTPException(status_code=404, detail="Interaction non trouvée")
    
    # Vérifier l'accès au dossier parent
    check_dossier_access(db_interaction.id_dossier, current_user, db)
    
    db.delete(db_interaction)
    db.commit()
    
    return None

@router.get("/dossier/{dossier_id}/historique", response_model=List[InteractionResponse])
def get_historique_interactions(
    dossier_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer l'historique des interactions d'un dossier"""
    # Vérifier l'accès au dossier
    check_dossier_access(dossier_id, current_user, db)
    
    interactions = db.query(Interaction).filter(
        Interaction.id_dossier == dossier_id
    ).order_by(
        Interaction.date_interaction.desc()
    ).all()
    
    return interactions
