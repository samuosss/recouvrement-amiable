from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate

class CRUDClient:
    def get(self, db: Session, id: int) -> Optional[Client]:
        """Récupérer un client par ID"""
        return db.query(Client).filter(Client.id_client == id).first()
    
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[Client]:
        """Récupérer plusieurs clients avec pagination"""
        return db.query(Client).offset(skip).limit(limit).all()
    
    def get_by_cin(self, db: Session, cin: str) -> Optional[Client]:
        """Récupérer un client par CIN"""
        return db.query(Client).filter(Client.cin == cin).first()
    
    def get_by_email(self, db: Session, email: str) -> Optional[Client]:
        """Récupérer un client par email"""
        return db.query(Client).filter(Client.email == email).first()
    
    def search(self, db: Session, query: str, skip: int = 0, limit: int = 100) -> List[Client]:
        """Rechercher des clients"""
        return db.query(Client).filter(
            (Client.nom.ilike(f"%{query}%")) |
            (Client.prenom.ilike(f"%{query}%")) |
            (Client.cin.ilike(f"%{query}%"))
        ).offset(skip).limit(limit).all()
    
    def create(self, db: Session, obj_in: ClientCreate) -> Client:
        """Créer un nouveau client"""
        db_obj = Client(
            cin=obj_in.cin,
            nom=obj_in.nom,
            prenom=obj_in.prenom,
            telephone=obj_in.telephone,
            email=obj_in.email,
            adresse=obj_in.adresse,
            ville=obj_in.ville,
            code_postal=obj_in.code_postal,
            date_naissance=obj_in.date_naissance,
            profession=obj_in.profession,
            situation_familiale=obj_in.situation_familiale
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(self, db: Session, db_obj: Client, obj_in: ClientUpdate) -> Client:
        """Mettre à jour un client"""
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, id: int) -> Optional[Client]:
        """Supprimer un client"""
        obj = self.get(db, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

client = CRUDClient()
