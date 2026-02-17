from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class TypeAlerteEnum(str, enum.Enum):
    RISQUE_CRITIQUE = "RisqueCritique"
    ECHEANCE_PROCHE = "EcheanceProche"
    PROMESSE_NON_TENUE = "PromesseNonTenue"
    REASSIGNATION_FREQUENTE = "ReassignationFrequente"
    TENTATIVE_CONTACT_ECHOUEE = "TentativeContactEchouee"
    AUTRE = "Autre"

class NiveauAlerteEnum(str, enum.Enum):
    INFO = "Info"
    WARNING = "Warning"
    CRITIQUE = "Critique"

class Alerte(Base, TimestampMixin):
    __tablename__ = "alertes"
    
    id_alerte = Column(Integer, primary_key=True, index=True)
    id_dossier = Column(Integer, ForeignKey("dossiers_clients.id_dossier"))
    id_utilisateur = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"))
    type = Column(Enum(TypeAlerteEnum), nullable=False)
    niveau = Column(Enum(NiveauAlerteEnum), nullable=False, default=NiveauAlerteEnum.INFO)
    titre = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    date_creation = Column(DateTime(timezone=True), nullable=False)
    lue = Column(Boolean, default=False)
    date_lecture = Column(DateTime(timezone=True))
    traitee = Column(Boolean, default=False)
    date_traitement = Column(DateTime(timezone=True))
    
    # Relations
    dossier = relationship("DossierClient", backref="alertes")
    utilisateur = relationship("Utilisateur", backref="alertes_recues")
    
    def __repr__(self):
        return f"<Alerte(id={self.id_alerte}, type='{self.type}', niveau='{self.niveau}', lue={self.lue})>"