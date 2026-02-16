from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class StatutEnvoiEnum(str, enum.Enum):
    EN_ATTENTE = "EnAttente"
    ENVOYE = "Envoye"
    DELIVRE = "Delivre"
    ECHEC = "Echec"
    OUVERT = "Ouvert"
    CLIQUE = "Clique"

class CampagneClient(Base, TimestampMixin):
    __tablename__ = "campagnes_clients"
    
    id = Column(Integer, primary_key=True, index=True)
    id_campagne = Column(Integer, ForeignKey("campagnes.id_campagne"), nullable=False)
    id_dossier = Column(Integer, ForeignKey("dossiers_clients.id_dossier"), nullable=False)
    date_envoi = Column(DateTime(timezone=True))
    date_delivre = Column(DateTime(timezone=True))
    date_ouvert = Column(DateTime(timezone=True))
    date_clique = Column(DateTime(timezone=True))
    statut = Column(Enum(StatutEnvoiEnum), nullable=False, default=StatutEnvoiEnum.EN_ATTENTE)
    canal = Column(String(20))  # SMS ou Email
    
    # Relations
    campagne = relationship("Campagne", backref="clients_campagne")
    dossier = relationship("DossierClient", backref="campagnes_recues")
    
    def __repr__(self):
        return f"<CampagneClient(id={self.id}, campagne_id={self.id_campagne}, statut='{self.statut}')>"