from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class TypeInteractionEnum(str, enum.Enum):
    APPEL = "Appel"
    EMAIL = "Email"
    SMS = "SMS"
    VISITE = "Visite"
    COURRIER = "Courrier"
    AUTRE = "Autre"

class Interaction(Base, TimestampMixin):
    __tablename__ = "interactions"
    
    id_interaction = Column(Integer, primary_key=True, index=True)
    id_dossier = Column(Integer, ForeignKey("dossiers_clients.id_dossier"), nullable=False)
    id_agent = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), nullable=False)
    type = Column(Enum(TypeInteractionEnum), nullable=False)
    date_interaction = Column(DateTime(timezone=True), nullable=False)
    duree_minutes = Column(Integer)
    resultat = Column(String(100))
    notes = Column(Text)
    promesse_paiement = Column(Boolean, default=False)
    montant_promis = Column(Numeric(15, 2))
    date_promesse = Column(DateTime(timezone=True))
    
    # Relations
    dossier = relationship("DossierClient", backref="interactions")
    agent = relationship("Utilisateur", backref="interactions")
    
    def __repr__(self):
        return f"<Interaction(id={self.id_interaction}, type='{self.type}', dossier_id={self.id_dossier})>"