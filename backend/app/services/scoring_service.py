"""
Service de scoring prédictif — portage du pipeline scoring_zitouna_v3.

Le fichier .pkl est un dict (pas un sklearn Pipeline fusionné) produit par
scoring_zitouna_v3.py :

    {
        "preprocessor": ColumnTransformer,   # fit sur NUM+BIN (StandardScaler) + CAT (OneHotEncoder)
        "model": CalibratedClassifierCV,     # XGBoost calibré (isotonic)
        "model_name": str,
        "threshold": float,                  # seuil optimisé par cost-matrix métier
        "mediane_montant": float,            # seuil pour le flag dette_elevee
        "features": list[str],               # 20 colonnes brutes+engineerées attendues, dans cet ordre
        "feat_names_proc": list[str],
        "num_features": list[str],
        "bin_features": list[str],
        "cat_features": list[str],
        "cost_matrix": dict,
        "metrics": dict,
        "version": str,
        "trained_at": str,
        "dataset": str,
    }

Le modèle a été entraîné sur y = "rembourse" (1 = remboursera) → la classe 1
de predict_proba EST bien la probabilité de recouvrement (pas de défaut) —
correspond directement à `probabilite_recouvrement` ci-dessous.

Les résultats sont persistés dans la table `scorings` existante (un
enregistrement historique par calcul), PAS en colonnes cache sur
DossierClient — Scoring est le modèle prévu à cet effet dans ce schéma.

TODO connus (voir conversation d'intégration) :
  - score_nlp : toujours 0.0 (neutre) tant que le join dossier → reponses_clients
    → analyses_nlp n'est pas câblé (modèle ReponseClient reçu mais join pas
    encore écrit ici).
  - taux_effort : toujours 0.40 (neutre), aucune source dans le schéma actuel.
  - type_client : toujours "Particulier", le schéma ne modélise pas les
    entreprises.
  - region : dérivée de Client.ville tel quel (pas de vrai référentiel région).
  - secteur_activite : toujours "Autre".
  - nb_produits_bancaires : toujours 1.
  - Les 4 paliers de NiveauRisqueEnum (Faible/Moyen/Eleve/Critique) sont une
    proposition de découpage des probabilités continues, en cohérence avec les
    3 paliers de "priorite" (0.60 / 0.35) utilisés côté entraînement — à
    ajuster si besoin, voir seuils dans _niveau_risque().
"""

from __future__ import annotations

import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.creance import Creance
from app.models.dossier_client import DossierClient
from app.models.interaction import Interaction, TypeInteractionEnum
from app.models.scoring import Scoring, NiveauRisqueEnum

# ─── Chargement du modèle ────────────────────────────────────────────────

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml_models" / "scoring_pipeline_zitouna_v3.pkl"

_pipeline_dict = None


def _get_pipeline_dict() -> dict:
    global _pipeline_dict
    if _pipeline_dict is None:
        # Ce .pkl est un dict produit par joblib.dump() (contient des
        # joblib.numpy_pickle.NumpyArrayWrapper pour les tableaux numpy
        # internes du ColumnTransformer/XGBoost) — joblib.load() est requis,
        # pickle.load() brut échoue ou reconstruit mal ces tableaux.
        _pipeline_dict = joblib.load(MODEL_PATH)
    return _pipeline_dict


# ─── Mapping schéma réel → features brutes du pipeline ──────────────────

DEFAULT_TAUX_EFFORT = 0.40
DEFAULT_SECTEUR_ACTIVITE = "Autre"
DEFAULT_NB_PRODUITS_BANCAIRES = 1
DEFAULT_SCORE_NLP = 0.0  # TODO: câbler via reponses_clients → analyses_nlp


def _palier_j(jours_retard: int) -> str:
    if jours_retard <= 30:
        return "J+30"
    elif jours_retard <= 60:
        return "J+60"
    elif jours_retard <= 90:
        return "J+90"
    return "J+120"


def _canal_reponse(interaction_type: Optional[TypeInteractionEnum]) -> str:
    if interaction_type is None:
        return "Aucun"
    mapping = {
        TypeInteractionEnum.SMS: "SMS",
        TypeInteractionEnum.EMAIL: "Email",
    }
    return mapping.get(interaction_type, "Aucun")


def _age(date_naissance: Optional[date]) -> Optional[int]:
    if date_naissance is None:
        return None
    today = date.today()
    return today.year - date_naissance.year - (
        (today.month, today.day) < (date_naissance.month, date_naissance.day)
    )


