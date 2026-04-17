"""
comites.py — Router Comité avec fixes :
  1. GET /invitations/{membre_id} déplacé AVANT /{comite_id} (fix conflit de route)
  2. POST /{comite_id}/inviter envoie une notification in-app à l'invité
  3. GET /{comite_id}/votes/liste → retourne List[VoteResponse] pour récupérer myVote
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.utilisateur import Utilisateur
from app.models.comite import (
    RoleComiteEnum, StatutComiteEnum, StatutInvitationEnum, ComiteMembre
)
from app.schemas.comite import (
    ComiteCreate, ComiteUpdate, ComiteResponse,
    MembreInviteCreate, MembreRepondreCreate, MembreResponse,
    VoteCreate, VoteResponse, VoteTally,
    MessageCreate, MessageResponse, InvitationDetail
)
from app.crud import comite as crud

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _require_manager(user: Utilisateur):
    allowed = ["Admin", "DGA", "Chef", "ADMIN", "DGA", "CHEF_AGENCE", "CHEF_REGIONAL"]
    if user.role not in allowed:
        raise HTTPException(status_code=403, detail="Accès réservé aux managers")


def _require_membre_accepte(comite_id: int, user: Utilisateur, db: Session):
    membre = db.query(ComiteMembre).filter(
        ComiteMembre.id_comite == comite_id,
        ComiteMembre.id_utilisateur == user.id_utilisateur,
        ComiteMembre.statut_invitation == StatutInvitationEnum.ACCEPTEE
    ).first()
    if not membre and user.role not in ["Admin", "ADMIN"]:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas membre accepté de ce comité")
    return membre


def _send_notification(db: Session, *, destinataire_id: int, titre: str, message: str, reference_id: Optional[int] = None):
    """Envoie une notification in-app. Silencieux si le modèle n'existe pas encore."""
    try:
        from app.models.notification import Notification
        notif = Notification(
            id_destinataire=destinataire_id,
            titre=titre,
            message=message,
            type_notif="comite",
            id_reference=reference_id,
            lue=False,
            date_creation=datetime.now(timezone.utc),
        )
        db.add(notif)
        # Pas de commit ici — le caller committera
    except ImportError:
        pass  # Pas encore de modèle Notification → silencieux


# ═══════════════════════════════════════════════════════════════════════════════
# BLOC 1 — ROUTES STATIQUES EN PREMIER (avant /{comite_id})
# ═══════════════════════════════════════════════════════════════════════════════

