from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from app.models.comite import (
    Comite, ComiteMembre, ComiteVote, ComiteMessage,
    StatutComiteEnum, StatutInvitationEnum, VoteEnum,
    RoleComiteEnum, TypeMessageEnum
)
from app.schemas.comite import (
    ComiteCreate, ComiteUpdate, MembreInviteCreate,
    MembreRepondreCreate, VoteCreate, MessageCreate, VoteTally
)

# ── Comite CRUD ───────────────────────────────────────────────────────────────
def get_comite(db: Session, comite_id: int) -> Optional[Comite]:
    return db.query(Comite).filter(Comite.id_comite == comite_id).first()

def get_comites(db: Session, skip: int = 0, limit: int = 100) -> List[Comite]:
    return db.query(Comite).order_by(Comite.created_at.desc()).offset(skip).limit(limit).all()

def create_comite(db: Session, comite: ComiteCreate, createur_id: int) -> Comite:
    db_comite = Comite(**comite.dict(), id_createur=createur_id)
    db.add(db_comite)
    db.commit()
    db.refresh(db_comite)
    return db_comite

def update_comite(db: Session, comite_id: int, update: ComiteUpdate) -> Optional[Comite]:
    db_comite = get_comite(db, comite_id)
    if not db_comite:
        return None
    for field, value in update.dict(exclude_unset=True).items():
        setattr(db_comite, field, value)
    db.commit()
    db.refresh(db_comite)
    return db_comite

def delete_comite(db: Session, comite_id: int) -> bool:
    db_comite = get_comite(db, comite_id)
    if not db_comite:
        return False
    db.delete(db_comite)
    db.commit()
    return True

def cloturer_comite(db: Session, comite_id: int, decision: Optional[str] = None) -> Optional[Comite]:
    db_comite = get_comite(db, comite_id)
    if not db_comite:
        return None
    db_comite.statut = StatutComiteEnum.CLOTURE
    if decision:
        db_comite.decision_finale = decision
    db.commit()
    db.refresh(db_comite)
    return db_comite

# ── Membres ───────────────────────────────────────────────────────────────────
def get_membres(db: Session, comite_id: int) -> List[ComiteMembre]:
    return db.query(ComiteMembre).options(
        joinedload(ComiteMembre.utilisateur)
    ).filter(ComiteMembre.id_comite == comite_id).all()

def get_membre(db: Session, comite_id: int, utilisateur_id: int) -> Optional[ComiteMembre]:
    return db.query(ComiteMembre).filter(
        ComiteMembre.id_comite == comite_id,
        ComiteMembre.id_utilisateur == utilisateur_id
    ).first()

def inviter_membre(db: Session, comite_id: int, invite: MembreInviteCreate) -> ComiteMembre:
    # Check if already member
    existing = get_membre(db, comite_id, invite.id_utilisateur)
    if existing:
        # Re-invite if refused
        existing.statut_invitation = StatutInvitationEnum.EN_ATTENTE
        existing.role_comite = invite.role_comite
        existing.message_invitation = invite.message_invitation
        db.commit()
        db.refresh(existing)
        return existing

    db_membre = ComiteMembre(
        id_comite=comite_id,
        id_utilisateur=invite.id_utilisateur,
        role_comite=invite.role_comite,
        message_invitation=invite.message_invitation,
        statut_invitation=StatutInvitationEnum.EN_ATTENTE
    )
    db.add(db_membre)
    db.commit()
    db.refresh(db_membre)
    return db_membre

def repondre_invitation(
    db: Session, comite_id: int,
    utilisateur_id: int, reponse: MembreRepondreCreate
) -> Optional[ComiteMembre]:
    db_membre = get_membre(db, comite_id, utilisateur_id)
    if not db_membre:
        return None
    db_membre.statut_invitation = reponse.decision
    db_membre.commentaire_reponse = reponse.commentaire
    db_membre.date_reponse = datetime.now()
    db.commit()
    db.refresh(db_membre)
    return db_membre

def retirer_membre(db: Session, comite_id: int, utilisateur_id: int) -> bool:
    db_membre = get_membre(db, comite_id, utilisateur_id)
    if not db_membre:
        return False
    db.delete(db_membre)
    db.commit()
    return True

def changer_role(
    db: Session, comite_id: int,
    utilisateur_id: int, role: RoleComiteEnum
) -> Optional[ComiteMembre]:
    db_membre = get_membre(db, comite_id, utilisateur_id)
    if not db_membre:
        return None
    db_membre.role_comite = role
    db.commit()
    db.refresh(db_membre)
    return db_membre

