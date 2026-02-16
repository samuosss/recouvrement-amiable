from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin

class Agence(Base, TimestampMixin):
    __tablename__ = "agences"
    
    id_agence = Column(Integer, primary_key=True, index=True)
    nom_agence = Column(String(100), nullable=False)
    code_agence = Column(String(20), nullable=False, unique=True)
    adresse = Column(String(255))
    telephone = Column(String(20))
    email = Column(String(100))
    id_region = Column(Integer, ForeignKey("regions.id_region"), nullable=False)
    
    # Relations
    region = relationship("Region", backref="agences")
    
    def __repr__(self):
        return f"<Agence(id={self.id_agence}, nom='{self.nom_agence}')>"