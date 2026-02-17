from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.schemas.utilisateur import (
    UtilisateurCreate,
    UtilisateurUpdate,
    UtilisateurResponse
)
from app.crud import utilisateur as crud_utilisateur
from app.models.utilisateur import RoleEnum

router = APIRouter()

@router.get("/", response_model=List[UtilisateurResponse])
def get_utilisateurs(
    skip: int = 0,
    limit: int = 100,
    role: Optional[RoleEnum] = None,
    agence_id: Optional[int] = None,
    actif: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Récupérer la liste des utilisateurs avec filtres optionnels
    
    - **role**: Filtrer par rôle (Agent, ChefAgence, etc.)
    - **agence_id**: Filtrer par agence
    - **actif**: Filtrer par statut actif/inactif
    - **search**: Rechercher dans nom, prénom, email
    """
    utilisateurs = crud_utilisateur.get_utilisateurs(
        db=db,
        skip=skip,
        limit=limit,
        role=role,
        agence_id=agence_id,
        actif=actif,
        search=search
    )
    return utilisateurs

@router.get("/{utilisateur_id}", response_model=UtilisateurResponse)
def get_utilisateur(
    utilisateur_id: int,
    db: Session = Depends(get_db)
):
    """Récupérer un utilisateur par ID"""
    db_utilisateur = crud_utilisateur.get_utilisateur(db, utilisateur_id)
    if not db_utilisateur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    return db_utilisateur

@router.post("/", response_model=UtilisateurResponse, status_code=status.HTTP_201_CREATED)
def create_utilisateur(
    utilisateur: UtilisateurCreate,
    db: Session = Depends(get_db)
):
    """
    Créer un nouvel utilisateur
    
    Le mot de passe sera automatiquement hashé avec bcrypt
    """
    # Vérifier si l'email existe déjà
    db_utilisateur = crud_utilisateur.get_utilisateur_by_email(db, utilisateur.email)
    if db_utilisateur:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un utilisateur avec cet email existe déjà"
        )
    
    return crud_utilisateur.create_utilisateur(db, utilisateur)

@router.put("/{utilisateur_id}", response_model=UtilisateurResponse)
def update_utilisateur(
    utilisateur_id: int,
    utilisateur_update: UtilisateurUpdate,
    db: Session = Depends(get_db)
):
    """Mettre à jour un utilisateur"""
    db_utilisateur = crud_utilisateur.update_utilisateur(db, utilisateur_id, utilisateur_update)
    if not db_utilisateur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    return db_utilisateur

@router.delete("/{utilisateur_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_utilisateur(
    utilisateur_id: int,
    db: Session = Depends(get_db)
):
    """Supprimer un utilisateur"""
    success = crud_utilisateur.delete_utilisateur(db, utilisateur_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    return None

@router.get("/agence/{agence_id}/agents", response_model=List[UtilisateurResponse])
def get_agents_by_agence(
    agence_id: int,
    actifs_only: bool = True,
    db: Session = Depends(get_db)
):
    """Récupérer les agents d'une agence spécifique"""
    if actifs_only:
        agents = crud_utilisateur.get_agents_actifs(db, agence_id)
    else:
        agents = crud_utilisateur.get_utilisateurs_by_agence(db, agence_id)
    return agents

@router.get("/stats/by-role", response_model=dict)
def get_utilisateurs_stats_by_role(db: Session = Depends(get_db)):
    """Statistiques utilisateurs par rôle"""
    from sqlalchemy import func
    from app.models.utilisateur import Utilisateur
    
    stats = db.query(
        Utilisateur.role,
        func.count(Utilisateur.id_utilisateur).label('count')
    ).group_by(Utilisateur.role).all()
    
    return {
        "stats": [{"role": stat.role.value, "count": stat.count} for stat in stats],
        "total": sum(stat.count for stat in stats)
    }