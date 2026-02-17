from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class StatutDossierEnum(str, enum.Enum):
    ACTIF = "Actif"
    CLOTURE = "Cloture"
    SUSPENDU = "Suspendu"
    EN_LITIGE = "EnLitige"

class PrioriteEnum(str, enum.Enum):
    BASSE = "Basse"
    NORMALE = "Normale"
    HAUTE = "Haute"
    CRITIQUE = "Critique"

class DossierClient(Base, TimestampMixin):
    __tablename__ = "dossiers_clients"
    
    id_dossier = Column(Integer, primary_key=True, index=True)
    id_client = Column(Integer, ForeignKey("clients.id_client"), nullable=False)
    numero_dossier = Column(String(50), nullable=False, unique=True, index=True)
    statut = Column(Enum(StatutDossierEnum), nullable=False, default=StatutDossierEnum.ACTIF)
    priorite = Column(Enum(PrioriteEnum), nullable=False, default=PrioriteEnum.NORMALE)
    montant_total_du = Column(Numeric(15, 2), nullable=False, default=0)
    date_ouverture = Column(DateTime(timezone=True), nullable=False)
    date_derniere_action = Column(DateTime(timezone=True))
    notes = Column(String)
    
    # Relations
    client = relationship("Client", backref="dossiers")
    
    def __repr__(self):
        return f"<DossierClient(id={self.id_dossier}, numero='{self.numero_dossier}', statut='{self.statut}')>"