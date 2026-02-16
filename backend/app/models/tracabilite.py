from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class ActionEnum(str, enum.Enum):
    CREATION = "Creation"
    MODIFICATION = "Modification"
    SUPPRESSION = "Suppression"
    CONSULTATION = "Consultation"
    AFFECTATION = "Affectation"
    REASSIGNATION = "Reassignation"

class Tracabilite(Base, TimestampMixin):
    __tablename__ = "tracabilite"
    
    id_trace = Column(Integer, primary_key=True, index=True)
    table_cible = Column(String(100), nullable=False, index=True)
    id_enregistrement = Column(Integer, nullable=False, index=True)
    action = Column(Enum(ActionEnum), nullable=False)
    id_utilisateur = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), nullable=False)
    date_action = Column(DateTime(timezone=True), nullable=False)
    anciennes_valeurs = Column(JSON)
    nouvelles_valeurs = Column(JSON)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    description = Column(Text)
    
    # Relations
    utilisateur = relationship("Utilisateur", backref="traces_audit")
    
    def __repr__(self):
        return f"<Tracabilite(id={self.id_trace}, table='{self.table_cible}', action='{self.action}', user_id={self.id_utilisateur})>"