"""
schemas/nlp.py — Schémas Pydantic pour les analyses NLP
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─── Sauvegarde (reçu du frontend après analyse sentiment) ────────────────────

class NLPSauvegarderRequest(BaseModel):
    """
    Corps de POST /nlp/sauvegarder
    Le frontend envoie le résultat brut du service NLP + l'id de la réponse client.
    """
    id_reponse:    int
    message:       str                        # texte analysé (pour archivage)
    resultat_nlp:  Dict[str, Any]             # réponse brute du sentiment_service


# ─── Réponse ──────────────────────────────────────────────────────────────────

class NLPAnalyseResponse(BaseModel):
    id_analyse:         int
    id_reponse:         int
    sentiment:          str
    score_confiance:    float
    intention:          Optional[str]         = None
    entites_extraites:  Optional[Dict]        = None
    mots_cles:          Optional[List[str]]   = None
    date_analyse:       datetime
    modele_version:     Optional[str]         = None
    created_at:         datetime

    class Config:
        from_attributes = True


# ─── Historique d'une réponse client ─────────────────────────────────────────

class NLPHistoriqueResponse(BaseModel):
    id_reponse:  int
    analyses:    List[NLPAnalyseResponse]
    total:       int