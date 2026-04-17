from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.comite import (
    StatutComiteEnum, RoleComiteEnum,
    StatutInvitationEnum, VoteEnum, TypeMessageEnum
)

# ── Utilisateur embed ─────────────────────────────────────────────────────────
class UtilisateurEmbed(BaseModel):
    id_utilisateur: int
    nom: str
    prenom: str
    email: str
    role: str
    class Config:
        from_attributes = True

# ── Comite ────────────────────────────────────────────────────────────────────
class ComiteCreate(BaseModel):
    instance: str
    id_campagne: Optional[int] = None
    id_dossier: Optional[int] = None
    date_seance: Optional[datetime] = None
    lieu: Optional[str] = None
    ordre_du_jour: Optional[str] = None

class ComiteUpdate(BaseModel):
    instance: Optional[str] = None
    date_seance: Optional[datetime] = None
    lieu: Optional[str] = None
    ordre_du_jour: Optional[str] = None
    statut: Optional[StatutComiteEnum] = None
    decision_finale: Optional[str] = None

class ComiteResponse(BaseModel):
    id_comite: int
    instance: str
    id_campagne: Optional[int] = None
    id_dossier: Optional[int] = None
    date_seance: Optional[datetime] = None
    lieu: Optional[str] = None
    ordre_du_jour: Optional[str] = None
    statut: StatutComiteEnum
    decision_finale: Optional[str] = None
    pv_url: Optional[str] = None
    id_createur: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True

# ── Membre ────────────────────────────────────────────────────────────────────
class MembreInviteCreate(BaseModel):
    id_utilisateur: int
    role_comite: RoleComiteEnum = RoleComiteEnum.MEMBRE
    message_invitation: Optional[str] = None

class MembreRepondreCreate(BaseModel):
    decision: StatutInvitationEnum  # Acceptee | Refusee
    commentaire: Optional[str] = None

class MembreResponse(BaseModel):
    id: int
    id_comite: int
    id_utilisateur: int
    role_comite: RoleComiteEnum
    statut_invitation: StatutInvitationEnum
    message_invitation: Optional[str] = None
    date_reponse: Optional[datetime] = None
    commentaire_reponse: Optional[str] = None
    utilisateur: Optional[UtilisateurEmbed] = None
    created_at: datetime
    class Config:
        from_attributes = True

# ── Vote ──────────────────────────────────────────────────────────────────────
class VoteCreate(BaseModel):
    vote: VoteEnum
    commentaire: Optional[str] = None

class VoteResponse(BaseModel):
    id: int
    id_comite: int
    id_utilisateur: int
    vote: VoteEnum
    commentaire: Optional[str] = None
    date_vote: datetime
    utilisateur: Optional[UtilisateurEmbed] = None
    class Config:
        from_attributes = True

class VoteTally(BaseModel):
    pour: int
    contre: int
    abstention: int
    total_votes: int
    total_membres: int
    en_attente: int
    quorum_atteint: bool
    tendance: str  # "Favorable" | "Défavorable" | "Indécis" | "En cours"

# ── Message ───────────────────────────────────────────────────────────────────
class MessageCreate(BaseModel):
    contenu: str

class MessageResponse(BaseModel):
    id: int
    id_comite: int
    id_utilisateur: int
    contenu: str
    type_message: TypeMessageEnum
    created_at: datetime
    utilisateur: Optional[UtilisateurEmbed] = None
    class Config:
        from_attributes = True

# ── Invitation detail ─────────────────────────────────────────────────────────
class InvitationDetail(BaseModel):
    membre: MembreResponse
    comite: ComiteResponse
    class Config:
        from_attributes = True