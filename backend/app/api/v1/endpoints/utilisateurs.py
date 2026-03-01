from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import (
    filter_utilisateurs_by_role,
    can_modify_user,
    require_admin,
    require_manager
)
from app.models.utilisateur import Utilisateur, RoleEnum
from app.schemas.utilisateur import (
    UtilisateurCreate,
    UtilisateurUpdate,
    UtilisateurResponse
)
from app.crud import utilisateur as crud_utilisateur

router = APIRouter()

@router.get("/", response_model=List[UtilisateurResponse])
def get_utilisateurs(
    skip: int = 0,
    limit: int = 100,
    role: Optional[RoleEnum] = None,
    agence_id: Optional[int] = None,
    actif: Optional[bool] = None,
    search: Optional[str] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer les utilisateurs selon les permissions
    
    Permissions:
    - Agent: Lui-même uniquement
    - Chef d'Agence: Utilisateurs de son agence
    - Chef Régional: Utilisateurs de sa région
    - DGA/Admin: Tous les utilisateurs
    """
    # Query de base
    query = db.query(Utilisateur)
    
    # Appliquer le filtrage hiérarchique
    query = filter_utilisateurs_by_role(query, current_user, db)
    
    # Filtres additionnels
    if role:
        query = query.filter(Utilisateur.role == role)
    if agence_id:
        query = query.filter(Utilisateur.id_agence == agence_id)
    if actif is not None:
        query = query.filter(Utilisateur.actif == actif)
    if search:
        from sqlalchemy import or_
        query = query.filter(
            or_(
                Utilisateur.nom.ilike(f"%{search}%"),
                Utilisateur.prenom.ilike(f"%{search}%"),
                Utilisateur.email.ilike(f"%{search}%")
            )
        )
    
    return query.offset(skip).limit(limit).all()

@router.get("/{utilisateur_id}", response_model=UtilisateurResponse)
def get_utilisateur(
    utilisateur_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer un utilisateur par ID"""
    db_utilisateur = crud_utilisateur.get_utilisateur(db, utilisateur_id)
    
    if not db_utilisateur:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    # Vérifier les permissions de lecture
    # On vérifie si l'utilisateur cible serait dans la liste filtrée
    query = db.query(Utilisateur).filter(Utilisateur.id_utilisateur == utilisateur_id)
    query = filter_utilisateurs_by_role(query, current_user, db)
    
    if not query.first():
        raise HTTPException(
            status_code=403,
            detail="Vous n'avez pas accès à cet utilisateur"
        )
    
    return db_utilisateur

@router.post("/", response_model=UtilisateurResponse, status_code=status.HTTP_201_CREATED)
def create_utilisateur(
    utilisateur: UtilisateurCreate,
    current_user: Utilisateur = Depends(require_manager),  # Minimum Chef d'Agence
    db: Session = Depends(get_db)
):
    """
    Créer un nouvel utilisateur
    
    Permissions: Chef d'Agence et au-dessus
    """
    # Vérifier si l'email existe déjà
    existing = crud_utilisateur.get_utilisateur_by_email(db, utilisateur.email)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Un utilisateur avec cet email existe déjà"
        )
    
    # Un Chef d'Agence ne peut créer que des Agents dans son agence
    if current_user.role == RoleEnum.CHEF_AGENCE:
        if utilisateur.role != RoleEnum.AGENT:
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez créer que des Agents"
            )
        if utilisateur.id_agence != current_user.id_agence:
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez créer des utilisateurs que dans votre agence"
            )
    
    return crud_utilisateur.create_utilisateur(db, utilisateur)

@router.put("/{utilisateur_id}", response_model=UtilisateurResponse)
def update_utilisateur(
    utilisateur_id: int,
    utilisateur_update: UtilisateurUpdate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mettre à jour un utilisateur"""
    # Récupérer l'utilisateur cible
    target_user = crud_utilisateur.get_utilisateur(db, utilisateur_id)
    
    if not target_user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    # Vérifier les permissions de modification
    if not can_modify_user(current_user, target_user, db):
        raise HTTPException(
            status_code=403,
            detail="Vous n'avez pas le droit de modifier cet utilisateur"
        )
    
    # Un utilisateur peut se modifier lui-même (sauf son rôle)
    if current_user.id_utilisateur == utilisateur_id:
        if utilisateur_update.role and utilisateur_update.role != current_user.role:
            raise HTTPException(
                status_code=403,
                detail="Vous ne pouvez pas changer votre propre rôle"
            )
    
    return crud_utilisateur.update_utilisateur(db, utilisateur_id, utilisateur_update)

@router.delete("/{utilisateur_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_utilisateur(
    utilisateur_id: int,
    current_user: Utilisateur = Depends(require_admin),  # Seulement Admin
    db: Session = Depends(get_db)
):
    """
    Supprimer un utilisateur
    
    Permissions: Admin uniquement
    """
    # Ne pas se supprimer soi-même
    if utilisateur_id == current_user.id_utilisateur:
        raise HTTPException(
            status_code=400,
            detail="Vous ne pouvez pas vous supprimer vous-même"
        )
    
    success = crud_utilisateur.delete_utilisateur(db, utilisateur_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    return None

@router.get("/stats/by-role", response_model=dict)
def get_utilisateurs_stats_by_role(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Statistiques utilisateurs par rôle (selon permissions)"""
    from sqlalchemy import func
    
    # Query filtrée par permissions
    query = db.query(Utilisateur)
    query = filter_utilisateurs_by_role(query, current_user, db)
    
    stats = query.with_entities(
        Utilisateur.role,
        func.count(Utilisateur.id_utilisateur).label('count')
    ).group_by(Utilisateur.role).all()
    
    return {
        "stats": [{"role": stat.role.value, "count": stat.count} for stat in stats],
        "total": sum(stat.count for stat in stats)
    }
