"""
Système de permissions hiérarchiques

Gère le contrôle d'accès basé sur les rôles (RBAC) pour le système de recouvrement.

Hiérarchie des rôles (du plus restreint au plus large) :
    1. Agent          : Accès à ses dossiers uniquement
    2. Chef d'Agence  : Accès aux dossiers de son agence
    3. Chef Régional  : Accès aux dossiers de sa région
    4. DGA            : Accès à tous les dossiers
    5. Admin          : Accès complet (données + configuration)
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session, Query
from typing import List, Optional

from app.core.security import get_current_active_user
from app.core.database import get_db
from app.models.utilisateur import Utilisateur, RoleEnum
from app.models.dossier_client import DossierClient
from app.models.affectation_dossier import AffectationDossier
from app.models.agence import Agence

# ========================
# VÉRIFICATION DE RÔLES
# ========================

def require_roles(allowed_roles: List[RoleEnum]):
    """
    Decorator pour restreindre l'accès à certains rôles
    
    Usage:
        @router.get("/admin-only")
        def admin_endpoint(user = Depends(require_roles([RoleEnum.ADMIN]))):
            ...
    
    Args:
        allowed_roles: Liste des rôles autorisés
        
    Returns:
        Dependency function pour FastAPI
    """
    async def role_checker(
        current_user: Utilisateur = Depends(get_current_active_user)
    ) -> Utilisateur:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Accès refusé. Rôles autorisés: {[r.value for r in allowed_roles]}"
            )
        return current_user
    
    return role_checker

def require_admin(
    current_user: Utilisateur = Depends(get_current_active_user)
) -> Utilisateur:
    """Nécessite le rôle Admin"""
    if current_user.role != RoleEnum.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs"
        )
    return current_user

def require_manager(
    current_user: Utilisateur = Depends(get_current_active_user)
) -> Utilisateur:
    """Nécessite Chef d'Agence, Chef Régional, DGA ou Admin"""
    allowed_roles = [
        RoleEnum.CHEF_AGENCE,
        RoleEnum.CHEF_REGIONAL,
        RoleEnum.DGA,
        RoleEnum.ADMIN
    ]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux managers"
        )
    return current_user

def require_dga_or_admin(
    current_user: Utilisateur = Depends(get_current_active_user)
) -> Utilisateur:
    """Nécessite DGA ou Admin"""
    if current_user.role not in [RoleEnum.DGA, RoleEnum.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux DGA et administrateurs"
        )
    return current_user

# ========================
# FILTRAGE HIÉRARCHIQUE DES DOSSIERS
# ========================

def filter_dossiers_by_role(
    query: Query,
    user: Utilisateur,
    db: Session
) -> Query:
    """
    Filtrer les dossiers selon le rôle de l'utilisateur
    
    Logique:
        - Agent: Dossiers où il est agent actif
        - Chef d'Agence: Dossiers des agents de son agence
        - Chef Régional: Dossiers des agents de sa région
        - DGA/Admin: Tous les dossiers
    
    Args:
        query: Query SQLAlchemy sur DossierClient
        user: Utilisateur connecté
        db: Session database
        
    Returns:
        Query filtrée selon les permissions
    """
    
    # DGA et Admin : Accès à tout
    if user.role in [RoleEnum.DGA, RoleEnum.ADMIN]:
        return query
    
    # Agent : Uniquement ses dossiers avec affectation active
    if user.role == RoleEnum.AGENT:
        return query.join(AffectationDossier).filter(
            AffectationDossier.id_agent == user.id_utilisateur,
            AffectationDossier.actif == True
        )
    
    # Chef d'Agence : Dossiers des agents de son agence
    if user.role == RoleEnum.CHEF_AGENCE:
        # Sous-requête : agents de son agence
        agents_agence = db.query(Utilisateur.id_utilisateur).filter(
            Utilisateur.id_agence == user.id_agence
        ).subquery()
        
        return query.join(AffectationDossier).filter(
            AffectationDossier.id_agent.in_(agents_agence),
            AffectationDossier.actif == True
        )
    
    # Chef Régional : Dossiers des agents de sa région
    if user.role == RoleEnum.CHEF_REGIONAL:
        # Récupérer la région de l'utilisateur
        user_agence = db.query(Agence).filter(
            Agence.id_agence == user.id_agence
        ).first()
        
        if not user_agence:
            # Si pas d'agence, pas de dossiers
            return query.filter(False)
        
        # Sous-requête : agences de sa région
        agences_region = db.query(Agence.id_agence).filter(
            Agence.id_region == user_agence.id_region
        ).subquery()
        
        # Sous-requête : agents des agences de sa région
        agents_region = db.query(Utilisateur.id_utilisateur).filter(
            Utilisateur.id_agence.in_(agences_region)
        ).subquery()
        
        return query.join(AffectationDossier).filter(
            AffectationDossier.id_agent.in_(agents_region),
            AffectationDossier.actif == True
        )
    
    # Fallback : pas d'accès
    return query.filter(False)

