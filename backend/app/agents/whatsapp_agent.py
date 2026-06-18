# agents/whatsapp_agent.py
"""
WhatsApp Agent — Banque Zitouna
Provider : UltraMsg (50 msg/mois free tier — démo PFE)
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

ULTRAMSG_INSTANCE = os.getenv("ULTRAMSG_INSTANCE", "")
ULTRAMSG_TOKEN    = os.getenv("ULTRAMSG_TOKEN", "")


# ---------------------------------------------------------------------------
# Point d'entrée public
# ---------------------------------------------------------------------------

def send_whatsapp(*, to: str, message: str) -> dict:
    """
    Envoie un message WhatsApp via UltraMsg.
    Si les credentials sont absents, logue un warning et retourne un mock
    (utile en dev pour ne pas bloquer le dispatch).
    """
    if not ULTRAMSG_INSTANCE or not ULTRAMSG_TOKEN:
        logger.warning(
            "WhatsApp skipped — ULTRAMSG_INSTANCE / ULTRAMSG_TOKEN non configurés"
        )
        return {"status": "skipped", "provider": "ultramsg", "message_id": None}

    return _send_via_ultramsg(to=to, message=message)


# ---------------------------------------------------------------------------
# UltraMsg
# ---------------------------------------------------------------------------

def _send_via_ultramsg(*, to: str, message: str) -> dict:
    # UltraMsg attend le numéro SANS le "+" : "21698000000"
    normalized = _normalize_phone(to)

    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"

    r = httpx.post(
        url,
        data={
            "token": ULTRAMSG_TOKEN,
            "to":    normalized,
            "body":  message,
        },
        timeout=10,
    )

    data = r.json()

    # UltraMsg retourne {"sent": "true", "message": "ok"} en succès
    if str(data.get("sent", "false")).lower() != "true":
        raise RuntimeError(f"UltraMsg error: {data}")

    message_id = str(data.get("id", ""))
    logger.info("WhatsApp sent via UltraMsg | to=%s | id=%s", normalized, message_id)

    return {
        "status":     "sent",
        "provider":   "ultramsg",
        "message_id": message_id,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_phone(phone: str) -> str:
    """
    Normalise un numéro vers le format UltraMsg : 21698XXXXXX (sans +).
    """
    cleaned = phone.strip().replace(" ", "").replace("-", "")

    if cleaned.startswith("+"):
        cleaned = cleaned[1:]

    if cleaned.startswith("00"):
        cleaned = cleaned[2:]

    # Numéro local 8 chiffres → ajouter indicatif
    if len(cleaned) == 8:
        cleaned = "216" + cleaned

    return cleaned