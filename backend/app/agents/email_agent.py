# app/agents/email_agent.py
"""
Email Agent — Banque Zitouna
Provider : Mailtrap SDK (dev/test)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import mailtrap as mt

logger = logging.getLogger(__name__)

SENDER_NAME   = "Banque Zitouna — Recouvrement"
SENDER_EMAIL  = os.getenv("SENDER_EMAIL", "hello@demomailtrap.co")
MAILTRAP_TOKEN = os.getenv("MAILTRAP_API_TOKEN", "")


def send_email(
    *,
    to: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
) -> dict:
    if not MAILTRAP_TOKEN:
        raise RuntimeError("MAILTRAP_API_TOKEN manquant dans .env")

    mail = mt.Mail(
        sender=mt.Address(email=SENDER_EMAIL, name=SENDER_NAME),
        to=[mt.Address(email=to)],
        subject=subject,
        text=body_text,
        html=body_html or f"<p>{body_text}</p>",
        category="Recouvrement",
    )

    client = mt.MailtrapClient(token=MAILTRAP_TOKEN)
    response = client.send(mail)

    logger.info("Email sent via Mailtrap SDK | to=%s | response=%s", to, response)
    return {"status": "sent", "provider": "mailtrap", "message_id": str(response)}