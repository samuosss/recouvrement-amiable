# agents/sms_agent.py
"""
SMS Agent — Banque Zitouna
Provider : Africa's Talking (sandbox gratuit illimité + production Tunisie)
Fallback  : TextBelt (1 SMS/jour clé free — tests unitaires uniquement)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import africastalking
import httpx

logger = logging.getLogger(__name__)

AT_USERNAME  = os.getenv("AT_USERNAME", "sandbox")
AT_API_KEY   = os.getenv("AT_API_KEY", "")
AT_SENDER_ID = os.getenv("AT_SENDER_ID", "BqZitouna")

# Initialisation unique du SDK Africa's Talking
_at_initialized = False


def _init_at() -> None:
    global _at_initialized
    if not _at_initialized and AT_API_KEY:
        africastalking.initialize(username=AT_USERNAME, api_key=AT_API_KEY)
        _at_initialized = True


# ---------------------------------------------------------------------------
# Point d'entrée public
# ---------------------------------------------------------------------------

def send_sms(*, to: str, message: str) -> dict:
    """
    Envoie un SMS.
    Provider principal : Africa's Talking
    Fallback           : TextBelt (si AT_API_KEY absent)
    """
    if AT_API_KEY:
        try:
            return _send_via_at(to=to, message=message)
        except Exception as exc:
            logger.warning("Africa's Talking failed (%s), trying TextBelt", exc)

    return _send_via_textbelt(to=to, message=message)


# ---------------------------------------------------------------------------
# Africa's Talking
# ---------------------------------------------------------------------------

def _send_via_at(*, to: str, message: str) -> dict:
    _init_at()
    sms = africastalking.SMS

    # Normaliser le numéro en +216XXXXXXXX
    normalized = _normalize_phone(to)

    response = sms.send(
        message    = message,
        recipients = [normalized],
        sender_id  = AT_SENDER_ID if AT_USERNAME != "sandbox" else None,
    )

    recipients = response.get("SMSMessageData", {}).get("Recipients", [])
    if not recipients:
        raise RuntimeError(f"AT: aucun destinataire dans la réponse — {response}")

    recipient = recipients[0]
    status    = recipient.get("status", "Unknown")

    if status not in ("Success", "Sent"):
        raise RuntimeError(f"AT: statut inattendu '{status}' pour {normalized}")

    message_id = recipient.get("messageId", "")
    logger.info(
        "SMS sent via AT | to=%s | status=%s | messageId=%s",
        normalized, status, message_id,
    )
    return {
        "status":     "sent",
        "provider":   "africas_talking",
        "message_id": message_id,
    }


# ---------------------------------------------------------------------------
# TextBelt (fallback tests unitaires)
# ---------------------------------------------------------------------------

def _send_via_textbelt(*, to: str, message: str) -> dict:
    normalized = _normalize_phone(to)
    r = httpx.post(
        "https://textbelt.com/text",
        data={
            "phone":   normalized,
            "message": message,
            "key":     "textbelt",   # clé gratuite = 1 SMS/jour
        },
        timeout=10,
    )
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"TextBelt error: {data.get('error')}")

    logger.info("SMS sent via TextBelt | to=%s", normalized)
    return {
        "status":     "sent",
        "provider":   "textbelt",
        "message_id": str(data.get("textId", "")),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_phone(phone: str) -> str:
    """
    Normalise un numéro tunisien vers le format +216XXXXXXXX.
    Accepte : 0021698XXXXXX | 21698XXXXXX | 98XXXXXX | +21698XXXXXX
    """
    cleaned = phone.strip().replace(" ", "").replace("-", "")

    if cleaned.startswith("+"):
        return cleaned

    if cleaned.startswith("00216"):
        return "+" + cleaned[2:]

    if cleaned.startswith("216"):
        return "+" + cleaned

    # Numéro local à 8 chiffres — on ajoute l'indicatif Tunisie
    if len(cleaned) == 8:
        return "+216" + cleaned

    return "+" + cleaned