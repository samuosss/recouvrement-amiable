from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class SentimentEnum(str, enum.Enum):
    POSITIF = "Positif"
    NEUTRE = "Neutre"
    NEGATIF = "Negatif"

class AnalyseNLP(Base, TimestampMixin):
    __tablename__ = "analyses_nlp"
    
    id_analyse = Column(Integer, primary_key=True, index=True)
    id_reponse = Column(Integer, ForeignKey("reponses_clients.id_reponse"), nullable=False)
    sentiment = Column(Enum(SentimentEnum), nullable=False)
    score_confiance = Column(Float, nullable=False)  # 0.0-1.0
    intention = Column(String(100))  # Ex: "Promesse paiement", "Contestation", "Demande délai"
    entites_extraites = Column(JSON)  # Dates, montants, personnes extraites du texte
    mots_cles = Column(JSON)  # Liste des mots-clés importants
    date_analyse = Column(DateTime(timezone=True), nullable=False)
    modele_version = Column(String(50))
    
    # Relations
    reponse = relationship("ReponseClient", backref="analyse_nlp")
    
    def __repr__(self):
        return f"<AnalyseNLP(id={self.id_analyse}, sentiment='{self.sentiment}', intention='{self.intention}')>"