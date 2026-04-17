"""
schemas/affectation.py  — Schémas Pydantic corrigés

Fixes :
  • id_assigneur est Optional (rempli automatiquement depuis current_user côté backend)
  • ReaffectationRequest n'expose plus id_assigneur (évite le bug où le frontend
    devait le fournir manuellement)
  • AffectationCreate accepte date_affectation par défaut à now()
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Base ──────────────────────────────────────────────────────────────────────

class AffectationBase(BaseModel):
    id_dossier:   int
    id_agent:     int
    id_assigneur: Optional[int] = None   # optionnel — injecté par le backend
    motif:        Optional[str] = None
    actif:        bool = True


# ─── Create ────────────────────────────────────────────────────────────────────

class AffectationCreate(AffectationBase):
    date_affectation: datetime = Field(default_factory=datetime.now)


# ─── Update ────────────────────────────────────────────────────────────────────

class AffectationUpdate(BaseModel):
    motif:    Optional[str]      = None
    actif:    Optional[bool]     = None
    date_fin: Optional[datetime] = None


# ─── Response ──────────────────────────────────────────────────────────────────

class AffectationResponse(AffectationBase):
    id_affectation:   int
    date_affectation: datetime
    date_fin:         Optional[datetime] = None
    created_at:       datetime
    updated_at:       Optional[datetime] = None

    class Config:
        from_attributes = True


class AffectationDetailResponse(AffectationResponse):
    """Réponse enrichie avec noms de l'agent, assigneur et numéro de dossier."""
    agent_nom:       Optional[str] = None
    agent_prenom:    Optional[str] = None
    assigneur_nom:   Optional[str] = None
    assigneur_prenom:Optional[str] = None
    dossier_numero:  Optional[str] = None
    client_nom:      Optional[str] = None


# ─── Réaffectation ─────────────────────────────────────────────────────────────

class ReaffectationRequest(BaseModel):
    """
    Requête de réaffectation d'un dossier à un nouvel agent.

    NOTE : id_assigneur est volontairement absent — le backend le récupère
    automatiquement depuis le token JWT (current_user).
    """
    id_dossier:      int
    id_nouvel_agent: int
    motif:           Optional[str] = None   # rendu optionnel côté schéma


# ─── Assignation (alias frontend-friendly) ────────────────────────────────────

class AssignationRequest(BaseModel):
    """
    Corps de la requête POST /affectations/assigner
    Correspond exactement à ce qu'envoie le composant AssignModal du frontend.
    """
    id_dossier: int
    id_agent:   int
    motif:      Optional[str] = None