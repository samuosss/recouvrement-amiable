from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class TypeTemplateEnum(str, enum.Enum):
    SMS = "SMS"
    EMAIL = "Email"

class Template(Base, TimestampMixin):
    __tablename__ = "templates"
    
    id_template = Column(Integer, primary_key=True, index=True)
    nom = Column(String(200), nullable=False, unique=True)
    description = Column(Text)
    type = Column(Enum(TypeTemplateEnum), nullable=False)
    sujet = Column(String(255))  # Pour les emails
    contenu = Column(Text, nullable=False)
    variables = Column(JSON)  # Liste des variables disponibles: {nom_client}, {montant_du}, etc.
    langue = Column(String(10), default="fr")
    actif = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Template(id={self.id_template}, nom='{self.nom}', type='{self.type}')>"