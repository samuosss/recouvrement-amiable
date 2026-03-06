from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.agent_auto import AgentAuto, TypeAgentEnum, StatutAgentEnum
from app.schemas.agent_auto import AgentAutoCreate, AgentAutoUpdate

def get_agent(db: Session, agent_id: int) -> Optional[AgentAuto]:
    return db.query(AgentAuto).filter(AgentAuto.id_agent == agent_id).first()

def get_agent_by_nom(db: Session, nom_agent: str) -> Optional[AgentAuto]:
    return db.query(AgentAuto).filter(AgentAuto.nom_agent == nom_agent).first()

def get_agents(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    type_agent: Optional[TypeAgentEnum] = None,
    statut: Optional[StatutAgentEnum] = None
) -> List[AgentAuto]:
    query = db.query(AgentAuto)
    
    if type_agent:
        query = query.filter(AgentAuto.type == type_agent)
    if statut:
        query = query.filter(AgentAuto.statut == statut)
    
    return query.offset(skip).limit(limit).all()

def create_agent(db: Session, agent: AgentAutoCreate) -> AgentAuto:
    db_agent = AgentAuto(
        **agent.dict(),
        statut=StatutAgentEnum.INACTIF,
        messages_traites=0
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

def update_agent(
    db: Session,
    agent_id: int,
    agent_update: AgentAutoUpdate
) -> Optional[AgentAuto]:
    db_agent = get_agent(db, agent_id)
    if not db_agent:
        return None
    
    for field, value in agent_update.dict(exclude_unset=True).items():
        setattr(db_agent, field, value)
    
    db.commit()
    db.refresh(db_agent)
    return db_agent

def delete_agent(db: Session, agent_id: int) -> bool:
    db_agent = get_agent(db, agent_id)
    if not db_agent:
        return False
    
    db.delete(db_agent)
    db.commit()
    return True

def changer_statut(
    db: Session,
    agent_id: int,
    nouveau_statut: StatutAgentEnum
) -> Optional[AgentAuto]:
    """Changer le statut d'un agent"""
    db_agent = get_agent(db, agent_id)
    if not db_agent:
        return None
    
    db_agent.statut = nouveau_statut
    
    db.commit()
    db.refresh(db_agent)
    return db_agent

def incrementer_messages_traites(
    db: Session,
    agent_id: int,
    nombre: int = 1
) -> Optional[AgentAuto]:
    """Incrémenter le compteur de messages traités"""
    db_agent = get_agent(db, agent_id)
    if not db_agent:
        return None
    
    db_agent.messages_traites += nombre
    db_agent.date_dernier_run = datetime.now()
    
    db.commit()
    db.refresh(db_agent)
    return db_agent

def get_agent_stats(db: Session, agent_id: int) -> dict:
    """Obtenir les statistiques d'un agent"""
    agent = get_agent(db, agent_id)
    if not agent:
        return None
    
    taux_utilisation = (agent.messages_traites / agent.capacite_max * 100) if agent.capacite_max > 0 else 0
    
    return {
        "id_agent": agent.id_agent,
        "nom_agent": agent.nom_agent,
        "type": agent.type.value,
        "statut": agent.statut.value,
        "messages_traites": agent.messages_traites,
        "capacite_max": agent.capacite_max,
        "taux_utilisation": round(taux_utilisation, 2),
        "date_dernier_run": agent.date_dernier_run
    }

def get_agents_actifs(db: Session) -> List[AgentAuto]:
    """Récupérer tous les agents actifs"""
    return db.query(AgentAuto).filter(
        AgentAuto.statut == StatutAgentEnum.ACTIF
    ).all()
