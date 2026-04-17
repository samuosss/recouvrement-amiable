"""
routers/nlp.py — Endpoints NLP / Analyses Sentiment
Version : 2.3.0 — avec alerte automatique sur sentiment négatif

Routes :
  POST /nlp/sauvegarder              ← appelé après chaque analyse de sentiment (crée une alerte si Very Negative/Negative)
  GET  /nlp/stats                    ← distribution globale des sentiments
  GET  /nlp/stats/evolution          ← évolution temporelle (day/week/month)
  GET  /nlp/stats/agent/all          ← stats NLP de tous les agents (manager+)
  GET  /nlp/stats/agent/{agent_id}   ← stats NLP d'un agent spécifique
  GET  /nlp/recent                   ← 100 dernières analyses toutes confondues
  GET  /nlp/reponse/{id}             ← historique NLP d'une réponse client
  GET  /nlp/dossier/{id}             ← toutes les analyses NLP d'un dossier
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_, desc
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.analyse_nlp import AnalyseNLP, SentimentEnum
from app.models.reponse_client import ReponseClient
from app.models.utilisateur import Utilisateur, RoleEnum
from app.models.affectation_dossier import AffectationDossier
from app.models.dossier_client import DossierClient
from app.models.alerte import Alerte, TypeAlerteEnum, NiveauAlerteEnum
from app.schemas.nlp import (
    NLPSauvegarderRequest,
    NLPAnalyseResponse,
    NLPHistoriqueResponse,
)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _map_label_to_sentiment(final_label: str) -> SentimentEnum:
    mapping = {
        "Very Negative": SentimentEnum.NEGATIF,
        "Negative":      SentimentEnum.NEGATIF,
        "Neutral":       SentimentEnum.NEUTRE,
        "Positive":      SentimentEnum.POSITIF,
        "Very Positive": SentimentEnum.POSITIF,
        "Incertain":     SentimentEnum.NEUTRE,
    }
    return mapping.get(final_label, SentimentEnum.NEUTRE)


def _extract_mots_cles(resultat: Dict[str, Any]) -> List[str]:
    keys = []
    action    = resultat.get("action", "")
    categorie = resultat.get("categorie", "")
    if action:    keys.append(action)
    if categorie: keys.append(categorie)
    if resultat.get("override_applied"):
        keys.append("override_regle_metier")

    entities = resultat.get("entities", {})
    if entities.get("montants"):
        keys.append(f"montant_{'_'.join(str(m) for m in entities['montants'][:2])}")
    if entities.get("keywords_metier"):
        for category in entities["keywords_metier"].keys():
            keys.append(f"cat_{category}")
    return keys


def _creer_alerte_non_cooperatif(
    db: Session,
    reponse_id: int,
    dossier_id: int,
    final_label: str,
    message_client: str,
    score: float,
):
    """
    Crée une alerte quand le message est non coopératif (Very Negative ou Negative).
    L'alerte est assignée à l'agent en charge du dossier.
    """
    # Déterminer le niveau et le titre selon le label
    if final_label == "Very Negative":
        niveau = NiveauAlerteEnum.CRITIQUE
        titre = "🚨 Client très agressif - Action urgente"
        type_alerte = TypeAlerteEnum.RISQUE_CRITIQUE
    else:  # Negative
        niveau = NiveauAlerteEnum.WARNING
        titre = "⚠️ Client en détresse / réticent"
        type_alerte = TypeAlerteEnum.RISQUE_CRITIQUE

    # Récupérer l'agent assigné au dossier (affectation active)
    affectation_active = db.query(AffectationDossier).filter(
        AffectationDossier.id_dossier == dossier_id,
        AffectationDossier.actif == True
    ).first()

    agent_id = affectation_active.id_agent if affectation_active else None

    # Extraire un extrait du message (max 100 caractères)
    message_extrait = message_client[:100] + ("..." if len(message_client) > 100 else "")

    # Message détaillé de l'alerte
    message_alerte = (
        f"Analyse NLP détecte un comportement {final_label} "
        f"(confiance: {int(score * 100)}%). "
        f"Message: \"{message_extrait}\". "
        f"Action recommandée: consulter le dossier immédiatement."
    )

    # Créer l'alerte
    alerte = Alerte(
        id_dossier=dossier_id,
        id_utilisateur=agent_id,
        type=type_alerte,
        niveau=niveau,
        titre=titre,
        message=message_alerte,
        date_creation=datetime.now(timezone.utc),
        lue=False,
        traitee=False,
    )
    db.add(alerte)

    return alerte


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES STATIQUES EN PREMIER (ordre critique pour FastAPI)
# ═══════════════════════════════════════════════════════════════════════════════

# ── /nlp/stats ─────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_nlp_stats(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Distribution globale des sentiments sur toutes les analyses sauvegardées.
    Utilisé par le dashboard Analyses.tsx (onglet NLP).
    """
    total = db.query(func.count(AnalyseNLP.id_analyse)).scalar() or 0

    distribution = (
        db.query(AnalyseNLP.sentiment, func.count(AnalyseNLP.id_analyse))
        .group_by(AnalyseNLP.sentiment)
        .all()
    )
    dist_map = {str(row[0].value): row[1] for row in distribution}

    positif = dist_map.get("Positif", 0)
    neutre  = dist_map.get("Neutre",  0)
    negatif = dist_map.get("Negatif", 0)

    return {
        "total_analyses": total,
        "distribution": {
            "Positif": positif,
            "Neutre":  neutre,
            "Negatif": negatif,
        },
        "taux_positif": round(positif / total * 100) if total > 0 else 0,
        "taux_negatif": round(negatif / total * 100) if total > 0 else 0,
        "taux_neutre":  round(neutre  / total * 100) if total > 0 else 0,
    }