# ── ✅ FIX 1 : /invitations/{membre_id} AVANT /{comite_id} ───────────────────
@router.get("/invitations/{membre_id}", response_model=MembreResponse)
def get_invitation(
    membre_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Détail d'une invitation par son ID (utilisé par ComiteInvitation.tsx)."""
    invitation = crud.get_invitation_by_id(db, membre_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation non trouvée")
    return invitation


# ── Liste comités ──────────────────────────────────────────────────────────────
@router.get("/", response_model=List[ComiteResponse])
def get_comites(
    skip: int = 0,
    limit: int = 100,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    return crud.get_comites(db, skip=skip, limit=limit)


# ── Créer comité ───────────────────────────────────────────────────────────────
@router.post("/", response_model=ComiteResponse, status_code=status.HTTP_201_CREATED)
def create_comite(
    comite: ComiteCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_manager(current_user)
    return crud.create_comite(db, comite, current_user.id_utilisateur)


# ═══════════════════════════════════════════════════════════════════════════════
# BLOC 2 — ROUTES DYNAMIQUES /{comite_id} (après les statiques)
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/{comite_id}", response_model=ComiteResponse)
def get_comite(
    comite_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    c = crud.get_comite(db, comite_id)
    if not c:
        raise HTTPException(status_code=404, detail="Comité non trouvé")
    return c


@router.put("/{comite_id}", response_model=ComiteResponse)
def update_comite(
    comite_id: int,
    update: ComiteUpdate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_manager(current_user)
    c = crud.update_comite(db, comite_id, update)
    if not c:
        raise HTTPException(status_code=404, detail="Comité non trouvé")
    return c


@router.delete("/{comite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comite(
    comite_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_manager(current_user)
    if not crud.delete_comite(db, comite_id):
        raise HTTPException(status_code=404, detail="Comité non trouvé")


@router.post("/{comite_id}/cloturer")
def cloturer_comite(
    comite_id: int,
    decision: Optional[str] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_manager(current_user)
    c = crud.cloturer_comite(db, comite_id, decision)
    if not c:
        raise HTTPException(status_code=404, detail="Comité non trouvé")
    return {"message": "Comité clôturé", "comite_id": comite_id, "decision": decision}


# ── Membres ────────────────────────────────────────────────────────────────────

@router.get("/{comite_id}/membres", response_model=List[MembreResponse])
def get_membres(
    comite_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not crud.get_comite(db, comite_id):
        raise HTTPException(status_code=404, detail="Comité non trouvé")
    return crud.get_membres(db, comite_id)


@router.post("/{comite_id}/inviter", response_model=MembreResponse, status_code=status.HTTP_201_CREATED)
def inviter_membre(
    comite_id: int,
    invite: MembreInviteCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_manager(current_user)
    comite = crud.get_comite(db, comite_id)
    if not comite:
        raise HTTPException(status_code=404, detail="Comité non trouvé")

    membre = crud.inviter_membre(db, comite_id, invite)

    # ✅ FIX 2 : notification in-app à l'invité avec lien vers sa page invitation
    _send_notification(
        db,
        destinataire_id=invite.id_utilisateur,
        titre=f"Invitation — {comite.instance}",
        message=(
            f"{current_user.prenom} {current_user.nom} vous invite à participer au {comite.instance} "
            f"en tant que {invite.role_comite}. "
            f"Répondez via : /invitation/{membre.id}"
        ),
        reference_id=membre.id,
    )
    db.commit()  # commit notification + membre en une fois
    db.refresh(membre)
    return membre


@router.post("/{comite_id}/repondre", response_model=MembreResponse)
def repondre_invitation(
    comite_id: int,
    reponse: MembreRepondreCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    membre = crud.repondre_invitation(db, comite_id, current_user.id_utilisateur, reponse)
    if not membre:
        raise HTTPException(status_code=404, detail="Invitation non trouvée")

    # Notifier le créateur du comité
    comite = crud.get_comite(db, comite_id)
    if comite:
        decision_label = "accepté" if reponse.decision == StatutInvitationEnum.ACCEPTEE else "décliné"
        _send_notification(
            db,
            destinataire_id=comite.id_createur,
            titre=f"Réponse invitation — {comite.instance}",
            message=(
                f"{current_user.prenom} {current_user.nom} a {decision_label} "
                f"l'invitation au {comite.instance}."
                f"{f' Motif : {reponse.commentaire}' if reponse.commentaire else ''}"
            ),
            reference_id=comite_id,
        )
        db.commit()

    return membre


@router.put("/{comite_id}/membres/{utilisateur_id}", response_model=MembreResponse)
def changer_role(
    comite_id: int,
    utilisateur_id: int,
    role: RoleComiteEnum,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_manager(current_user)
    membre = crud.changer_role(db, comite_id, utilisateur_id, role)
    if not membre:
        raise HTTPException(status_code=404, detail="Membre non trouvé")
    return membre


@router.delete("/{comite_id}/membres/{utilisateur_id}", status_code=status.HTTP_204_NO_CONTENT)
def retirer_membre(
    comite_id: int,
    utilisateur_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_manager(current_user)
    if not crud.retirer_membre(db, comite_id, utilisateur_id):
        raise HTTPException(status_code=404, detail="Membre non trouvé")


# ── Votes ──────────────────────────────────────────────────────────────────────

@router.get("/{comite_id}/votes", response_model=VoteTally)
def get_tally(
    comite_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Retourne le tally (compteurs agrégés)."""
    if not crud.get_comite(db, comite_id):
        raise HTTPException(status_code=404, detail="Comité non trouvé")
    return crud.get_tally(db, comite_id)


# ✅ FIX 3 : nouvelle route /votes/liste → List[VoteResponse] pour récupérer myVote
@router.get("/{comite_id}/votes/liste", response_model=List[VoteResponse])
def get_votes_liste(
    comite_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Retourne la liste détaillée des votes individuels.
    Utilisé par ComiteCredit.tsx pour connaître le vote de l'utilisateur connecté.
    """
    if not crud.get_comite(db, comite_id):
        raise HTTPException(status_code=404, detail="Comité non trouvé")
    return crud.get_votes(db, comite_id)


@router.post("/{comite_id}/voter", response_model=VoteResponse)
def voter(
    comite_id: int,
    vote_data: VoteCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    membre = _require_membre_accepte(comite_id, current_user, db)
    if membre and membre.role_comite == RoleComiteEnum.OBSERVATEUR:
        raise HTTPException(status_code=403, detail="Les observateurs ne peuvent pas voter")

    comite = crud.get_comite(db, comite_id)
    if not comite:
        raise HTTPException(status_code=404, detail="Comité non trouvé")
    if comite.statut == StatutComiteEnum.CLOTURE:
        raise HTTPException(status_code=400, detail="Le comité est clôturé")

    return crud.soumettre_vote(db, comite_id, current_user.id_utilisateur, vote_data)


# ── Messages ───────────────────────────────────────────────────────────────────

@router.get("/{comite_id}/messages", response_model=List[MessageResponse])
def get_messages(
    comite_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_membre_accepte(comite_id, current_user, db)
    return crud.get_messages(db, comite_id)


@router.post("/{comite_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def envoyer_message(
    comite_id: int,
    msg: MessageCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_membre_accepte(comite_id, current_user, db)
    comite = crud.get_comite(db, comite_id)
    if not comite:
        raise HTTPException(status_code=404, detail="Comité non trouvé")
    if comite.statut == StatutComiteEnum.CLOTURE:
        raise HTTPException(status_code=400, detail="Le comité est clôturé")
    return crud.envoyer_message(db, comite_id, current_user.id_utilisateur, msg)