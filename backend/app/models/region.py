from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from app.core.database import Base
from app.models.base import TimestampMixin

class Region(Base, TimestampMixin):
    __tablename__ = "regions"
    
    id_region = Column(Integer, primary_key=True, index=True)
    nom_region = Column(String(100), nullable=False, unique=True)
    code_region = Column(String(20), nullable=False, unique=True)
    description = Column(String(255))
    
    def __repr__(self):
        return f"<Region(id={self.id_region}, nom='{self.nom_region}')>"