# ── /nlp/stats/evolution ───────────────────────────────────────────────────────

@router.get("/stats/evolution")
def get_nlp_stats_evolution(
    period: str = Query("week", description="day | week | month"),
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Évolution temporelle des analyses.
    Retourne les données pour le graphique en barres du dashboard NLP.
    """
    now = datetime.now(timezone.utc)

    if period == "day":
        start_date  = now - timedelta(days=30)
        date_trunc  = func.date_trunc("day",   AnalyseNLP.date_analyse)
        format_str  = "%Y-%m-%d"
    elif period == "week":
        start_date  = now - timedelta(weeks=12)
        date_trunc  = func.date_trunc("week",  AnalyseNLP.date_analyse)
        format_str  = "%Y-W%V"
    else:  # month
        start_date  = now - timedelta(days=180)
        date_trunc  = func.date_trunc("month", AnalyseNLP.date_analyse)
        format_str  = "%Y-%m"

    evolution = (
        db.query(
            date_trunc.label("periode"),
            AnalyseNLP.sentiment,
            func.count(AnalyseNLP.id_analyse).label("count"),
        )
        .filter(AnalyseNLP.date_analyse >= start_date)
        .group_by("periode", AnalyseNLP.sentiment)
        .order_by("periode")
        .all()
    )

    # Structurer par période
    result: List[Dict] = []
    current_periode = None
    period_data: Dict[str, int] = {}

    for row in evolution:
        if row.periode != current_periode:
            if current_periode is not None:
                result.append({
                    "periode": current_periode.strftime(format_str),
                    **period_data,
                })
            current_periode = row.periode
            period_data = {"Positif": 0, "Neutre": 0, "Negatif": 0}

        sentiment_str = row.sentiment.value
        if sentiment_str in period_data:
            period_data[sentiment_str] = row.count

    if current_periode is not None:
        result.append({
            "periode": current_periode.strftime(format_str),
            **period_data,
        })

    return {
        "period": period,
        "data":   result,
        "total":  sum(
            r.get("Positif", 0) + r.get("Neutre", 0) + r.get("Negatif", 0)
            for r in result
        ),
    }


# ── /nlp/stats/agent/all ──────────────────────────────────────────────────────
# NOTE : doit être déclaré AVANT /stats/agent/{agent_id}

@router.get("/stats/agent/all")
def get_all_agents_nlp_stats(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Statistiques NLP agrégées pour tous les agents.
    Réservé aux managers (Chef Agence et au-dessus).

    Retourne un tableau compatible avec NLPAgentsTable du dashboard.
    Format par agent :
      { agent_id, agent_nom, total_analyses, distribution: {Positif, Neutre, Negatif} }
    """
    if current_user.role not in [
        RoleEnum.CHEF_AGENCE,
        RoleEnum.CHEF_REGIONAL,
        RoleEnum.DGA,
        RoleEnum.ADMIN,
    ]:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux managers.",
        )

    # ── Jointure :
    #   AnalyseNLP → ReponseClient → DossierClient → AffectationDossier → Utilisateur
    rows = (
        db.query(
            Utilisateur.id_utilisateur,
            Utilisateur.nom,
            Utilisateur.prenom,
            AnalyseNLP.sentiment,
            func.count(AnalyseNLP.id_analyse).label("count"),
        )
        .join(ReponseClient, AnalyseNLP.id_reponse == ReponseClient.id_reponse)
        .join(DossierClient, ReponseClient.id_dossier == DossierClient.id_dossier)
        .join(
            AffectationDossier,
            and_(
                AffectationDossier.id_dossier == DossierClient.id_dossier,
                AffectationDossier.actif == True,
            ),
        )
        .join(Utilisateur, AffectationDossier.id_agent == Utilisateur.id_utilisateur)
        .filter(Utilisateur.role == RoleEnum.AGENT)
        .group_by(
            Utilisateur.id_utilisateur,
            Utilisateur.nom,
            Utilisateur.prenom,
            AnalyseNLP.sentiment,
        )
        .all()
    )

    # Structurer par agent
    agents_map: Dict[int, Dict] = {}
    for row in rows:
        aid = row.id_utilisateur
        if aid not in agents_map:
            agents_map[aid] = {
                "agent_id":       aid,
                "agent_nom":      f"{row.prenom} {row.nom}",
                "total_analyses": 0,
                "distribution":   {"Positif": 0, "Neutre": 0, "Negatif": 0},
            }
        sval = row.sentiment.value  # "Positif" | "Neutre" | "Negatif"
        agents_map[aid]["distribution"][sval] = row.count
        agents_map[aid]["total_analyses"] += row.count

    agents_list = sorted(
        agents_map.values(),
        key=lambda a: a["total_analyses"],
        reverse=True,
    )

    return {
        "agents":          agents_list,
        "total_agents":    len(agents_list),
        "total_analyses":  sum(a["total_analyses"] for a in agents_list),
    }


