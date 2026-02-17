from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class TypeMessageEnum(str, enum.Enum):
    SMS = "SMS"
    EMAIL = "Email"

class StatutMessageEnum(str, enum.Enum):
    EN_ATTENTE = "EnAttente"
    ENVOYE = "Envoye"
    DELIVRE = "Delivre"
    ECHEC = "Echec"
    OUVERT = "Ouvert"
    CLIQUE = "Clique"

class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    
    id_message = Column(Integer, primary_key=True, index=True)
    id_campagne_client = Column(Integer, ForeignKey("campagnes_clients.id"))
    id_dossier = Column(Integer, ForeignKey("dossiers_clients.id_dossier"), nullable=False)
    type = Column(Enum(TypeMessageEnum), nullable=False)
    destinataire = Column(String(100), nullable=False)  # Numéro tél ou email
    sujet = Column(String(255))  # Pour emails
    contenu = Column(Text, nullable=False)
    date_envoi = Column(DateTime(timezone=True))
    date_delivre = Column(DateTime(timezone=True))
    statut = Column(Enum(StatutMessageEnum), nullable=False, default=StatutMessageEnum.EN_ATTENTE)
    id_agent_auto = Column(Integer, ForeignKey("agents_auto.id_agent"))
    code_erreur = Column(String(100))
    message_erreur = Column(Text)
    
    # Relations
    campagne_client = relationship("CampagneClient", backref="messages")
    dossier = relationship("DossierClient", backref="messages")
    agent_auto = relationship("AgentAuto", backref="messages_envoyes")
    
    def __repr__(self):
        return f"<Message(id={self.id_message}, type='{self.type}', statut='{self.statut}')>"