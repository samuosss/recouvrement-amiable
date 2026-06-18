# agents/logs.py
"""
Dispatch Logs — Banque Zitouna
Modèle SQLAlchemy + fonction d'écriture pour la table dispatch_logs.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, DateTime, Enum, ForeignKey,
    Integer, String, Text,
)
from sqlalchemy.orm import Session

# Importer Base depuis ton projet existant
# Adapter le chemin si nécessaire
from app.core.database import Base


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------

class StatutDispatchEnum(str, enum.Enum):
    SENT    = "sent"
    SKIPPED = "skipped"
    ERROR   = "error"


class CanalEnum(str, enum.Enum):
    EMAIL     = "email"
    SMS       = "sms"
    WHATSAPP  = "whatsapp"


# ---------------------------------------------------------------------------
# Modèle SQLAlchemy
# ---------------------------------------------------------------------------

class DispatchLog(Base):
    """
    Trace chaque tentative d'envoi de communication vers un débiteur.
    Utile pour :
      - Éviter les doublons (ne pas envoyer 2x le même palier)
      - Statistiques de délivrabilité dans Analyses.tsx
      - Audit trail réglementaire
    """
    __tablename__ = "dispatch_logs"

    id            = Column(Integer, primary_key=True, index=True)
    id_creance    = Column(Integer, ForeignKey("creances.id_creance"), nullable=False, index=True)
    canal         = Column(Enum(CanalEnum), nullable=False)
    palier        = Column(Integer, nullable=False)        # J+ ex: 0, 7, 15...
    statut        = Column(Enum(StatutDispatchEnum), nullable=False)
    message_id    = Column(String(255), nullable=True)     # ID provider (Brevo, AT...)
    erreur        = Column(Text, nullable=True)
    sent_at       = Column(DateTime(timezone=True), nullable=False)
    created_at    = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Fonction d'écriture
# ---------------------------------------------------------------------------

def log_dispatch(
    db: Session,
    *,
    id_creance: int,
    canal: str,
    palier: int,
    statut: str,
    message_id: Optional[str] = None,
    erreur: Optional[str] = None,
    sent_at: Optional[datetime] = None,
) -> DispatchLog:
    """
    Insère un enregistrement dans dispatch_logs.
    Ne commite pas — le commit est géré par l'appelant (workflow engine).
    """
    entry = DispatchLog(
        id_creance = id_creance,
        canal      = canal,
        palier     = palier,
        statut     = statut,
        message_id = message_id,
        erreur     = erreur,
        sent_at    = sent_at or datetime.now(timezone.utc),
    )
    db.add(entry)
    return entry


def already_dispatched(
    db: Session,
    *,
    id_creance: int,
    palier: int,
    canal: str,
) -> bool:
    """
    Vérifie si un envoi réussi existe déjà pour cette créance / palier / canal.
    Permet d'éviter les doublons en cas de relance du scheduler.
    """
    return (
        db.query(DispatchLog)
        .filter(
            DispatchLog.id_creance == id_creance,
            DispatchLog.palier     == palier,
            DispatchLog.canal      == canal,
            DispatchLog.statut     == StatutDispatchEnum.SENT,
        )
        .first()
    ) is not None