# ── /nlp/stats/agent/{agent_id} ───────────────────────────────────────────────

@router.get("/stats/agent/{agent_id}")
def get_nlp_stats_agent(
    agent_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Distribution des sentiments pour un agent spécifique."""
    if current_user.role == RoleEnum.AGENT and agent_id != current_user.id_utilisateur:
        raise HTTPException(
            status_code=403,
            detail="Vous ne pouvez voir que vos propres statistiques.",
        )

    rows = (
        db.query(AnalyseNLP.sentiment, func.count(AnalyseNLP.id_analyse))
        .join(ReponseClient, AnalyseNLP.id_reponse == ReponseClient.id_reponse)
        .join(DossierClient, ReponseClient.id_dossier == DossierClient.id_dossier)
        .join(
            AffectationDossier,
            and_(
                AffectationDossier.id_dossier == DossierClient.id_dossier,
                AffectationDossier.id_agent   == agent_id,
            ),
        )
        .group_by(AnalyseNLP.sentiment)
        .all()
    )

    dist_map = {str(row[0].value): row[1] for row in rows}
    total    = sum(dist_map.values())

    agent = db.query(Utilisateur).filter(
        Utilisateur.id_utilisateur == agent_id
    ).first()
    agent_nom = f"{agent.prenom} {agent.nom}" if agent else f"Agent #{agent_id}"

    return {
        "agent_id":       agent_id,
        "agent_nom":      agent_nom,
        "total_analyses": total,
        "distribution": {
            "Positif": dist_map.get("Positif", 0),
            "Neutre":  dist_map.get("Neutre",  0),
            "Negatif": dist_map.get("Negatif", 0),
        },
    }


# ── /nlp/recent ────────────────────────────────────────────────────────────────

@router.get("/recent")
def get_recent_analyses(
    limit: int = Query(100, ge=1, le=500, description="Nombre d'analyses à retourner"),
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Retourne les N dernières analyses NLP toutes confondues.

    Utilisé par le dashboard Analyses.tsx pour :
    1. Construire le nuage de mots-clés (keywords_metier des entités extraites)
    2. Afficher les dernières analyses (section "Dernières analyses")

    Chaque item contient :
      - id_analyse, sentiment, score_confiance, intention
      - entites_extraites (contient keywords_metier, montants, dates, conseil, badge_color, categorie)
      - mots_cles
      - date_analyse
      - canal (via ReponseClient)
      - message (via ReponseClient.contenu si disponible)
    """
    rows = (
        db.query(AnalyseNLP, ReponseClient)
        .join(ReponseClient, AnalyseNLP.id_reponse == ReponseClient.id_reponse)
        .order_by(desc(AnalyseNLP.date_analyse))
        .limit(limit)
        .all()
    )

    analyses = []
    for analyse, reponse in rows:
        entites = analyse.entites_extraites or {}
        analyses.append({
            "id_analyse":        analyse.id_analyse,
            "id_reponse":        analyse.id_reponse,
            "sentiment":         analyse.sentiment.value,
            "score_confiance":   analyse.score_confiance,
            "intention":         analyse.intention,
            "entites_extraites": entites,
            "mots_cles":         analyse.mots_cles or [],
            "date_analyse":      analyse.date_analyse.isoformat(),
            # Champs issus de ReponseClient
            "canal":             reponse.canal if hasattr(reponse, "canal") else None,
            "message":           reponse.contenu if hasattr(reponse, "contenu") else None,
        })

    return {
        "analyses": analyses,
        "total":    len(analyses),
    }


# ── /nlp/sauvegarder ──────────────────────────────────────────────────────────
# ✅ VERSION AVEC ALERTE AUTOMATIQUE

@router.post("/sauvegarder", response_model=NLPAnalyseResponse)
def sauvegarder_analyse(
    payload: NLPSauvegarderRequest,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Sauvegarde le résultat d'une analyse NLP en base.
    Appelé automatiquement par le frontend après chaque analyse de sentiment.

    ⚠️ Si le sentiment est "Very Negative" ou "Negative", une alerte est automatiquement
    créée et assignée à l'agent en charge du dossier.
    """
    reponse = db.query(ReponseClient).filter(
        ReponseClient.id_reponse == payload.id_reponse
    ).first()
    if not reponse:
        raise HTTPException(status_code=404, detail="Réponse client introuvable.")

    nlp = payload.resultat_nlp
    final_label = nlp.get("final_label", "Neutral")

    sentiment  = _map_label_to_sentiment(final_label)
    score      = float(nlp.get("model_score", 0.0))
    intention  = nlp.get("action", None)
    if intention:
        intention = intention.replace("_", " ").title()

    entities_data = nlp.get("entities", {})

    entites = {
        "all_scores":        nlp.get("all_scores", {}),
        "override_applied":  nlp.get("override_applied", False),
        "badge_color":       nlp.get("badge_color", "gray"),
        "priorite":          nlp.get("priorite", ""),
        "delai_relance_jours": nlp.get("delai_relance_jours", 7),
        "conseil":           nlp.get("conseil", ""),
        "categorie":         nlp.get("categorie", ""),
        # Entités extraites
        "montants":          entities_data.get("montants", []),
        "dates":             entities_data.get("dates", {}),
        "keywords_metier":   entities_data.get("keywords_metier", {}),
        "longueur_message":  entities_data.get("longueur_message", len(payload.message)),
        "a_mots_cles_metier": entities_data.get("a_mots_cles_metier", False),
    }

    mots_cles = _extract_mots_cles(nlp)
    keywords_metier = entities_data.get("keywords_metier", {})
    for category, keywords in keywords_metier.items():
        mots_cles.extend(keywords)
    for montant in entities_data.get("montants", []):
        mots_cles.append(f"montant_{montant}")
    mots_cles = list(set(mots_cles))

    analyse = AnalyseNLP(
        id_reponse        = payload.id_reponse,
        sentiment         = sentiment,
        score_confiance   = score,
        intention         = intention,
        entites_extraites = entites,
        mots_cles         = mots_cles,
        date_analyse      = datetime.now(timezone.utc),
        modele_version    = "tabularisai/multilingual-sentiment-analysis-v2",
    )
    db.add(analyse)
    db.flush()  # Pour obtenir l'ID de l'analyse si besoin

    # ✅ NOUVEAU : Créer une alerte si sentiment non coopératif
    if final_label in ["Very Negative", "Negative"]:
        _creer_alerte_non_cooperatif(
            db=db,
            reponse_id=payload.id_reponse,
            dossier_id=reponse.id_dossier,
            final_label=final_label,
            message_client=payload.message,
            score=score,
        )

    db.commit()
    db.refresh(analyse)
    return analyse


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES DYNAMIQUES EN DERNIER
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/reponse/{reponse_id}", response_model=NLPHistoriqueResponse)
def get_analyses_reponse(
    reponse_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Historique des analyses NLP d'une réponse client spécifique."""
    analyses = (
        db.query(AnalyseNLP)
        .filter(AnalyseNLP.id_reponse == reponse_id)
        .order_by(desc(AnalyseNLP.date_analyse))
        .all()
    )
    return {
        "id_reponse": reponse_id,
        "analyses":   analyses,
        "total":      len(analyses),
    }


@router.get("/dossier/{dossier_id}")
def get_analyses_dossier(
    dossier_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Toutes les analyses NLP des réponses d'un dossier."""
    resultats = (
        db.query(AnalyseNLP, ReponseClient)
        .join(ReponseClient, AnalyseNLP.id_reponse == ReponseClient.id_reponse)
        .filter(ReponseClient.id_dossier == dossier_id)
        .order_by(desc(AnalyseNLP.date_analyse))
        .all()
    )

    return {
        "dossier_id": dossier_id,
        "total":      len(resultats),
        "analyses": [
            {
                "id_analyse":      a.id_analyse,
                "id_reponse":      a.id_reponse,
                "canal":           r.canal if hasattr(r, "canal") else None,
                "date_reponse":    r.date_reponse.isoformat() if hasattr(r, "date_reponse") and r.date_reponse else None,
                "sentiment":       a.sentiment.value,
                "score_confiance": a.score_confiance,
                "intention":       a.intention,
                "entites":         a.entites_extraites,
                "mots_cles":       a.mots_cles,
                "date_analyse":    a.date_analyse.isoformat(),
            }
            for a, r in resultats
        ],
    }