# ========================
# VÉRIFICATION D'ACCÈS À UN DOSSIER SPÉCIFIQUE
# ========================

def check_dossier_access(
    dossier_id: int,
    user: Utilisateur,
    db: Session
) -> bool:
    """
    Vérifier si un utilisateur a accès à un dossier spécifique
    
    Args:
        dossier_id: ID du dossier
        user: Utilisateur connecté
        db: Session database
        
    Returns:
        True si l'utilisateur a accès
        
    Raises:
        HTTPException 403 si accès refusé
        HTTPException 404 si dossier non trouvé
    """
    
    # Vérifier que le dossier existe
    dossier = db.query(DossierClient).filter(
        DossierClient.id_dossier == dossier_id
    ).first()
    
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé"
        )
    
    # DGA et Admin : Accès à tout
    if user.role in [RoleEnum.DGA, RoleEnum.ADMIN]:
        return True
    
    # Récupérer l'affectation active
    affectation = db.query(AffectationDossier).filter(
        AffectationDossier.id_dossier == dossier_id,
        AffectationDossier.actif == True
    ).first()
    
    if not affectation:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce dossier n'a pas d'affectation active"
        )
    
    # Agent : Vérifier que c'est son dossier
    if user.role == RoleEnum.AGENT:
        if affectation.id_agent != user.id_utilisateur:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'avez pas accès à ce dossier"
            )
        return True
    
    # Chef d'Agence : Vérifier que l'agent est de son agence
    if user.role == RoleEnum.CHEF_AGENCE:
        agent = db.query(Utilisateur).filter(
            Utilisateur.id_utilisateur == affectation.id_agent
        ).first()
        
        if not agent or agent.id_agence != user.id_agence:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce dossier n'appartient pas à votre agence"
            )
        return True
    
    # Chef Régional : Vérifier que l'agence de l'agent est dans sa région
    if user.role == RoleEnum.CHEF_REGIONAL:
        agent = db.query(Utilisateur).filter(
            Utilisateur.id_utilisateur == affectation.id_agent
        ).first()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agent non trouvé"
            )
        
        agent_agence = db.query(Agence).filter(
            Agence.id_agence == agent.id_agence
        ).first()
        
        user_agence = db.query(Agence).filter(
            Agence.id_agence == user.id_agence
        ).first()
        
        if not agent_agence or not user_agence:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Agence non trouvée"
            )
        
        if agent_agence.id_region != user_agence.id_region:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Ce dossier n'appartient pas à votre région"
            )
        return True
    
    # Fallback
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès refusé"
    )

# ========================
# FILTRAGE DES UTILISATEURS
# ========================

def filter_utilisateurs_by_role(
    query: Query,
    user: Utilisateur,
    db: Session
) -> Query:
    """
    Filtrer les utilisateurs selon le rôle
    
    - Agent: Voir uniquement lui-même
    - Chef d'Agence: Voir les utilisateurs de son agence
    - Chef Régional: Voir les utilisateurs de sa région
    - DGA/Admin: Voir tous les utilisateurs
    """
    
    # DGA et Admin : Accès à tout
    if user.role in [RoleEnum.DGA, RoleEnum.ADMIN]:
        return query
    
    # Agent : Uniquement lui-même
    if user.role == RoleEnum.AGENT:
        return query.filter(Utilisateur.id_utilisateur == user.id_utilisateur)
    
    # Chef d'Agence : Utilisateurs de son agence
    if user.role == RoleEnum.CHEF_AGENCE:
        return query.filter(Utilisateur.id_agence == user.id_agence)
    
    # Chef Régional : Utilisateurs de sa région
    if user.role == RoleEnum.CHEF_REGIONAL:
        user_agence = db.query(Agence).filter(
            Agence.id_agence == user.id_agence
        ).first()
        
        if not user_agence:
            return query.filter(False)
        
        agences_region = db.query(Agence.id_agence).filter(
            Agence.id_region == user_agence.id_region
        ).subquery()
        
        return query.filter(Utilisateur.id_agence.in_(agences_region))
    
    return query.filter(False)

