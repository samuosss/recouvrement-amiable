from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.message import TypeMessageEnum, StatutMessageEnum
from app.models.utilisateur import Utilisateur
from app.schemas.message import (
    MessageCreate,
    MessageUpdate,
    MessageResponse
)
from app.crud import message as crud_message

router = APIRouter()

@router.get("/", response_model=List[MessageResponse])
def get_messages(
    skip: int = 0,
    limit: int = 100,
    type_message: Optional[TypeMessageEnum] = None,
    statut: Optional[StatutMessageEnum] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer tous les messages"""
    return crud_message.get_messages(
        db,
        skip=skip,
        limit=limit,
        type_message=type_message,
        statut=statut
    )

@router.get("/{message_id}", response_model=MessageResponse)
def get_message(
    message_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer un message par ID"""
    message = crud_message.get_message(db, message_id)
    
    if not message:
        raise HTTPException(status_code=404, detail="Message non trouvé")
    
    return message

@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    message: MessageCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Créer un nouveau message (ajout à la file d'attente)
    
    Le message sera traité par les agents automatiques
    """
    return crud_message.create_message(db, message)

@router.put("/{message_id}", response_model=MessageResponse)
def update_message(
    message_id: int,
    message_update: MessageUpdate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mettre à jour un message"""
    message = crud_message.update_message(db, message_id, message_update)
    
    if not message:
        raise HTTPException(status_code=404, detail="Message non trouvé")
    
    return message

@router.get("/en-attente/liste")
def get_messages_en_attente(
    type_message: Optional[TypeMessageEnum] = None,
    limite: int = 100,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer les messages en attente d'envoi
    
    Utilisé par les agents automatiques pour traiter la file
    """
    messages = crud_message.get_messages_en_attente(db, type_message, limite)
    
    return {
        "nombre_messages": len(messages),
        "type_filtre": type_message.value if type_message else "Tous",
        "messages": messages
    }

@router.post("/{message_id}/marquer-envoye")
def marquer_envoye(
    message_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Marquer un message comme envoyé"""
    message = crud_message.marquer_envoye(db, message_id)
    
    if not message:
        raise HTTPException(status_code=404, detail="Message non trouvé")
    
    return {
        "success": True,
        "message": "Message marqué comme envoyé",
        "message_id": message_id,
        "date_envoi": message.date_envoi
    }

@router.post("/{message_id}/marquer-delivre")
def marquer_delivre(
    message_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Marquer un message comme délivré"""
    message = crud_message.marquer_delivre(db, message_id)
    
    if not message:
        raise HTTPException(status_code=404, detail="Message non trouvé")
    
    return {
        "success": True,
        "message": "Message marqué comme délivré",
        "message_id": message_id,
        "date_delivre": message.date_delivre
    }

@router.post("/{message_id}/marquer-echec")
def marquer_echec(
    message_id: int,
    code_erreur: str,
    message_erreur: str,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Marquer un message comme échoué"""
    message = crud_message.marquer_echec(db, message_id, code_erreur, message_erreur)
    
    if not message:
        raise HTTPException(status_code=404, detail="Message non trouvé")
    
    return {
        "success": True,
        "message": "Message marqué comme échoué",
        "message_id": message_id,
        "code_erreur": code_erreur
    }

@router.get("/stats/global")
def get_stats_messages(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Statistiques globales des messages"""
    from sqlalchemy import func
    
    stats = db.query(
        Message.statut,
        func.count(Message.id_message).label('count')
    ).group_by(Message.statut).all()
    
    total = sum(stat.count for stat in stats)
    
    return {
        "total_messages": total,
        "par_statut": {stat.statut.value: stat.count for stat in stats}
    }
