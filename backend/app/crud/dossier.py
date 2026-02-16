from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from app.models.dossier_client import DossierClient

class CRUDDossier:
    def get(self, db: Session, dossier_id: int) -> Optional[DossierClient]:
        return db.query(DossierClient).filter(DossierClient.id_dossier == dossier_id).first()
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        statut: Optional[str] = None,
        id_client: Optional[int] = None,
    ) -> List[DossierClient]:
        query = db.query(DossierClient)
        if statut:
            query = query.filter(DossierClient.statut == statut)
        if id_client:
            query = query.filter(DossierClient.id_client == id_client)
        return query.order_by(desc(DossierClient.date_ouverture)).offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in) -> DossierClient:
        db_obj = DossierClient(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(self, db: Session, *, db_obj: DossierClient, obj_in) -> DossierClient:
        obj_data = obj_in.dict(exclude_unset=True)
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, dossier_id: int) -> Optional[DossierClient]:
        # Supprimer directement sans charger les relations
        # Utiliser une requête SQL brute pour éviter les problèmes de cascade
        
        # D'abord supprimer les enfants manuellement avec des requêtes SQL
        from sqlalchemy import text
        
        # Supprimer dans l'ordre (respecter les contraintes FK)
        tables = [
            "recommandations",
            "scorings", 
            "alertes",
            "reponses_clients",
            "messages",
            "campagnes_clients",
            "interactions",
            "creances",
            "affectations_dossiers"
        ]
        
        for table in tables:
            db.execute(text(f"DELETE FROM {table} WHERE id_dossier = :dossier_id"), 
                      {"dossier_id": dossier_id})
        
        # Puis supprimer le dossier
        dossier = self.get(db, dossier_id=dossier_id)
        if not dossier:
            return None
            
        db.delete(dossier)
        db.commit()
        
        return dossier

dossier = CRUDDossier()