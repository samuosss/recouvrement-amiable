from fastapi import APIRouter
from app.api.v1.endpoints import (
    clients, 
    dossiers, 
    creances, 
    interactions,
    agences,
    regions, 
    utilisateurs,
    affectations,
    auth,
    templates,
    campagnes,
    campagne_clients,
    messages,
    agents_auto,
    alertes, 
    tracabilite,
    dashboard,
    reponses_clients,
    comites,
    nlp,
    analytics
)

api_router = APIRouter()
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["🔐 Authentification"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(dossiers.router, prefix="/dossiers", tags=["dossiers"])
api_router.include_router(creances.router, prefix="/creances", tags=["créances"])
api_router.include_router(interactions.router, prefix="/interactions", tags=["interactions"])
api_router.include_router(agences.router, prefix="/agences", tags=["agences"])
api_router.include_router(regions.router, prefix="/regions", tags=["régions"])
api_router.include_router(utilisateurs.router, prefix="/utilisateurs", tags=["utilisateurs"])
api_router.include_router(affectations.router, prefix="/affectations", tags=["affectations"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(campagnes.router, prefix="/campagnes", tags=["campagnes"])
api_router.include_router(campagne_clients.router, prefix="/campagne-clients", tags=["campagne-clients"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(agents_auto.router, prefix="/agents-auto", tags=["agents-auto"])
api_router.include_router(alertes.router, prefix="/alertes", tags=["alertes"])
api_router.include_router(tracabilite.router, prefix="/tracabilite", tags=["tracabilite"])  
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(reponses_clients.router, prefix="/reponses-clients", tags=["réponses clients"])
api_router.include_router(comites.router, prefix="/comites", tags=["comités"])
api_router.include_router(nlp.router, prefix="/nlp", tags=["NLP"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
    