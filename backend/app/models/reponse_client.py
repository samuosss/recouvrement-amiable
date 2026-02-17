from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class CanalReponseEnum(str, enum.Enum):
    SMS = "SMS"
    EMAIL = "Email"
    APPEL = "Appel"
    PORTAIL = "Portail"

class ReponseClient(Base, TimestampMixin):
    __tablename__ = "reponses_clients"
    
    id_reponse = Column(Integer, primary_key=True, index=True)
    id_message = Column(Integer, ForeignKey("messages.id_message"))
    id_dossier = Column(Integer, ForeignKey("dossiers_clients.id_dossier"), nullable=False)
    contenu_brut = Column(Text, nullable=False)
    date_reponse = Column(DateTime(timezone=True), nullable=False)
    canal = Column(Enum(CanalReponseEnum), nullable=False)
    expediteur = Column(String(100))
    
    # Relations
    message = relationship("Message", backref="reponses")
    dossier = relationship("DossierClient", backref="reponses_recues")
    
    def __repr__(self):
        return f"<ReponseClient(id={self.id_reponse}, dossier_id={self.id_dossier}, canal='{self.canal}')>"
