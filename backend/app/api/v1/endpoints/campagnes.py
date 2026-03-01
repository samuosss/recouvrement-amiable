from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import require_manager
from app.models.campagne import TypeCampagneEnum, StatutCampagneEnum
from app.models.utilisateur import Utilisateur
from app.schemas.campagne import (
    CampagneCreate,
    CampagneUpdate,
    CampagneResponse,
    CampagneStats
)
from app.crud import campagne as crud_campagne

router = APIRouter()

@router.get("/", response_model=List[CampagneResponse])
def get_campagnes(
    skip: int = 0,
    limit: int = 100,
    statut: Optional[StatutCampagneEnum] = None,
    type_campagne: Optional[TypeCampagneEnum] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les campagnes"""
    return crud_campagne.get_campagnes(
        db,
        skip=skip,
        limit=limit,
        statut=statut,
        type_campagne=type_campagne
    )

@router.get("/{campagne_id}", response_model=CampagneResponse)
def get_campagne(
    campagne_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer une campagne par ID"""
    campagne = crud_campagne.get_campagne(db, campagne_id)
    
    if not campagne:
        raise HTTPException(status_code=404, detail="Campagne non trouvée")
    
    return campagne

@router.post("/", response_model=CampagneResponse, status_code=status.HTTP_201_CREATED)
def create_campagne(
    campagne: CampagneCreate,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Créer une nouvelle campagne
    
    Permissions: Managers uniquement
    
    Critères de ciblage supportés:
```json
    {
        "statut_dossier": ["Actif", "Suspendu"],
        "priorite": ["Haute", "Moyenne"],
        "montant_min": 5000,
        "montant_max": 50000
    }
```
    """
    return crud_campagne.create_campagne(db, campagne, current_user.id_utilisateur)

@router.put("/{campagne_id}", response_model=CampagneResponse)
def update_campagne(
    campagne_id: int,
    campagne_update: CampagneUpdate,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Mettre à jour une campagne"""
    campagne = crud_campagne.update_campagne(db, campagne_id, campagne_update)
    
    if not campagne:
        raise HTTPException(status_code=404, detail="Campagne non trouvée")
    
    return campagne

@router.delete("/{campagne_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campagne(
    campagne_id: int,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Supprimer une campagne"""
    success = crud_campagne.delete_campagne(db, campagne_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Campagne non trouvée")
    
    return None

@router.post("/{campagne_id}/lancer")
def lancer_campagne(
    campagne_id: int,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """
    Lancer une campagne
    
    - Identifie les clients cibles selon les critères
    - Crée les entrées CampagneClient
    - Passe le statut à "En cours"
    - Les agents automatiques prendront ensuite le relais
    """
    result = crud_campagne.lancer_campagne(db, campagne_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result

@router.get("/{campagne_id}/stats", response_model=CampagneStats)
def get_campagne_stats(
    campagne_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtenir les statistiques d'une campagne"""
    campagne = crud_campagne.get_campagne(db, campagne_id)
    
    if not campagne:
        raise HTTPException(status_code=404, detail="Campagne non trouvée")
    
    stats = crud_campagne.get_campagne_stats(db, campagne_id)
    
    return CampagneStats(
        id_campagne=campagne_id,
        nom_campagne=campagne.nom_campagne,
        **stats
    )

@router.post("/{campagne_id}/pause")
def pause_campagne(
    campagne_id: int,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Mettre en pause une campagne en cours"""
    campagne = crud_campagne.get_campagne(db, campagne_id)
    
    if not campagne:
        raise HTTPException(status_code=404, detail="Campagne non trouvée")
    
    if campagne.statut != StatutCampagneEnum.EN_COURS:
        raise HTTPException(
            status_code=400,
            detail="Seules les campagnes en cours peuvent être mises en pause"
        )
    
    campagne.statut = StatutCampagneEnum.EN_PAUSE
    db.commit()
    
    return {"message": "Campagne mise en pause", "campagne_id": campagne_id}

@router.post("/{campagne_id}/reprendre")
def reprendre_campagne(
    campagne_id: int,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Reprendre une campagne en pause"""
    campagne = crud_campagne.get_campagne(db, campagne_id)
    
    if not campagne:
        raise HTTPException(status_code=404, detail="Campagne non trouvée")
    
    if campagne.statut != StatutCampagneEnum.EN_PAUSE:
        raise HTTPException(
            status_code=400,
            detail="Seules les campagnes en pause peuvent être reprises"
        )
    
    campagne.statut = StatutCampagneEnum.EN_COURS
    db.commit()
    
    return {"message": "Campagne reprise", "campagne_id": campagne_id}
