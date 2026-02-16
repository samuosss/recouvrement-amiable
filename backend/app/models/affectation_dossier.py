from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class AffectationDossier(Base, TimestampMixin):
    __tablename__ = "affectations_dossiers"
    
    id_affectation = Column(Integer, primary_key=True, index=True)
    id_dossier = Column(Integer, ForeignKey("dossiers_clients.id_dossier"), nullable=False)
    id_agent = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), nullable=False)
    id_assigneur = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), nullable=False)
    date_affectation = Column(DateTime(timezone=True), nullable=False)
    date_fin = Column(DateTime(timezone=True))
    motif = Column(String(255))
    actif = Column(Boolean, default=True, nullable=False)
    
    # Relations
    dossier = relationship("DossierClient", backref="affectations")
    agent = relationship("Utilisateur", foreign_keys=[id_agent], backref="dossiers_affectes")
    assigneur = relationship("Utilisateur", foreign_keys=[id_assigneur], backref="affectations_effectuees")
    
    def __repr__(self):
        return f"<AffectationDossier(id={self.id_affectation}, dossier_id={self.id_dossier}, agent_id={self.id_agent})>"