# app/api/v1/endpoints/dispatch.py
"""
Router Dispatch — Banque Zitouna
Endpoints pour tester et déclencher manuellement le moteur de dispatch.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.agents.sms_agent import send_sms
from app.agents.email_agent import send_email
from app.agents.logs import DispatchLog, StatutDispatchEnum

router = APIRouter(prefix="/dispatch", tags=["Dispatch"])


# ---------------------------------------------------------------------------
# Schemas Pydantic
# ---------------------------------------------------------------------------

class TestSMSRequest(BaseModel):
    telephone: str
    message: str = "Test SMS — Banque Zitouna Recouvrement"


class TestEmailRequest(BaseModel):
    email: str
    sujet: str = "Test Email — Banque Zitouna"
    corps: str = "Ceci est un email de test depuis le système de recouvrement."


class DispatchStatResponse(BaseModel):
    total: int
    envoyes: int
    skipped: int
    erreurs: int
    par_canal: dict


# ---------------------------------------------------------------------------
# POST /dispatch/test/sms
# ---------------------------------------------------------------------------

@router.post("/test/sms", summary="Tester l'envoi d'un SMS")
def test_sms(body: TestSMSRequest):
    try:
        result = send_sms(to=body.telephone, message=body.message)
        return {"statut": "ok", "detail": result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ---------------------------------------------------------------------------
# POST /dispatch/test/email
# ---------------------------------------------------------------------------

@router.post("/test/email", summary="Tester l'envoi d'un email")
def test_email(body: TestEmailRequest):
    try:
        result = send_email(
            to=body.email,
            subject=body.sujet,
            body_text=body.corps,
            body_html=f"<p>{body.corps}</p>",
        )
        return {"statut": "ok", "detail": result}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


# ---------------------------------------------------------------------------
# GET /dispatch/stats
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=DispatchStatResponse, summary="Statistiques de dispatch")
def get_dispatch_stats(
    depuis: Optional[str] = Query(None, description="Date ISO début ex: 2025-01-01"),
    db: Session = Depends(get_db),
):
    query = db.query(DispatchLog)

    if depuis:
        try:
            dt = datetime.fromisoformat(depuis).replace(tzinfo=timezone.utc)
            query = query.filter(DispatchLog.sent_at >= dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Format de date invalide. Utiliser ISO ex: 2025-01-01")

    logs = query.all()

    total   = len(logs)
    envoyes = sum(1 for l in logs if l.statut == StatutDispatchEnum.SENT)
    skipped = sum(1 for l in logs if l.statut == StatutDispatchEnum.SKIPPED)
    erreurs = sum(1 for l in logs if l.statut == StatutDispatchEnum.ERROR)

    par_canal: dict[str, int] = {}
    for log in logs:
        canal = log.canal.value if hasattr(log.canal, "value") else str(log.canal)
        par_canal[canal] = par_canal.get(canal, 0) + 1

    return DispatchStatResponse(
        total=total,
        envoyes=envoyes,
        skipped=skipped,
        erreurs=erreurs,
        par_canal=par_canal,
    )


# ---------------------------------------------------------------------------
# GET /dispatch/logs
# ---------------------------------------------------------------------------

@router.get("/logs", summary="Historique des dispatches")
def get_dispatch_logs(
    id_creance: Optional[int] = Query(None),
    canal: Optional[str] = Query(None),
    statut: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(DispatchLog)

    if id_creance:
        query = query.filter(DispatchLog.id_creance == id_creance)
    if canal:
        query = query.filter(DispatchLog.canal == canal)
    if statut:
        query = query.filter(DispatchLog.statut == statut)

    logs = query.order_by(DispatchLog.sent_at.desc()).limit(limit).all()

    return [
        {
            "id": l.id,
            "id_creance": l.id_creance,
            "canal": l.canal,
            "palier": l.palier,
            "statut": l.statut,
            "message_id": l.message_id,
            "erreur": l.erreur,
            "sent_at": l.sent_at,
        }
        for l in logs
    ]