# ========================
# HELPER FUNCTIONS
# ========================

def can_modify_user(
    current_user: Utilisateur,
    target_user: Utilisateur,
    db: Session
) -> bool:
    """
    Vérifier si un utilisateur peut modifier un autre utilisateur
    
    Règles:
        - Admin: Peut modifier tout le monde
        - DGA: Peut modifier sauf Admin
        - Chef Régional: Peut modifier dans sa région (sauf DGA/Admin)
        - Chef Agence: Peut modifier dans son agence (sauf DGA/Admin/Chef Regional)
        - Agent: Ne peut modifier personne
    """
    
    # Admin peut tout
    if current_user.role == RoleEnum.ADMIN:
        return True
    
    # DGA peut tout sauf Admin
    if current_user.role == RoleEnum.DGA:
        return target_user.role != RoleEnum.ADMIN
    
    # Agent ne peut rien modifier
    if current_user.role == RoleEnum.AGENT:
        return False
    
    # Chef d'Agence : peut modifier dans son agence (sauf managers supérieurs)
    if current_user.role == RoleEnum.CHEF_AGENCE:
        if target_user.role in [RoleEnum.DGA, RoleEnum.ADMIN, RoleEnum.CHEF_REGIONAL]:
            return False
        return target_user.id_agence == current_user.id_agence
    
    # Chef Régional : peut modifier dans sa région (sauf DGA/Admin)
    if current_user.role == RoleEnum.CHEF_REGIONAL:
        if target_user.role in [RoleEnum.DGA, RoleEnum.ADMIN]:
            return False
        
        current_agence = db.query(Agence).filter(
            Agence.id_agence == current_user.id_agence
        ).first()
        
        target_agence = db.query(Agence).filter(
            Agence.id_agence == target_user.id_agence
        ).first()
        
        if not current_agence or not target_agence:
            return False
        
        return current_agence.id_region == target_agence.id_region
    
    return False

def get_user_scope_summary(user: Utilisateur, db: Session) -> dict:
    """
    Obtenir un résumé de la portée d'accès d'un utilisateur
    
    Utile pour afficher dans le frontend les limites de l'utilisateur
    """
    
    if user.role in [RoleEnum.DGA, RoleEnum.ADMIN]:
        return {
            "role": user.role.value,
            "scope": "global",
            "description": "Accès à toutes les données"
        }
    
    if user.role == RoleEnum.CHEF_REGIONAL:
        user_agence = db.query(Agence).filter(
            Agence.id_agence == user.id_agence
        ).first()
        
        if user_agence:
            from app.models.region import Region
            region = db.query(Region).filter(
                Region.id_region == user_agence.id_region
            ).first()
            
            return {
                "role": user.role.value,
                "scope": "region",
                "region_id": user_agence.id_region,
                "region_nom": region.nom_region if region else "Inconnue",
                "description": f"Accès aux données de la région {region.nom_region if region else ''}"
            }
    
    if user.role == RoleEnum.CHEF_AGENCE:
        agence = db.query(Agence).filter(
            Agence.id_agence == user.id_agence
        ).first()
        
        return {
            "role": user.role.value,
            "scope": "agence",
            "agence_id": user.id_agence,
            "agence_nom": agence.nom_agence if agence else "Inconnue",
            "description": f"Accès aux données de l'agence {agence.nom_agence if agence else ''}"
        }
    
    if user.role == RoleEnum.AGENT:
        return {
            "role": user.role.value,
            "scope": "personal",
            "description": "Accès uniquement aux dossiers assignés"
        }
    
    return {
        "role": user.role.value,
        "scope": "none",
        "description": "Pas d'accès"
    }
