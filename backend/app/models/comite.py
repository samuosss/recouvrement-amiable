from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base
from app.models.base import TimestampMixin

class StatutComiteEnum(str, enum.Enum):
    PLANIFIE = "Planifie"
    EN_COURS = "EnCours"
    CLOTURE  = "Cloture"
    ANNULE   = "Annule"

class RoleComiteEnum(str, enum.Enum):
    PRESIDENT   = "President"
    RAPPORTEUR  = "Rapporteur"
    MEMBRE      = "Membre"
    OBSERVATEUR = "Observateur"

class StatutInvitationEnum(str, enum.Enum):
    EN_ATTENTE = "En_attente"
    ACCEPTEE   = "Acceptee"
    REFUSEE    = "Refusee"

class VoteEnum(str, enum.Enum):
    POUR       = "POUR"
    CONTRE     = "CONTRE"
    ABSTENTION = "ABSTENTION"

class TypeMessageEnum(str, enum.Enum):
    MESSAGE = "message"
    SYSTEM  = "system"
    VOTE    = "vote"

class Comite(Base, TimestampMixin):
    __tablename__ = "comites"

    id_comite       = Column(Integer, primary_key=True, index=True)
    id_campagne     = Column(Integer, ForeignKey("campagnes.id_campagne"), nullable=True)
    id_dossier      = Column(Integer, ForeignKey("dossiers_clients.id_dossier"), nullable=True)
    instance        = Column(String(100), nullable=False)
    date_seance     = Column(DateTime(timezone=True), nullable=True)
    lieu            = Column(String(200), nullable=True)
    ordre_du_jour   = Column(Text, nullable=True)
    statut          = Column(Enum(StatutComiteEnum), default=StatutComiteEnum.PLANIFIE, nullable=False)
    decision_finale = Column(Text, nullable=True)
    pv_url          = Column(String(500), nullable=True)
    id_createur     = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), nullable=False)

    membres  = relationship("ComiteMembre",  back_populates="comite", cascade="all, delete-orphan")
    votes    = relationship("ComiteVote",    back_populates="comite", cascade="all, delete-orphan")
    messages = relationship("ComiteMessage", back_populates="comite", cascade="all, delete-orphan")
    createur = relationship("Utilisateur", foreign_keys=[id_createur])

class ComiteMembre(Base, TimestampMixin):
    __tablename__ = "comite_membres"

    id                  = Column(Integer, primary_key=True, index=True)
    id_comite           = Column(Integer, ForeignKey("comites.id_comite"), nullable=False)
    id_utilisateur      = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), nullable=False)
    role_comite         = Column(Enum(RoleComiteEnum), default=RoleComiteEnum.MEMBRE, nullable=False)
    statut_invitation   = Column(Enum(StatutInvitationEnum), default=StatutInvitationEnum.EN_ATTENTE, nullable=False)
    message_invitation  = Column(Text, nullable=True)
    date_reponse        = Column(DateTime(timezone=True), nullable=True)
    commentaire_reponse = Column(Text, nullable=True)

    comite      = relationship("Comite", back_populates="membres")
    utilisateur = relationship("Utilisateur", foreign_keys=[id_utilisateur])

    __table_args__ = (UniqueConstraint("id_comite", "id_utilisateur"),)

class ComiteVote(Base, TimestampMixin):
    __tablename__ = "comite_votes"

    id             = Column(Integer, primary_key=True, index=True)
    id_comite      = Column(Integer, ForeignKey("comites.id_comite"), nullable=False)
    id_utilisateur = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), nullable=False)
    vote           = Column(Enum(VoteEnum), nullable=False)
    commentaire    = Column(Text, nullable=True)
    date_vote      = Column(DateTime(timezone=True), server_default=func.now())

    comite      = relationship("Comite", back_populates="votes")
    utilisateur = relationship("Utilisateur", foreign_keys=[id_utilisateur])

    __table_args__ = (UniqueConstraint("id_comite", "id_utilisateur"),)

class ComiteMessage(Base, TimestampMixin):
    __tablename__ = "comite_messages"

    id             = Column(Integer, primary_key=True, index=True)
    id_comite      = Column(Integer, ForeignKey("comites.id_comite"), nullable=False)
    id_utilisateur = Column(Integer, ForeignKey("utilisateurs.id_utilisateur"), nullable=False)
    contenu        = Column(Text, nullable=False)
    type_message   = Column(Enum(TypeMessageEnum), default=TypeMessageEnum.MESSAGE, nullable=False)

    comite      = relationship("Comite", back_populates="messages")
    utilisateur = relationship("Utilisateur", foreign_keys=[id_utilisateur])