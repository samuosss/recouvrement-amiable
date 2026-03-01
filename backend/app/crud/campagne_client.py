from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.campagne_client import CampagneClient, StatutEnvoiEnum
from app.schemas.campagne_client import CampagneClientCreate, CampagneClientUpdate

def get_campagne_client(db: Session, campagne_client_id: int) -> Optional[CampagneClient]:
    return db.query(CampagneClient).filter(CampagneClient.id == campagne_client_id).first()

def get_campagnes_clients(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    campagne_id: Optional[int] = None,
    dossier_id: Optional[int] = None,
    statut: Optional[StatutEnvoiEnum] = None
) -> List[CampagneClient]:
    query = db.query(CampagneClient)
    
    if campagne_id:
        query = query.filter(CampagneClient.id_campagne == campagne_id)
    if dossier_id:
        query = query.filter(CampagneClient.id_dossier == dossier_id)
    if statut:
        query = query.filter(CampagneClient.statut == statut)
    
    return query.offset(skip).limit(limit).all()

def create_campagne_client(
    db: Session,
    campagne_client: CampagneClientCreate
) -> CampagneClient:
    db_campagne_client = CampagneClient(
        **campagne_client.dict(),
        statut=StatutEnvoiEnum.EN_ATTENTE
    )
    db.add(db_campagne_client)
    db.commit()
    db.refresh(db_campagne_client)
    return db_campagne_client

def update_campagne_client(
    db: Session,
    campagne_client_id: int,
    campagne_client_update: CampagneClientUpdate
) -> Optional[CampagneClient]:
    db_campagne_client = get_campagne_client(db, campagne_client_id)
    if not db_campagne_client:
        return None
    
    for field, value in campagne_client_update.dict(exclude_unset=True).items():
        setattr(db_campagne_client, field, value)
    
    db.commit()
    db.refresh(db_campagne_client)
    return db_campagne_client

def marquer_envoye(db: Session, campagne_client_id: int) -> Optional[CampagneClient]:
    db_campagne_client = get_campagne_client(db, campagne_client_id)
    if not db_campagne_client:
        return None
    
    db_campagne_client.statut = StatutEnvoiEnum.ENVOYE
    db_campagne_client.date_envoi = datetime.now()
    
    db.commit()
    db.refresh(db_campagne_client)
    return db_campagne_client

def marquer_delivre(db: Session, campagne_client_id: int) -> Optional[CampagneClient]:
    db_campagne_client = get_campagne_client(db, campagne_client_id)
    if not db_campagne_client:
        return None
    
    db_campagne_client.statut = StatutEnvoiEnum.DELIVRE
    db_campagne_client.date_delivre = datetime.now()
    
    db.commit()
    db.refresh(db_campagne_client)
    return db_campagne_client

def marquer_ouvert(db: Session, campagne_client_id: int) -> Optional[CampagneClient]:
    db_campagne_client = get_campagne_client(db, campagne_client_id)
    if not db_campagne_client:
        return None
    
    db_campagne_client.statut = StatutEnvoiEnum.OUVERT
    db_campagne_client.date_ouvert = datetime.now()
    
    db.commit()
    db.refresh(db_campagne_client)
    return db_campagne_client

def marquer_clique(db: Session, campagne_client_id: int) -> Optional[CampagneClient]:
    db_campagne_client = get_campagne_client(db, campagne_client_id)
    if not db_campagne_client:
        return None
    
    db_campagne_client.statut = StatutEnvoiEnum.CLIQUE
    db_campagne_client.date_clique = datetime.now()
    
    db.commit()
    db.refresh(db_campagne_client)
    return db_campagne_client

def marquer_echec(db: Session, campagne_client_id: int) -> Optional[CampagneClient]:
    db_campagne_client = get_campagne_client(db, campagne_client_id)
    if not db_campagne_client:
        return None
    
    db_campagne_client.statut = StatutEnvoiEnum.ECHEC
    
    db.commit()
    db.refresh(db_campagne_client)
    return db_campagne_client

def get_prochains_envois(
    db: Session,
    campagne_id: int,
    limite: int = 100
) -> List[CampagneClient]:
    return db.query(CampagneClient).filter(
        CampagneClient.id_campagne == campagne_id,
        CampagneClient.statut == StatutEnvoiEnum.EN_ATTENTE
    ).limit(limite).all()
