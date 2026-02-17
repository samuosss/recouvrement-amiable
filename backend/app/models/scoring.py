from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class NiveauRisqueEnum(str, enum.Enum):
    FAIBLE = "Faible"
    MOYEN = "Moyen"
    ELEVE = "Eleve"
    CRITIQUE = "Critique"

class Scoring(Base, TimestampMixin):
    __tablename__ = "scorings"
    
    id_scoring = Column(Integer, primary_key=True, index=True)
    id_dossier = Column(Integer, ForeignKey("dossiers_clients.id_dossier"), nullable=False)
    score_risque = Column(Integer, nullable=False)  # 0-100
    niveau_risque = Column(Enum(NiveauRisqueEnum), nullable=False)
    probabilite_recouvrement = Column(Float, nullable=False)  # 0.0-1.0
    date_calcul = Column(DateTime(timezone=True), nullable=False)
    modele_version = Column(String(50), nullable=False)
    facteurs_cles = Column(JSON)  # Détails des facteurs qui influencent le score
    
    # Relations
    dossier = relationship("DossierClient", backref="scorings")
    
    def __repr__(self):
        return f"<Scoring(id={self.id_scoring}, dossier_id={self.id_dossier}, score={self.score_risque}, niveau='{self.niveau_risque}')>"