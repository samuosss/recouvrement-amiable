# app/agents/scheduler.py
"""
Scheduler — Banque Zitouna
Tourne chaque matin à 06h00 (heure de Tunis).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.creance import Creance, StatutCreanceEnum
from app.models.dossier_client import DossierClient
from app.models.affectation_dossier import AffectationDossier
from app.models.client import Client
from app.models.utilisateur import Utilisateur

from .dispatch_engine import dispatch_palier, PALIER_CHANNELS
from .logs import already_dispatched

logger = logging.getLogger(__name__)

TZ = "Africa/Tunis"
scheduler = AsyncIOScheduler(timezone=TZ)


# ---------------------------------------------------------------------------
# Job principal — 06h00 chaque matin
# ---------------------------------------------------------------------------

@scheduler.scheduled_job(
    CronTrigger(hour=6, minute=0, timezone=TZ),
    id="dispatch_workflow",
    name="Dispatch J+ quotidien",
    misfire_grace_time=3600,
)
async def run_daily_dispatch() -> None:
    logger.info("[Scheduler] Démarrage — %s", datetime.now(timezone.utc))
    db: Session = SessionLocal()

    try:
        creances = _get_creances_impayees(db)
        logger.info("[Scheduler] %d créances impayées trouvées", len(creances))

        total_sent = total_skipped = total_errors = 0

        for creance in creances:
            try:
                s, sk, e = _process_creance(db, creance)
                total_sent    += s
                total_skipped += sk
                total_errors  += e
            except Exception as exc:
                logger.error("[Scheduler] Erreur créance %s : %s", creance.id_creance, exc)
                total_errors += 1

        db.commit()
        logger.info(
            "[Scheduler] Terminé — envoyés=%d skippés=%d erreurs=%d",
            total_sent, total_skipped, total_errors,
        )

    except Exception as exc:
        db.rollback()
        logger.critical("[Scheduler] Échec critique : %s", exc)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Traitement d'une créance
# ---------------------------------------------------------------------------

def _process_creance(db: Session, creance: Creance) -> tuple[int, int, int]:
    j      = creance.jours_retard
    palier = _resolve_palier(j)

    # ── Dossier ──────────────────────────────────────────────
    dossier: DossierClient | None = (
        db.query(DossierClient)
        .filter(DossierClient.id_dossier == creance.id_dossier)
        .first()
    )
    if not dossier:
        logger.warning("Pas de dossier pour créance %s — skip", creance.id_creance)
        return 0, 1, 0

    # ── Client ───────────────────────────────────────────────
    # DossierClient.id_client → Client (pas "debiteur", c'est "client")
    client: Client | None = (
        db.query(Client)
        .filter(Client.id_client == dossier.id_client)
        .first()
    )
    if not client:
        logger.warning("Pas de client pour dossier %s — skip", dossier.id_dossier)
        return 0, 1, 0

    # ── Agent affecté ─────────────────────────────────────────
    affectation: AffectationDossier | None = (
        db.query(AffectationDossier)
        .filter(
            AffectationDossier.id_dossier == dossier.id_dossier,
            AffectationDossier.actif      == True,
        )
        .first()
    )
    agent: Utilisateur | None = None
    if affectation:
        agent = (
            db.query(Utilisateur)
            .filter(Utilisateur.id_utilisateur == affectation.id_agent)
            .first()
        )

    # ── Canaux du palier ──────────────────────────────────────
    canaux = PALIER_CHANNELS.get(palier, ["sms"])
    sent = skipped = errors = 0

    for canal in canaux:
        # Anti-doublon : skip si déjà envoyé avec succès
        if already_dispatched(db, id_creance=creance.id_creance, palier=palier, canal=canal):
            logger.debug("Already dispatched | créance=%s J+%s %s", creance.id_creance, palier, canal)
            skipped += 1
            continue

        try:
            results = dispatch_palier(
                db               = db,
                id_dossier       = dossier.numero_dossier,   # ex: "DOS-2024-042"
                id_creance       = creance.id_creance,
                jours_retard     = j,
                prenom           = client.prenom,
                nom              = client.nom,
                montant          = _fmt_montant(creance.montant_restant),  # montant encore dû
                echeance         = _fmt_date(creance.date_echeance),
                agent_nom        = f"{getattr(agent, 'prenom', '')} {getattr(agent, 'nom', '')}".strip() if agent else "",
                agent_tel        = getattr(agent, "telephone", "") if agent else "",
                email_client     = client.email or None,
                telephone_client = client.telephone or None,
            )
            if results.get(canal, {}).get("status") == "sent":
                sent += 1
            else:
                skipped += 1
        except Exception as exc:
            logger.error(
                "Dispatch error | créance=%s canal=%s J+%s | %s",
                creance.id_creance, canal, palier, exc,
            )
            errors += 1

    return sent, skipped, errors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_creances_impayees(db: Session) -> list[Creance]:
    return (
        db.query(Creance)
        .filter(
            Creance.statut.in_([
                StatutCreanceEnum.EN_COURS,
                StatutCreanceEnum.PARTIELLEMENT_REGLE,
            ]),
            Creance.jours_retard > 0,
        )
        .all()
    )


def _resolve_palier(jours_retard: int) -> int:
    paliers = sorted([0, 7, 15, 30, 60, 90, 180])
    resolved = 0
    for p in paliers:
        if jours_retard >= p:
            resolved = p
    return resolved


def _fmt_montant(val) -> str:
    try:
        return f"{float(val):,.2f}".replace(",", " ")
    except (TypeError, ValueError):
        return str(val or "0.00")


def _fmt_date(val) -> str:
    if val is None:
        return "—"
    if hasattr(val, "strftime"):
        return val.strftime("%d/%m/%Y")
    return str(val)


# ---------------------------------------------------------------------------
# Démarrage / arrêt (appelés depuis main.py)
# ---------------------------------------------------------------------------

def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("[Scheduler] Démarré — prochain run à 06h00 (%s)", TZ)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[Scheduler] Arrêté")