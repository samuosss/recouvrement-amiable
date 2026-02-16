from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta
from app.models.creance import Creance
from app.schemas.creance import CreanceCreate, CreanceUpdate

class CRUDCreance:
    def get(self, db: Session, creance_id: int) -> Optional[Creance]:
        return db.query(Creance).filter(Creance.id_creance == creance_id).first()
    
    def get_by_numero_contrat(self, db: Session, numero_contrat: str) -> Optional[Creance]:  # CHANGÉ
        return db.query(Creance).filter(Creance.numero_contrat == numero_contrat).first()
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        statut: Optional[str] = None,
        id_dossier: Optional[int] = None,  # CHANGÉ
        min_montant: Optional[float] = None,
        max_montant: Optional[float] = None
    ) -> List[Creance]:
        query = db.query(Creance)
        if statut:
            query = query.filter(Creance.statut == statut)
        if id_dossier:
            query = query.filter(Creance.id_dossier == id_dossier)
        if min_montant:
            query = query.filter(Creance.montant_restant >= min_montant)  # CHANGÉ
        if max_montant:
            query = query.filter(Creance.montant_restant <= max_montant)  # CHANGÉ
        return query.order_by(desc(Creance.date_echeance)).offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: CreanceCreate) -> Creance:
        db_obj = Creance(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(self, db: Session, *, db_obj: Creance, obj_in: CreanceUpdate) -> Creance:
        obj_data = obj_in.dict(exclude_unset=True)
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, creance_id: int) -> Optional[Creance]:
        obj = db.query(Creance).filter(Creance.id_creance == creance_id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def get_creances_en_retard(self, db: Session, jours: int = 30) -> List[Creance]:
        date_limite = datetime.now() - timedelta(days=jours)
        return db.query(Creance).filter(
            Creance.date_debut_retard != None,  # CHANGÉ
            Creance.statut.in_(['EnCours', 'PartiellementRegle'])  # CHANGÉ
        ).all()
    
    def get_summary(self, db: Session) -> dict:
        stats = db.query(
            func.count(Creance.id_creance).label("total"),
            func.sum(Creance.montant_initial).label("montant_total"),
            func.sum(Creance.montant_paye).label("montant_paye")
        ).first()
        
        impayees = db.query(Creance).filter(Creance.statut == "EnCours").all()
        total_impayees = sum(c.montant_restant for c in impayees)  # CHANGÉ
        
        return {
            "nombre_creances": stats.total or 0,
            "total_impayees": total_impayees,
            "total_payees": stats.montant_paye or 0,
            "total_en_retard": total_impayees
        }

creance = CRUDCreance()