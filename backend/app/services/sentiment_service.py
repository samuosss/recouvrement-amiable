"""
Sentiment Analysis Service — App Recouvrement
Modèle : tabularisai/multilingual-sentiment-analysis
Version: 2.1.0 avec extraction d'entités métier
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from functools import lru_cache
from typing import Optional, List, Dict, Any
import time
import re
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

CONFIDENCE_THRESHOLD = 0.40

SENTIMENT_MAP = {
    0: "Very Negative",
    1: "Negative",
    2: "Neutral",
    3: "Positive",
    4: "Very Positive",
}

# ── Post-processing métier ────────────────────────────────────────────────────

KEYWORD_OVERRIDES = [
    {
        "keywords": ["prêt à payer", "je vais payer", "je peux payer", "accord", "je veux régler",
                     "virement", "chèque", "rendez-vous", "arrangement", "facilité", "mensualité",
                     "مستعد", "نخلص", "نحل", "تسوية"],
        "override": "Very Positive",
    },
    {
        "keywords": ["si vous réduisez", "si vous m'accordez", "réduction", "rabais", "50%", "30%",
                     "partiel", "acompte", "en échange"],
        "override": "Positive",
    },
    {
        "keywords": ["perdu mon travail", "au chômage", "licencié", "faillite", "maladie",
                     "hospitalisation", "décès", "divorce", "je n'ai rien", "ma عنديش",
                     "ما عنديش", "والله ما عندي", "بلا خدمة"],
        "override": "Negative",
    },
    {
        "keywords": ["jamais", "harcèlement", "avocat", "tribunal", "plainte", "arnaque",
                     "escroc", "je refuse", "ne paierai pas", "ne dois rien", "faux"],
        "override": "Very Negative",
    },
]

RECOUVREMENT_MAP = {
    "Very Negative": {
        "categorie":           "Agressif / Refus",
        "action":              "escalade_senior",
        "delai_relance_jours": 14,
        "priorite":            "haute",
        "conseil":             "Stopper la relance automatique. Transférer à un agent senior.",
        "badge_color":         "red",
    },
    "Negative": {
        "categorie":           "Détresse / Réticent",
        "action":              "contact_personnalise",
        "delai_relance_jours": 7,
        "priorite":            "haute",
        "conseil":             "Appel empathique. Identifier le blocage, orienter vers cellule sociale si besoin.",
        "badge_color":         "orange",
    },
    "Neutral": {
        "categorie":           "Indécis",
        "action":              "relance_standard",
        "delai_relance_jours": 7,
        "priorite":            "normale",
        "conseil":             "Relance standard avec rappel des modalités de paiement.",
        "badge_color":         "gray",
    },
    "Positive": {
        "categorie":           "Ouvert / Négociation",
        "action":              "proposer_echeancier",
        "delai_relance_jours": 3,
        "priorite":            "normale",
        "conseil":             "Proposer un échéancier adapté. Conclure rapidement.",
        "badge_color":         "blue",
    },
    "Very Positive": {
        "categorie":           "Coopératif",
        "action":              "echeancier_immediat",
        "delai_relance_jours": 1,
        "priorite":            "basse",
        "conseil":             "Débiteur motivé. Envoyer la convention d'échéancier immédiatement.",
        "badge_color":         "green",
    },
    "Incertain": {
        "categorie":           "Incertain (score faible)",
        "action":              "verification_manuelle",
        "delai_relance_jours": 5,
        "priorite":            "normale",
        "conseil":             "Score de confiance trop faible. Révision manuelle recommandée.",
        "badge_color":         "gray",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Extraction d'entités métier
# ─────────────────────────────────────────────────────────────────────────────

def extract_amounts(text: str) -> List[str]:
    """Extrait les montants mentionnés dans le message."""
    amounts = []
    
    patterns = [
        r'\b(\d+(?:[\.,]\d+)?)\s*(TND|DT|دينار|dinars?|dinar)\b',
        r'\b(\d+(?:[\.,]\d+)?)\s*(milliers?|mille)\s*(TND|DT|dinars?)?\b',
        r'\b(mille|cinq cents|deux mille|dix mille)\s*(TND|DT|dinars?)?\b',
        r'\b(\d+(?:[\.,]\d+)?)\s*(€|EUR|euros?)\b',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                amount_str = f"{match[0]} {match[1] if len(match) > 1 else ''}".strip()
            else:
                amount_str = match
            if amount_str and amount_str not in amounts:
                amounts.append(amount_str)
    
    if re.search(r'(payer|verser|régler|rembourser|paye|paiement|promis)', text, re.IGNORECASE):
        solo_numbers = re.findall(r'\b(\d{3,})\b', text)
        for num in solo_numbers:
            if num not in amounts:
                amounts.append(num)
    
    return amounts


def extract_dates(text: str) -> Dict[str, Any]:
    """Extrait les dates mentionnées (absolues et relatives)."""
    now = datetime.now()
    dates = {
        "absolues": [],
        "relatives": [],
        "keywords": []
    }
    
    abs_patterns = [
        r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b',
        r'\b(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})\b',
        r'\b(\d{1,2})\s+(janv|févr|mars|avr|mai|juin|juil|août|sept|oct|nov|déc)\s+(\d{4})?\b',
    ]
    
    for pattern in abs_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            date_str = " ".join(match).strip()
            if date_str and date_str not in dates["absolues"]:
                dates["absolues"].append(date_str)
    
    relative_patterns = [
        (r'demain', 1),
        (r'après-demain', 2),
        (r'dans\s+(\d+)\s+jours?', None),
        (r'dans\s+(\d+)\s+semaines?', None),
        (r'cette semaine', 7),
        (r'la semaine prochaine', 7),
        (r'fin du mois', None),
        (r'le mois prochain', 30),
    ]
    
    for pattern, days_offset in relative_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            if 'dans' in pattern:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    num = int(match.group(1))
                    if 'semaine' in pattern:
                        num *= 7
                    date_calc = (now + timedelta(days=num)).strftime("%Y-%m-%d")
                    dates["relatives"].append({
                        "keyword": pattern.replace(r'\s+', ' ').replace(r'(\d+)', str(num)),
                        "date_calculee": date_calc,
                        "jours": num
                    })
            else:
                if days_offset is not None:
                    date_calc = (now + timedelta(days=days_offset)).strftime("%Y-%m-%d")
                else:
                    date_calc = None
                dates["relatives"].append({
                    "keyword": pattern.replace(r'\s+', ' '),
                    "date_calculee": date_calc
                })
            dates["keywords"].append(pattern.replace(r'\s+', ' '))
    
    return dates


def extract_keywords_metier(text: str, final_label: str) -> Dict[str, List[str]]:
    """Extrait les mots-clés métier spécifiques au recouvrement."""
    text_lower = text.lower()
    
    categories = {
        "paiement": ["payer", "virement", "chèque", "espèces", "carte bancaire", "prélèvement", "نخلص", "دفع"],
        "engagement": ["promesse", "accord", "engagement", "je vais", "je peux", "dès que", "مستعد", "promis"],
        "negociation": ["réduction", "remise", "rabais", "acompte", "partiel", "échéancier", "rééchelonner"],
        "contestation": ["erreur", "faux", "pas d'accord", "conteste", "litige", "réclamation", "je ne dois rien"],
        "difficulte": ["chômage", "licencié", "maladie", "décès", "difficulté", "ما عنديش", "ma عنديش"],
        "agressif": ["harcèlement", "avocat", "tribunal", "plainte", "arnaque", "jamais", "menace"],
        "urgence": ["urgent", "immédiat", "rapidement", "aujourd'hui", "maintenant", "dès que possible"]
    }
    
    found = {}
    for category, keywords in categories.items():
        matches = [kw for kw in keywords if kw in text_lower]
        if matches:
            found[category] = matches
    
    return found


def extract_full_entities(message: str, final_label: str) -> Dict[str, Any]:
    """Fonction principale d'extraction d'entités."""
    return {
        "montants": extract_amounts(message),
        "dates": extract_dates(message),
        "keywords_metier": extract_keywords_metier(message, final_label),
        "longueur_message": len(message),
        "a_mots_cles_metier": len(extract_keywords_metier(message, final_label)) > 0
    }


# ─────────────────────────────────────────────────────────────────────────────
# Chargement modèle
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def load_model():
    print("[INFO] Chargement du modèle...")
    tokenizer = AutoTokenizer.from_pretrained("tabularisai/multilingual-sentiment-analysis")
    model = AutoModelForSequenceClassification.from_pretrained("tabularisai/multilingual-sentiment-analysis")
    model.eval()
    print("[INFO] Modèle prêt.")
    return tokenizer, model


def apply_keyword_override(text: str) -> Optional[str]:
    """Applique les règles métier si un mot-clé est détecté."""
    text_lower = text.lower()
    for rule in KEYWORD_OVERRIDES:
        if any(kw.lower() in text_lower for kw in rule["keywords"]):
            return rule["override"]
    return None


def predict(text: str) -> dict:
    tokenizer, model = load_model()

    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
    with torch.no_grad():
        probs = torch.nn.functional.softmax(model(**inputs).logits, dim=-1)[0]

    predicted_idx = torch.argmax(probs).item()
    model_label = SENTIMENT_MAP[predicted_idx]
    model_score = round(probs[predicted_idx].item(), 4)
    all_scores = {SENTIMENT_MAP[i]: round(probs[i].item(), 4) for i in range(5)}

    override = apply_keyword_override(text)
    if override:
        final_label = override
        override_applied = True
    elif model_score < CONFIDENCE_THRESHOLD:
        final_label = "Incertain"
        override_applied = False
    else:
        final_label = model_label
        override_applied = False

    entities = extract_full_entities(text, final_label)

    return {
        "model_label": model_label,
        "model_score": model_score,
        "final_label": final_label,
        "override_applied": override_applied,
        "all_scores": all_scores,
        "entities": entities,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Schémas Pydantic
# ─────────────────────────────────────────────────────────────────────────────

class AnalyseRequest(BaseModel):
    message: str
    dossier_id: Optional[str] = None
    agent_id: Optional[str] = None


class AnalyseResponse(BaseModel):
    model_label: str
    model_score: float
    all_scores: dict
    override_applied: bool
    final_label: str
    categorie: str
    action: str
    delai_relance_jours: int
    priorite: str
    conseil: str
    badge_color: str
    duree_ms: float
    dossier_id: Optional[str]
    agent_id: Optional[str]
    entities: Optional[dict] = None


# ─────────────────────────────────────────────────────────────────────────────
# API FastAPI
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Sentiment Recouvrement API", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    load_model()


@app.get("/health")
def health():
    return {"status": "ok", "model": "tabularisai/multilingual-sentiment-analysis", "version": "2.1.0"}


@app.post("/analyse", response_model=AnalyseResponse)
def analyser(req: AnalyseRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message vide.")

    t0 = time.time()
    result = predict(req.message)
    duree = round((time.time() - t0) * 1000, 1)
    action = RECOUVREMENT_MAP[result["final_label"]]

    return AnalyseResponse(
        model_label=result["model_label"],
        model_score=result["model_score"],
        all_scores=result["all_scores"],
        override_applied=result["override_applied"],
        final_label=result["final_label"],
        duree_ms=duree,
        dossier_id=req.dossier_id,
        agent_id=req.agent_id,
        entities=result["entities"],
        **action,
    )


@app.post("/analyse/batch")
def analyser_batch(items: list[AnalyseRequest]):
    return [analyser(i) for i in items]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)