def build_features_for_dossier(db: Session, dossier: DossierClient) -> Optional[dict]:
    """Construit la ligne de features BRUTES (avant feature engineering) pour
    un dossier donné. Retourne None si le dossier n'a pas de créance active."""
    creance = (
        db.query(Creance)
        .filter(Creance.id_dossier == dossier.id_dossier)
        .order_by(Creance.montant_restant.desc())
        .first()
    )
    if creance is None:
        return None

    client = db.query(Client).filter(Client.id_client == dossier.id_client).first()

    nb_contacts = (
        db.query(func.count(Interaction.id_interaction))
        .filter(Interaction.id_dossier == dossier.id_dossier)
        .scalar()
        or 0
    )
    derniere_interaction = (
        db.query(Interaction)
        .filter(Interaction.id_dossier == dossier.id_dossier)
        .order_by(Interaction.date_interaction.desc())
        .first()
    )

    montant_initial = float(creance.montant_initial or 0)
    montant_paye = float(creance.montant_paye or 0)
    historique_paiement = (montant_paye / montant_initial) if montant_initial > 0 else 0.0

    jours_retard = int(creance.jours_retard or 0)

    return {
        "montant_dette": float(creance.montant_restant or 0),
        "anciennete_dette": jours_retard,
        "palier_j": _palier_j(jours_retard),
        "nb_contacts": int(nb_contacts),
        "canal_reponse": _canal_reponse(derniere_interaction.type if derniere_interaction else None),
        "score_nlp": DEFAULT_SCORE_NLP,
        "historique_paiement": round(historique_paiement, 4),
        "type_client": "Particulier",
        "age_client": _age(client.date_naissance) if client else None,
        "nb_produits_bancaires": DEFAULT_NB_PRODUITS_BANCAIRES,
        "taux_effort": DEFAULT_TAUX_EFFORT,
        "secteur_activite": DEFAULT_SECTEUR_ACTIVITE,
        "region": (client.ville if client and client.ville else "Inconnue"),
    }


def _engineer_features(df: pd.DataFrame, mediane_montant: float) -> pd.DataFrame:
    """Reproduit EXACTEMENT feature_engineering() de scoring_zitouna_v3.py —
    les 7 colonnes dérivées attendues par le preprocessor entraîné."""
    df = df.copy()
    df["score_nlp_positif"] = (df["score_nlp"] > 0).astype(int)
    df["dette_elevee"] = (df["montant_dette"] > mediane_montant).astype(int)
    df["contact_intensif"] = (df["nb_contacts"] >= 5).astype(int)
    df["palier_critique"] = df["palier_j"].isin(["J+90", "J+120"]).astype(int)
    df["historique_bon"] = (df["historique_paiement"] > 0.40).astype(int)
    df["score_x_historique"] = df["score_nlp"] * df["historique_paiement"]
    df["effort_x_montant"] = df["taux_effort"] * np.log1p(df["montant_dette"])
    return df


# ─── Scoring ──────────────────────────────────────────────────────────────

def _niveau_risque(proba: float) -> NiveauRisqueEnum:
    # Découpage en 4 paliers, en cohérence avec les seuils de "priorite"
    # (0.60 / 0.35) utilisés dans le script d'entraînement — étendu à 4
    # niveaux pour matcher NiveauRisqueEnum. proba = P(remboursera).
    if proba >= 0.60:
        return NiveauRisqueEnum.FAIBLE
    elif proba >= 0.45:
        return NiveauRisqueEnum.MOYEN
    elif proba >= 0.30:
        return NiveauRisqueEnum.ELEVE
    return NiveauRisqueEnum.CRITIQUE


def score_dossier(db: Session, dossier: DossierClient, persist: bool = False) -> Optional[dict]:
    """Score un dossier. Si persist=True, crée un enregistrement Scoring."""
    raw_features = build_features_for_dossier(db, dossier)
    if raw_features is None:
        return None

    pipeline_dict = _get_pipeline_dict()
    preprocessor = pipeline_dict["preprocessor"]
    model = pipeline_dict["model"]
    mediane_montant = pipeline_dict["mediane_montant"]
    feature_order = pipeline_dict["features"]  # ordre exact des 20 colonnes attendues

    df = pd.DataFrame([raw_features])
    df = _engineer_features(df, mediane_montant)
    df = df[feature_order]  # sélectionne/ordonne exactement comme à l'entraînement

    X = preprocessor.transform(df)
    proba = float(model.predict_proba(X)[0, 1])  # P(rembourse=1) = probabilité de recouvrement

    niveau = _niveau_risque(proba)
    score_risque = round(proba * 100)

    result = {
        "id_dossier": dossier.id_dossier,
        "score_risque": score_risque,
        "niveau_risque": niveau,
        "probabilite_recouvrement": round(proba, 4),
        "facteurs_cles": raw_features,
    }

    if persist:
        scoring_row = Scoring(
            id_dossier=dossier.id_dossier,
            score_risque=score_risque,
            niveau_risque=niveau,
            probabilite_recouvrement=round(proba, 4),
            date_calcul=datetime.utcnow(),
            modele_version=pipeline_dict.get("version", "3.0.0"),
            facteurs_cles=raw_features,
        )
        db.add(scoring_row)

    return result


def recalculate_all(db: Session) -> tuple[int, float]:
    """Score tous les dossiers actifs et crée un nouvel enregistrement Scoring pour chacun."""
    start = time.time()
    dossiers = db.query(DossierClient).all()
    count = 0
    for dossier in dossiers:
        result = score_dossier(db, dossier, persist=True)
        if result is not None:
            count += 1
    db.commit()
    return count, round(time.time() - start, 2)


def get_latest_scoring(db: Session, id_dossier: int) -> Optional[Scoring]:
    return (
        db.query(Scoring)
        .filter(Scoring.id_dossier == id_dossier)
        .order_by(Scoring.date_calcul.desc())
        .first()
    )


def get_model_meta() -> dict:
    pipeline_dict = _get_pipeline_dict()
    return {
        "nom": pipeline_dict.get("model_name", "XGBoost Calibré"),
        "seuil": pipeline_dict.get("threshold", 0.0606),
    }