# agents/template_engine.py
"""
Template Engine — Banque Zitouna
Rendu Jinja2 des templates SMS / Email selon le palier J+
"""

from __future__ import annotations

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

# Chemin absolu vers le dossier templates
_TEMPLATES_DIR = Path(__file__).parent / "templates"

_env = Environment(
    loader        = FileSystemLoader(str(_TEMPLATES_DIR)),
    undefined     = StrictUndefined,   # plante si une variable est manquante
    autoescape    = False,             # pas d'autoescape pour les templates texte
    trim_blocks   = True,
    lstrip_blocks = True,
)


def render_template(template_path: str, data: dict) -> str:
    """
    Rend un template Jinja2.

    Args:
        template_path : chemin relatif depuis agents/templates/
                        ex: "sms/J15.txt"  |  "email/J15.html"
        data          : dict des variables à injecter

    Returns:
        Contenu rendu sous forme de chaîne.

    Raises:
        FileNotFoundError : si le template n'existe pas (pour les fallbacks).
    """
    try:
        tmpl = _env.get_template(template_path)
        return tmpl.render(**data).strip()
    except TemplateNotFound as exc:
        raise FileNotFoundError(
            f"Template introuvable : agents/templates/{template_path}"
        ) from exc


def list_templates() -> list[str]:
    """Retourne la liste de tous les templates disponibles (debug)."""
    result = []
    for root, _, files in os.walk(_TEMPLATES_DIR):
        for f in files:
            full = Path(root) / f
            result.append(str(full.relative_to(_TEMPLATES_DIR)))
    return sorted(result)