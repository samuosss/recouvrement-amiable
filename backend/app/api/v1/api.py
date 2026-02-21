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
    auth
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