# ── Votes ─────────────────────────────────────────────────────────────────────
def get_votes(db: Session, comite_id: int) -> List[ComiteVote]:
    return db.query(ComiteVote).options(
        joinedload(ComiteVote.utilisateur)
    ).filter(ComiteVote.id_comite == comite_id).all()

def get_vote_utilisateur(db: Session, comite_id: int, utilisateur_id: int) -> Optional[ComiteVote]:
    return db.query(ComiteVote).filter(
        ComiteVote.id_comite == comite_id,
        ComiteVote.id_utilisateur == utilisateur_id
    ).first()

def soumettre_vote(
    db: Session, comite_id: int,
    utilisateur_id: int, vote_data: VoteCreate
) -> ComiteVote:
    existing = get_vote_utilisateur(db, comite_id, utilisateur_id)
    if existing:
        existing.vote = vote_data.vote
        existing.commentaire = vote_data.commentaire
        existing.date_vote = datetime.now()
        db.commit()
        db.refresh(existing)
        # Post system message
        _post_system_message(db, comite_id, utilisateur_id, vote_data.vote, modified=True)
        return existing

    db_vote = ComiteVote(
        id_comite=comite_id,
        id_utilisateur=utilisateur_id,
        vote=vote_data.vote,
        commentaire=vote_data.commentaire,
        date_vote=datetime.now()
    )
    db.add(db_vote)
    db.commit()
    db.refresh(db_vote)
    # Post system message
    _post_system_message(db, comite_id, utilisateur_id, vote_data.vote, modified=False)
    return db_vote

def get_tally(db: Session, comite_id: int) -> VoteTally:
    votes = get_votes(db, comite_id)
    membres = get_membres(db, comite_id)
    votants = [m for m in membres if m.role_comite != RoleComiteEnum.OBSERVATEUR]

    pour       = sum(1 for v in votes if v.vote == VoteEnum.POUR)
    contre     = sum(1 for v in votes if v.vote == VoteEnum.CONTRE)
    abstention = sum(1 for v in votes if v.vote == VoteEnum.ABSTENTION)
    total_votes   = len(votes)
    total_membres = len(votants)
    en_attente    = total_membres - total_votes
    quorum        = total_votes >= 3

    if pour > contre:
        tendance = "Favorable"
    elif contre > pour:
        tendance = "Défavorable"
    elif total_votes == 0:
        tendance = "En cours"
    else:
        tendance = "Indécis"

    return VoteTally(
        pour=pour, contre=contre, abstention=abstention,
        total_votes=total_votes, total_membres=total_membres,
        en_attente=en_attente, quorum_atteint=quorum,
        tendance=tendance
    )

# ── Messages ──────────────────────────────────────────────────────────────────
def get_messages(db: Session, comite_id: int) -> List[ComiteMessage]:
    return db.query(ComiteMessage).options(
        joinedload(ComiteMessage.utilisateur)
    ).filter(ComiteMessage.id_comite == comite_id).order_by(
        ComiteMessage.created_at.asc()
    ).all()

def envoyer_message(
    db: Session, comite_id: int,
    utilisateur_id: int, msg: MessageCreate
) -> ComiteMessage:
    db_msg = ComiteMessage(
        id_comite=comite_id,
        id_utilisateur=utilisateur_id,
        contenu=msg.contenu,
        type_message=TypeMessageEnum.MESSAGE
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg

def _post_system_message(
    db: Session, comite_id: int,
    utilisateur_id: int, vote: VoteEnum, modified: bool
) -> None:
    label = {
        VoteEnum.POUR: "a voté POUR",
        VoteEnum.CONTRE: "a voté CONTRE",
        VoteEnum.ABSTENTION: "s'est abstenu(e)"
    }[vote]
    prefix = "a modifié son vote —" if modified else ""
    utilisateur = db.query(
        __import__("app.models.utilisateur", fromlist=["Utilisateur"]).Utilisateur
    ).filter_by(id_utilisateur=utilisateur_id).first()
    nom = f"{utilisateur.prenom} {utilisateur.nom}" if utilisateur else "Un membre"
    contenu = f"{nom} {prefix} {label}."

    db_msg = ComiteMessage(
        id_comite=comite_id,
        id_utilisateur=utilisateur_id,
        contenu=contenu,
        type_message=TypeMessageEnum.VOTE
    )
    db.add(db_msg)
    db.commit()

# ── Invitation by token ───────────────────────────────────────────────────────
def get_invitation_by_id(db: Session, membre_id: int) -> Optional[ComiteMembre]:
    return db.query(ComiteMembre).options(
        joinedload(ComiteMembre.utilisateur),
        joinedload(ComiteMembre.comite)
    ).filter(ComiteMembre.id == membre_id).first()