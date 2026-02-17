from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class TypeAgentEnum(str, enum.Enum):
    SMS = "SMS"
    EMAIL = "Email"
    MIXTE = "Mixte"

class StatutAgentEnum(str, enum.Enum):
    ACTIF = "Actif"
    INACTIF = "Inactif"
    PAUSE = "Pause"
    ERREUR = "Erreur"

class AgentAuto(Base, TimestampMixin):
    __tablename__ = "agents_auto"
    
    id_agent = Column(Integer, primary_key=True, index=True)
    nom_agent = Column(String(100), nullable=False, unique=True)
    type = Column(Enum(TypeAgentEnum), nullable=False)
    statut = Column(Enum(StatutAgentEnum), nullable=False, default=StatutAgentEnum.ACTIF)
    capacite_max = Column(Integer, default=100)  # Messages par heure
    messages_traites = Column(Integer, default=0)
    date_dernier_run = Column(DateTime(timezone=True))
    date_prochain_run = Column(DateTime(timezone=True))
    configuration = Column(JSON)  # Paramètres spécifiques
    
    def __repr__(self):
        return f"<AgentAuto(id={self.id_agent}, nom='{self.nom_agent}', statut='{self.statut}')>"