from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class StatutCreanceEnum(str, enum.Enum):
    EN_COURS = "EnCours"
    REGLE = "Regle"
    PARTIELLEMENT_REGLE = "PartiellementRegle"
    EN_LITIGE = "EnLitige"
    IRRECUPERABLE = "Irrecuperable"

class Creance(Base, TimestampMixin):
    __tablename__ = "creances"
    
    id_creance = Column(Integer, primary_key=True, index=True)
    id_dossier = Column(Integer, ForeignKey("dossiers_clients.id_dossier"), nullable=False)
    numero_contrat = Column(String(50), nullable=False, index=True)
    type_credit = Column(String(100), nullable=False)
    montant_initial = Column(Numeric(15, 2), nullable=False)
    montant_restant = Column(Numeric(15, 2), nullable=False)
    montant_paye = Column(Numeric(15, 2), default=0)
    date_echeance = Column(Date, nullable=False)
    date_debut_retard = Column(Date)
    jours_retard = Column(Integer, default=0)
    taux_interet = Column(Numeric(5, 2))
    penalites = Column(Numeric(15, 2), default=0)
    statut = Column(Enum(StatutCreanceEnum), nullable=False, default=StatutCreanceEnum.EN_COURS)
    
    # Relations
    dossier = relationship("DossierClient", backref="creances")
    
    def __repr__(self):
        return f"<Creance(id={self.id_creance}, contrat='{self.numero_contrat}', montant_restant={self.montant_restant})>"