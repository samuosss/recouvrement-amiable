from sqlalchemy import Column, Integer, String, Text, Numeric, Float, Boolean, Date, DateTime, ForeignKey, Enum, JSON
from app.core.database import Base
from app.models.base import TimestampMixin

class Client(Base, TimestampMixin):
    __tablename__ = "clients"
    
    id_client = Column(Integer, primary_key=True, index=True)
    cin = Column(String(20), nullable=False, unique=True, index=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    date_naissance = Column(Date)
    telephone = Column(String(20), nullable=False)
    email = Column(String(100))
    adresse = Column(String(255))
    ville = Column(String(100))
    code_postal = Column(String(10))
    profession = Column(String(100))
    situation_familiale = Column(String(50))
    
    def __repr__(self):
        return f"<Client(id={self.id_client}, cin='{self.cin}', nom='{self.nom} {self.prenom}')>"