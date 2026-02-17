from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from app.models.interaction import Interaction
from app.schemas.interaction import InteractionCreate, InteractionUpdate

class CRUDInteraction:
    def get(self, db: Session, interaction_id: int) -> Optional[Interaction]:
        return db.query(Interaction).filter(Interaction.id_interaction == interaction_id).first()
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        type_interaction: Optional[str] = None,
        id_dossier: Optional[int] = None,
        id_agent: Optional[int] = None
    ) -> List[Interaction]:
        query = db.query(Interaction)
        if type_interaction:
            query = query.filter(Interaction.type == type_interaction)
        if id_dossier:
            query = query.filter(Interaction.id_dossier == id_dossier)
        if id_agent:
            query = query.filter(Interaction.id_agent == id_agent)
        return query.order_by(desc(Interaction.date_interaction)).offset(skip).limit(limit).all()
    
    def create(self, db: Session, *, obj_in: InteractionCreate) -> Interaction:
        db_obj = Interaction(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update(self, db: Session, *, db_obj: Interaction, obj_in: InteractionUpdate) -> Interaction:
        obj_data = obj_in.dict(exclude_unset=True)
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def delete(self, db: Session, *, interaction_id: int) -> Optional[Interaction]:
        obj = db.query(Interaction).filter(Interaction.id_interaction == interaction_id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def get_by_dossier(self, db: Session, id_dossier: int) -> List[Interaction]:
        return db.query(Interaction).filter(
            Interaction.id_dossier == id_dossier
        ).order_by(desc(Interaction.date_interaction)).all()
    
    def get_recent(self, db: Session, limit: int = 10) -> List[Interaction]:
        return db.query(Interaction).order_by(
            desc(Interaction.date_interaction)
        ).limit(limit).all()
    
    def get_stats(self, db: Session, id_agent: Optional[int] = None) -> dict:
        query = db.query(Interaction)
        if id_agent:
            query = query.filter(Interaction.id_agent == id_agent)
        
        total = query.count()
        succes = query.filter(Interaction.resultat == "Succes").count()
        promesses = query.filter(Interaction.promesse_paiement == True).count()
        montant_promis = db.query(func.sum(Interaction.montant_promis)).filter(
            Interaction.promesse_paiement == True
        ).scalar() or 0.0
        
        return {
            "total_interactions": total,
            "interactions_succes": succes,
            "taux_succes": round((succes / total * 100), 2) if total > 0 else 0,
            "promesses_paiement": promesses,
            "montant_total_promis": montant_promis
        }

interaction = CRUDInteraction()