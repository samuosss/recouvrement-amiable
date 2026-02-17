from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class TypeCampagneEnum(str, enum.Enum):
    SMS = "SMS"
    EMAIL = "Email"
    MIXTE = "Mixte"

class StatutCampagneEnum(str, enum.Enum):
    PLANIFIEE = "Planifiee"
    EN_COURS = "EnCours"
    TERMINEE = "Terminee"
    ANNULEE = "Annulee"

class Campagne(Base, TimestampMixin):
    __tablename__ = "campagnes"
    
    id_campagne = Column(Integer, primary_key=True, index=True)
    nom_campagne = Column(String(200), nullable=False)
    description = Column(Text)
    type = Column(Enum(TypeCampagneEnum), nullable=False)
    date_debut = Column(DateTime(timezone=True), nullable=False)
    date_fin = Column(DateTime(timezone=True))
    statut = Column(Enum(StatutCampagneEnum), nullable=False, default=StatutCampagneEnum.PLANIFIEE)
    criteres_segmentation = Column(JSON)  # Stocke les critères de sélection des clients
    nombre_cibles = Column(Integer, default=0)
    nombre_envoyes = Column(Integer, default=0)
    nombre_delivres = Column(Integer, default=0)
    nombre_ouverts = Column(Integer, default=0)
    nombre_cliques = Column(Integer, default=0)
    id_template = Column(Integer)  # ForeignKey ajouté après création du modèle Template
    
    def __repr__(self):
        return f"<Campagne(id={self.id_campagne}, nom='{self.nom_campagne}', statut='{self.statut}')>"