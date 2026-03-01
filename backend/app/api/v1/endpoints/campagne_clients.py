from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import require_manager
from app.models.campagne_client import StatutEnvoiEnum
from app.models.utilisateur import Utilisateur
from app.schemas.campagne_client import (
    CampagneClientCreate,
    CampagneClientUpdate,
    CampagneClientResponse
)
from app.crud import campagne_client as crud_campagne_client

router = APIRouter()

@router.get("/", response_model=List[CampagneClientResponse])
def get_campagnes_clients(
    skip: int = 0,
    limit: int = 100,
    campagne_id: Optional[int] = None,
    client_id: Optional[int] = None,
    statut: Optional[StatutEnvoiEnum] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer les liaisons campagne-client"""
    return crud_campagne_client.get_campagnes_clients(
        db,
        skip=skip,
        limit=limit,
        campagne_id=campagne_id,
        client_id=client_id,
        statut=statut
    )

@router.get("/{campagne_client_id}", response_model=CampagneClientResponse)
def get_campagne_client(
    campagne_client_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer une liaison par ID"""
    campagne_client = crud_campagne_client.get_campagne_client(db, campagne_client_id)
    
    if not campagne_client:
        raise HTTPException(status_code=404, detail="Liaison non trouvée")
    
    return campagne_client

@router.post("/", response_model=CampagneClientResponse, status_code=status.HTTP_201_CREATED)
def create_campagne_client(
    campagne_client: CampagneClientCreate,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Ajouter un client à une campagne
    
    Permissions: Managers uniquement
    """
    return crud_campagne_client.create_campagne_client(db, campagne_client)

@router.put("/{campagne_client_id}", response_model=CampagneClientResponse)
def update_campagne_client(
    campagne_client_id: int,
    campagne_client_update: CampagneClientUpdate,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Mettre à jour une liaison campagne-client"""
    campagne_client = crud_campagne_client.update_campagne_client(
        db, campagne_client_id, campagne_client_update
    )
    
    if not campagne_client:
        raise HTTPException(status_code=404, detail="Liaison non trouvée")
    
    return campagne_client

@router.post("/{campagne_client_id}/marquer-envoye")
def marquer_envoye(
    campagne_client_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Marquer un message comme envoyé (utilisé par les agents auto)"""
    result = crud_campagne_client.marquer_envoye(db, campagne_client_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Liaison non trouvée")
    
    return {"message": "Message marqué comme envoyé", "campagne_client_id": campagne_client_id}

@router.post("/{campagne_client_id}/marquer-reussi")
def marquer_reussi(
    campagne_client_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Marquer un envoi comme réussi"""
    result = crud_campagne_client.marquer_reussi(db, campagne_client_id)
    
    if not result:
        raise HTTPException(status_code=404, detail="Liaison non trouvée")
    
    return {"message": "Envoi marqué comme réussi", "campagne_client_id": campagne_client_id}

@router.post("/{campagne_client_id}/marquer-echec")
def marquer_echec(
    campagne_client_id: int,
    raison: str,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Marquer un envoi comme échoué"""
    result = crud_campagne_client.marquer_echec(db, campagne_client_id, raison)
    
    if not result:
        raise HTTPException(status_code=404, detail="Liaison non trouvée")
    
    return {"message": "Envoi marqué comme échoué", "campagne_client_id": campagne_client_id}

@router.get("/campagne/{campagne_id}/prochains-envois")
def get_prochains_envois(
    campagne_id: int,
    limite: int = 100,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer les prochains messages à envoyer pour une campagne
    
    Utilisé par les agents automatiques
    """
    envois = crud_campagne_client.get_prochains_envois(db, campagne_id, limite)
    
    return {
        "campagne_id": campagne_id,
        "nombre_envois": len(envois),
        "envois": envois
    }
