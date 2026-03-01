from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.message import Message, TypeMessageEnum, StatutMessageEnum
from app.schemas.message import MessageCreate, MessageUpdate

def get_message(db: Session, message_id: int) -> Optional[Message]:
    return db.query(Message).filter(Message.id_message == message_id).first()

def get_messages(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    type_message: Optional[TypeMessageEnum] = None,
    statut: Optional[StatutMessageEnum] = None
) -> List[Message]:
    query = db.query(Message)
    
    if type_message:
        query = query.filter(Message.type == type_message)
    if statut:
        query = query.filter(Message.statut == statut)
    
    return query.order_by(Message.created_at.desc()).offset(skip).limit(limit).all()

def create_message(db: Session, message: MessageCreate) -> Message:
    db_message = Message(
        **message.dict(),
        statut=StatutMessageEnum.EN_ATTENTE
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def update_message(
    db: Session,
    message_id: int,
    message_update: MessageUpdate
) -> Optional[Message]:
    db_message = get_message(db, message_id)
    if not db_message:
        return None
    
    for field, value in message_update.dict(exclude_unset=True).items():
        setattr(db_message, field, value)
    
    db.commit()
    db.refresh(db_message)
    return db_message

def get_messages_en_attente(
    db: Session,
    type_message: Optional[TypeMessageEnum] = None,
    limite: int = 100
) -> List[Message]:
    """Récupérer les messages en attente d'envoi"""
    query = db.query(Message).filter(
        Message.statut == StatutMessageEnum.EN_ATTENTE
    )
    
    if type_message:
        query = query.filter(Message.type == type_message)
    
    return query.limit(limite).all()

def marquer_envoye(db: Session, message_id: int) -> Optional[Message]:
    """Marquer un message comme envoyé"""
    db_message = get_message(db, message_id)
    if not db_message:
        return None
    
    db_message.statut = StatutMessageEnum.ENVOYE
    db_message.date_envoi = datetime.now()
    
    db.commit()
    db.refresh(db_message)
    return db_message

def marquer_delivre(db: Session, message_id: int) -> Optional[Message]:
    """Marquer un message comme délivré"""
    db_message = get_message(db, message_id)
    if not db_message:
        return None
    
    db_message.statut = StatutMessageEnum.DELIVRE
    db_message.date_delivre = datetime.now()
    
    db.commit()
    db.refresh(db_message)
    return db_message

def marquer_echec(db: Session, message_id: int, code_erreur: str, message_erreur: str) -> Optional[Message]:
    """Marquer un message comme échoué"""
    db_message = get_message(db, message_id)
    if not db_message:
        return None
    
    db_message.statut = StatutMessageEnum.ECHEC
    db_message.code_erreur = code_erreur
    db_message.message_erreur = message_erreur
    
    db.commit()
    db.refresh(db_message)
    return db_message
