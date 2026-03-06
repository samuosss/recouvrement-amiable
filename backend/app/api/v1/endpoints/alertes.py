from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.utilisateur import Utilisateur
from app.models.alerte import TypeAlerteEnum, NiveauAlerteEnum
from app.schemas.alerte import (
    AlerteCreate,
    AlerteUpdate,
    AlerteResponse,
    AlerteStats
)
from app.crud import alerte as crud_alerte

router = APIRouter()

@router.get("/", response_model=List[AlerteResponse])
def get_alertes(
    skip: int = 0,
    limit: int = 100,
    niveau: Optional[NiveauAlerteEnum] = None,
    type_alerte: Optional[TypeAlerteEnum] = None,
    lue: Optional[bool] = None,
    traitee: Optional[bool] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer les alertes
    
    Si agent: voir uniquement ses alertes
    Si manager: voir toutes les alertes
    """
    # Si agent, filtrer par utilisateur
    utilisateur_id = current_user.id_utilisateur if current_user.role == "Agent" else None
    
    return crud_alerte.get_alertes(
        db,
        skip=skip,
        limit=limit,
        utilisateur_id=utilisateur_id,
        niveau=niveau,
        type_alerte=type_alerte,
        lue=lue,
        traitee=traitee
    )

@router.get("/non-lues", response_model=List[AlerteResponse])
def get_alertes_non_lues(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer les alertes non lues de l'utilisateur"""
    utilisateur_id = current_user.id_utilisateur if current_user.role == "Agent" else None
    return crud_alerte.get_alertes_non_lues(db, utilisateur_id)

@router.get("/non-traitees", response_model=List[AlerteResponse])
def get_alertes_non_traitees(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer les alertes non traitées"""
    utilisateur_id = current_user.id_utilisateur if current_user.role == "Agent" else None
    return crud_alerte.get_alertes_non_traitees(db, utilisateur_id)

@router.get("/critiques", response_model=List[AlerteResponse])
def get_alertes_critiques(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les alertes critiques non traitées"""
    return crud_alerte.get_alertes_critiques(db)

@router.get("/dossier/{dossier_id}", response_model=List[AlerteResponse])
def get_alertes_dossier(
    dossier_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les alertes d'un dossier"""
    return crud_alerte.get_alertes_dossier(db, dossier_id, skip, limit)

@router.get("/{alerte_id}", response_model=AlerteResponse)
def get_alerte(
    alerte_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer une alerte par ID"""
    alerte = crud_alerte.get_alerte(db, alerte_id)
    
    if not alerte:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    
    # Si agent, vérifier que c'est son alerte
    if current_user.role == "Agent" and alerte.id_utilisateur != current_user.id_utilisateur:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    return alerte

@router.post("/", response_model=AlerteResponse, status_code=status.HTTP_201_CREATED)
def create_alerte(
    alerte: AlerteCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Créer une nouvelle alerte"""
    return crud_alerte.create_alerte(db, alerte)

@router.put("/{alerte_id}", response_model=AlerteResponse)
def update_alerte(
    alerte_id: int,
    alerte_update: AlerteUpdate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mettre à jour une alerte"""
    alerte = crud_alerte.update_alerte(db, alerte_id, alerte_update)
    
    if not alerte:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    
    return alerte

@router.post("/{alerte_id}/lire")
def marquer_lue(
    alerte_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Marquer une alerte comme lue"""
    alerte = crud_alerte.marquer_lue(db, alerte_id)
    
    if not alerte:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    
    return {
        "message": "Alerte marquée comme lue",
        "alerte_id": alerte_id,
        "date_lecture": alerte.date_lecture
    }

@router.post("/{alerte_id}/traiter")
def marquer_traitee(
    alerte_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Marquer une alerte comme traitée"""
    alerte = crud_alerte.marquer_traitee(db, alerte_id)
    
    if not alerte:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    
    return {
        "message": "Alerte marquée comme traitée",
        "alerte_id": alerte_id,
        "date_traitement": alerte.date_traitement
    }

@router.get("/stats/global", response_model=AlerteStats)
def get_stats_alertes(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Statistiques des alertes"""
    # Si agent, stats personnelles uniquement
    utilisateur_id = current_user.id_utilisateur if current_user.role == "Agent" else None
    
    stats = crud_alerte.get_stats_alertes(db, utilisateur_id)
    return AlerteStats(**stats)
