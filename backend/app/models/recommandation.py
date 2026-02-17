from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class CanalOptimalEnum(str, enum.Enum):
    APPEL = "Appel"
    SMS = "SMS"
    EMAIL = "Email"
    VISITE = "Visite"
    COURRIER = "Courrier"

class Recommandation(Base, TimestampMixin):
    __tablename__ = "recommandations"
    
    id_recommandation = Column(Integer, primary_key=True, index=True)
    id_dossier = Column(Integer, ForeignKey("dossiers_clients.id_dossier"), nullable=False)
    id_scoring = Column(Integer, ForeignKey("scorings.id_scoring"))
    strategie_proposee = Column(String(200), nullable=False)
    description = Column(Text)
    canal_optimal = Column(Enum(CanalOptimalEnum), nullable=False)
    timing_optimal = Column(DateTime(timezone=True))
    message_suggere = Column(Text)
    score_confiance = Column(Float, nullable=False)  # 0.0-1.0
    date_creation = Column(DateTime(timezone=True), nullable=False)
    validee = Column(Boolean, default=False)
    id_valideur = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"))
    date_validation = Column(DateTime(timezone=True))
    appliquee = Column(Boolean, default=False)
    
    # Relations
    dossier = relationship("DossierClient", backref="recommandations")
    scoring = relationship("Scoring", backref="recommandations")
    valideur = relationship("Utilisateur", backref="recommandations_validees")
    
    def __repr__(self):
        return f"<Recommandation(id={self.id_recommandation}, strategie='{self.strategie_proposee}', confiance={self.score_confiance})>"