from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, JSON
from sqlalchemy.sql import func
import enum

from app.core.database import Base

class TypeTemplateEnum(str, enum.Enum):
    SMS = "SMS"
    EMAIL = "Email"
    NOTIFICATION = "Notification"

class Template(Base):
    __tablename__ = "templates"
    
    id_template = Column(Integer, primary_key=True, index=True)
    nom_template = Column(String(100), nullable=False)
    type_template = Column(Enum(TypeTemplateEnum), nullable=False)
    objet = Column(String(255))  # Pour les emails
    corps = Column(Text, nullable=False)
    variables_disponibles = Column(JSON)
    actif = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
