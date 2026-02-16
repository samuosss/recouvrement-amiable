from fastapi import APIRouter
from app.api.v1.endpoints import clients, dossiers, creances, interactions

api_router = APIRouter()

api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(dossiers.router, prefix="/dossiers", tags=["dossiers"])
api_router.include_router(creances.router, prefix="/creances", tags=["créances"])
api_router.include_router(interactions.router, prefix="/interactions", tags=["interactions"])