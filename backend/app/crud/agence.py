from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List

from app.models.agence import Agence
from app.models.utilisateur import Utilisateur
from app.models.dossier_client import DossierClient
from app.schemas.agence import AgenceCreate, AgenceUpdate

def get_agence(db: Session, agence_id: int) -> Optional[Agence]:
    return db.query(Agence).filter(Agence.id_agence == agence_id).first()

def get_agence_by_code(db: Session, code: str) -> Optional[Agence]:
    return db.query(Agence).filter(Agence.code_agence == code).first()

def get_agences(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    region_id: Optional[int] = None
) -> List[Agence]:
    query = db.query(Agence)
    if region_id:
        query = query.filter(Agence.id_region == region_id)
    return query.offset(skip).limit(limit).all()

def create_agence(db: Session, agence: AgenceCreate) -> Agence:
    db_agence = Agence(**agence.dict())
    db.add(db_agence)
    db.commit()
    db.refresh(db_agence)
    return db_agence

def update_agence(db: Session, agence_id: int, agence_update: AgenceUpdate) -> Optional[Agence]:
    db_agence = get_agence(db, agence_id)
    if not db_agence:
        return None
    
    for field, value in agence_update.dict(exclude_unset=True).items():
        setattr(db_agence, field, value)
    
    db.commit()
    db.refresh(db_agence)
    return db_agence

def delete_agence(db: Session, agence_id: int) -> bool:
    db_agence = get_agence(db, agence_id)
    if not db_agence:
        return False
    
    db.delete(db_agence)
    db.commit()
    return True

def get_agence_stats(db: Session, agence_id: int) -> dict:
    """Récupérer les statistiques d'une agence"""
    nombre_utilisateurs = db.query(func.count(Utilisateur.id_utilisateur)).filter(
        Utilisateur.id_agence == agence_id
    ).scalar()
    
    nombre_dossiers = db.query(func.count(DossierClient.id_dossier)).join(
        Utilisateur
    ).filter(Utilisateur.id_agence == agence_id).scalar()
    
    return {
        "nombre_utilisateurs": nombre_utilisateurs or 0,
        "nombre_dossiers": nombre_dossiers or 0
    }