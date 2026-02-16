from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.region import Region
from app.models.agence import Agence
from app.models.utilisateur import Utilisateur
from app.models.client import Client
from app.models.dossier_client import DossierClient
from app.models.affectation_dossier import AffectationDossier
from app.models.creance import Creance
from app.models.interaction import Interaction
from app.models.campagne import Campagne
from app.models.campagne_client import CampagneClient
from app.models.template import Template
from app.models.message import Message
from app.models.reponse_client import ReponseClient
from app.models.scoring import Scoring
from app.models.recommandation import Recommandation
from app.models.analyse_nlp import AnalyseNLP
from app.models.agent_auto import AgentAuto
from app.models.alerte import Alerte
from app.models.tracabilite import Tracabilite

__all__ = [
    "Base",
    "TimestampMixin",
    "Region",
    "Agence",
    "Utilisateur",
    "Client",
    "DossierClient",
    "AffectationDossier",
    "Creance",
    "Interaction",
    "Campagne",
    "CampagneClient",
    "Template",
    "Message",
    "ReponseClient",
    "Scoring",
    "Recommandation",
    "AnalyseNLP",
    "AgentAuto",
    "Alerte",
    "Tracabilite",
]
