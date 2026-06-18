# agents/dispatch_engine.py
"""
Dispatch Engine — Banque Zitouna
Orchestre l'envoi Email / SMS / WhatsApp selon le palier J+
et logue chaque envoi dans dispatch_logs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from .email_agent import send_email
from .sms_agent import send_sms
from .whatsapp_agent import send_whatsapp
from .template_engine import render_template
from .logs import log_dispatch

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapping palier → canaux à utiliser
# Clé   : jour_declencheur (J+)
# Valeur: liste de canaux actifs pour ce palier
# ---------------------------------------------------------------------------
PALIER_CHANNELS: dict[int, list[str]] = {
    0:   ["sms"],
    7:   ["sms", "whatsapp"],
    15:  ["email", "sms"],
    30:  ["email", "sms"],
    60:  ["email"],
    90:  ["email", "sms"],
    180: ["email"],          # interne DGA uniquement
}


def dispatch_palier(
    db: Session,
    *,
    id_dossier: str,
    id_creance: int,
    jours_retard: int,
    prenom: str,
    nom: str,
    montant: str,
    echeance: str,
    agent_nom: str = "",
    agent_tel: str = "",
    email_client: Optional[str] = None,
    telephone_client: Optional[str] = None,
    intro: Optional[str] = None,
) -> dict:
    """
    Point d'entrée principal.
    Appelé par le workflow engine à chaque déclenchement de palier.

    Retourne un dict résumant les résultats par canal.
    """
    # Trouver le palier le plus proche dans PALIER_CHANNELS
    palier = _resolve_palier(jours_retard)
    channels = PALIER_CHANNELS.get(palier, ["sms"])

    # Données communes pour tous les templates
    template_data = {
        "prenom":       prenom,
        "nom":          nom,
        "montant":      montant,
        "jours_retard": jours_retard,
        "id_dossier":   id_dossier,
        "echeance":     echeance,
        "agent_nom":    agent_nom,
        "agent_tel":    agent_tel,
        "intro":        intro,
    }

    results: dict[str, dict] = {}

    for channel in channels:
        try:
            result = _dispatch_channel(
                db=db,
                channel=channel,
                palier=palier,
                id_creance=id_creance,
                email_client=email_client,
                telephone_client=telephone_client,
                template_data=template_data,
            )
            results[channel] = result
        except Exception as exc:
            logger.error(
                "Dispatch failed | channel=%s palier=J+%s dossier=%s | %s",
                channel, palier, id_dossier, exc,
            )
            results[channel] = {"status": "error", "error": str(exc)}

    logger.info(
        "Dispatch done | dossier=%s J+%s | channels=%s | results=%s",
        id_dossier, jours_retard, channels, results,
    )
    return results


# ---------------------------------------------------------------------------
# Helpers privés
# ---------------------------------------------------------------------------

def _resolve_palier(jours_retard: int) -> int:
    """
    Retourne le palier exact correspondant à jours_retard.
    Si jours_retard = 17, retourne 15 (le plus proche en dessous).
    """
    paliers_sorted = sorted(PALIER_CHANNELS.keys())
    resolved = 0
    for p in paliers_sorted:
        if jours_retard >= p:
            resolved = p
    return resolved


def _dispatch_channel(
    db: Session,
    *,
    channel: str,
    palier: int,
    id_creance: int,
    email_client: Optional[str],
    telephone_client: Optional[str],
    template_data: dict,
) -> dict:
    """Dispatch sur un canal précis et logue le résultat."""

    sent_at = datetime.now(timezone.utc)

    if channel == "email":
        if not email_client:
            raise ValueError("email_client requis pour canal email")

        subject = render_template(f"email/J{palier}_subject.txt", template_data)
        # Essayer HTML d'abord, fallback texte
        try:
            body_html = render_template(f"email/J{palier}.html", template_data)
            body_text = render_template(f"email/J{palier}.txt", template_data)
        except FileNotFoundError:
            body_html = None
            body_text = render_template(f"email/J{palier}.txt", template_data)

        result = send_email(
            to=email_client,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

    elif channel == "sms":
        if not telephone_client:
            raise ValueError("telephone_client requis pour canal sms")

        message = render_template(f"sms/J{palier}.txt", template_data)
        result = send_sms(to=telephone_client, message=message)

    elif channel == "whatsapp":
        if not telephone_client:
            raise ValueError("telephone_client requis pour canal whatsapp")

        # Template WhatsApp spécifique si dispo, sinon fallback SMS
        try:
            message = render_template(f"sms/J{palier}_whatsapp.txt", template_data)
        except FileNotFoundError:
            message = render_template(f"sms/J{palier}.txt", template_data)

        result = send_whatsapp(to=telephone_client, message=message)

    else:
        raise ValueError(f"Canal inconnu : {channel}")

    # Log en BDD
    log_dispatch(
        db=db,
        id_creance=id_creance,
        canal=channel,
        palier=palier,
        statut=result.get("status", "error"),
        message_id=result.get("message_id"),
        erreur=result.get("error"),
        sent_at=sent_at,
    )

    return result