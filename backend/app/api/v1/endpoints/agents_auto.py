from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import require_manager
from app.models.utilisateur import Utilisateur
from app.models.agent_auto import TypeAgentEnum, StatutAgentEnum
from app.schemas.agent_auto import (
    AgentAutoCreate,
    AgentAutoUpdate,
    AgentAutoResponse,
    AgentAutoStats
)
from app.crud import agent_auto as crud_agent

router = APIRouter()

@router.get("/", response_model=List[AgentAutoResponse])
def get_agents(
    skip: int = 0,
    limit: int = 100,
    type_agent: Optional[TypeAgentEnum] = None,
    statut: Optional[StatutAgentEnum] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer tous les agents automatiques
    
    Note: Structure préparée. Logique d'exécution Phase 4.
    """
    return crud_agent.get_agents(db, skip=skip, limit=limit, type_agent=type_agent, statut=statut)

@router.get("/actifs", response_model=List[AgentAutoResponse])
def get_agents_actifs(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer uniquement les agents actifs"""
    return crud_agent.get_agents_actifs(db)

@router.get("/{agent_id}", response_model=AgentAutoResponse)
def get_agent(
    agent_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer un agent par ID"""
    agent = crud_agent.get_agent(db, agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent non trouvé")
    
    return agent

@router.post("/", response_model=AgentAutoResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    agent: AgentAutoCreate,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Créer un nouvel agent automatique
    
    Permissions: Managers uniquement
    """
    # Vérifier si le nom existe déjà
    existing = crud_agent.get_agent_by_nom(db, agent.nom_agent)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Un agent avec ce nom existe déjà"
        )
    
    return crud_agent.create_agent(db, agent)

@router.put("/{agent_id}", response_model=AgentAutoResponse)
def update_agent(
    agent_id: int,
    agent_update: AgentAutoUpdate,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Mettre à jour un agent automatique"""
    agent = crud_agent.update_agent(db, agent_id, agent_update)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent non trouvé")
    
    return agent

@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: int,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Supprimer un agent automatique"""
    success = crud_agent.delete_agent(db, agent_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Agent non trouvé")
    
    return None

@router.post("/{agent_id}/activer")
def activer_agent(
    agent_id: int,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Activer un agent automatique"""
    agent = crud_agent.changer_statut(db, agent_id, StatutAgentEnum.ACTIF)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent non trouvé")
    
    return {
        "message": "Agent activé",
        "agent_id": agent_id,
        "statut": "Actif",
        "note": "Logique d'exécution sera implémentée en Phase 4"
    }

@router.post("/{agent_id}/desactiver")
def desactiver_agent(
    agent_id: int,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Désactiver un agent automatique"""
    agent = crud_agent.changer_statut(db, agent_id, StatutAgentEnum.INACTIF)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent non trouvé")
    
    return {
        "message": "Agent désactivé",
        "agent_id": agent_id,
        "statut": "Inactif"
    }

@router.post("/{agent_id}/pause")
def mettre_en_pause(
    agent_id: int,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Mettre un agent en pause"""
    agent = crud_agent.changer_statut(db, agent_id, StatutAgentEnum.PAUSE)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent non trouvé")
    
    return {
        "message": "Agent en pause",
        "agent_id": agent_id,
        "statut": "Pause"
    }

@router.get("/{agent_id}/stats", response_model=AgentAutoStats)
def get_agent_stats(
    agent_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtenir les statistiques d'un agent"""
    stats = crud_agent.get_agent_stats(db, agent_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Agent non trouvé")
    
    return AgentAutoStats(**stats)
