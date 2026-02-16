from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class RoleEnum(str, enum.Enum):
    AGENT = "Agent"
    CHEF_AGENCE = "ChefAgence"
    CHEF_REGIONAL = "ChefRegional"
    DGA = "DGA"
    ADMIN = "Admin"

class Utilisateur(Base, TimestampMixin):
    __tablename__ = "utilisateurs"
    
    id_utilisateur = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True, index=True)
    mot_de_passe = Column(String(255), nullable=False)  # Hash bcrypt
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.AGENT)
    telephone = Column(String(20))
    id_agence = Column(Integer, ForeignKey("agences.id_agence"))
    actif = Column(Boolean, default=True, nullable=False)
    
    # Relations
    agence = relationship("Agence", backref="utilisateurs")
    
    def __repr__(self):
        return f"<Utilisateur(id={self.id_utilisateur}, nom='{self.nom} {self.prenom}', role='{self.role}')>"