from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import (
    filter_dossiers_by_role,
    check_dossier_access,
    require_manager,
    get_user_scope_summary
)
from app.models.dossier_client import DossierClient, StatutDossierEnum, PrioriteEnum
from app.models.utilisateur import Utilisateur
from app.schemas.dossier import (
    DossierCreate,
    DossierUpdate,
    DossierResponse
)

router = APIRouter()

# ========================
# ENDPOINTS LECTURE
# ========================

@router.get("/", response_model=List[DossierResponse])
def get_dossiers(
    skip: int = 0,
    limit: int = 100,
    statut: Optional[StatutDossierEnum] = None,
    priorite: Optional[PrioriteEnum] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer les dossiers selon les permissions de l'utilisateur
    
    **Permissions:**
    - **Agent**: Ses dossiers uniquement
    - **Chef d'Agence**: Dossiers de son agence
    - **Chef Régional**: Dossiers de sa région
    - **DGA/Admin**: Tous les dossiers
    
    **Filtres optionnels:**
    - statut: Filtrer par statut
    - priorite: Filtrer par priorité
    """
    # Créer la query de base
    query = db.query(DossierClient)
    
    # Appliquer le filtrage hiérarchique selon le rôle
    query = filter_dossiers_by_role(query, current_user, db)
    
    # Appliquer les filtres additionnels
    if statut:
        query = query.filter(DossierClient.statut == statut)
    if priorite:
        query = query.filter(DossierClient.priorite == priorite)
    
    # Éviter les doublons (à cause des joins)
    query = query.distinct()
    
    # Tri par date (plus récents en premier)
    query = query.order_by(DossierClient.date_ouverture.desc())
    
    # Pagination
    dossiers = query.offset(skip).limit(limit).all()
    
    return dossiers

@router.get("/me/scope", response_model=dict)
def get_my_scope(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtenir la portée d'accès de l'utilisateur connecté
    
    Retourne les informations sur ce que l'utilisateur peut voir :
    - Son rôle
    - Sa portée d'accès (global, région, agence, personnel)
    - Description textuelle
    
    Utile pour afficher dans le frontend les limites de l'utilisateur
    """
    return get_user_scope_summary(current_user, db)

@router.get("/{id_dossier}", response_model=DossierResponse)
def get_dossier(
    id_dossier: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer un dossier par ID
    
    Vérifie automatiquement que l'utilisateur a accès à ce dossier
    selon son rôle et sa hiérarchie.
    
    **Raises:**
    - 404: Dossier non trouvé
    - 403: Accès refusé (hors périmètre)
    """
    # Vérifier l'accès (lève une exception si refusé)
    check_dossier_access(id_dossier, current_user, db)
    
    # Récupérer le dossier
    dossier = db.query(DossierClient).filter(
        DossierClient.id_dossier == id_dossier
    ).first()
    
    if not dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé"
        )
    
    return dossier

@router.get("/stats/summary", response_model=dict)
def get_dossiers_stats(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Obtenir des statistiques sur les dossiers accessibles
    
    Les statistiques sont filtrées selon les permissions de l'utilisateur.
    """
    from sqlalchemy import func
    
    # Query de base filtrée par permissions
    query = db.query(DossierClient)
    query = filter_dossiers_by_role(query, current_user, db)
    query = query.distinct()
    
    # Total
    total = query.count()
    
    # Par statut
    stats_statut = db.query(
        DossierClient.statut,
        func.count(DossierClient.id_dossier).label('count')
    ).select_from(query.subquery()).group_by(
        DossierClient.statut
    ).all()
    
    # Par priorité
    stats_priorite = db.query(
        DossierClient.priorite,
        func.count(DossierClient.id_dossier).label('count')
    ).select_from(query.subquery()).group_by(
        DossierClient.priorite
    ).all()
    
    # Montant total
    montant_total = query.with_entities(
        func.sum(DossierClient.montant_total_du)
    ).scalar() or 0
    
    return {
        "total_dossiers": total,
        "montant_total_du": float(montant_total),
        "par_statut": {stat.statut.value: stat.count for stat in stats_statut},
        "par_priorite": {stat.priorite.value: stat.count for stat in stats_priorite},
        "scope": get_user_scope_summary(current_user, db)
    }

# ========================
# ENDPOINTS ÉCRITURE
# ========================

@router.post("/", response_model=DossierResponse, status_code=status.HTTP_201_CREATED)
def create_dossier(
    dossier: DossierCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Créer un nouveau dossier
    
    **Permissions**: Tous les utilisateurs authentifiés peuvent créer un dossier
    """
    # Vérifier que le client existe
    from app.models.client import Client
    client = db.query(Client).filter(Client.id_client == dossier.id_client).first()
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client non trouvé"
        )
    
    # Créer le dossier
    db_dossier = DossierClient(**dossier.dict())
    db.add(db_dossier)
    db.commit()
    db.refresh(db_dossier)
    
    # Traçabilité
    from app.models.tracabilite import Tracabilite, ActionEnum
    from datetime import datetime
    
    trace = Tracabilite(
        table_cible="dossiers_clients",
        id_enregistrement=db_dossier.id_dossier,
        action=ActionEnum.CREATION,
        id_utilisateur=current_user.id_utilisateur,
        date_action=datetime.now(),
        nouvelles_valeurs=dossier.dict(),
        description=f"Création dossier {db_dossier.numero_dossier}"
    )
    db.add(trace)
    db.commit()
    
    return db_dossier

@router.put("/{id_dossier}", response_model=DossierResponse)
def update_dossier(
    id_dossier: int,
    dossier_update: DossierUpdate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Mettre à jour un dossier
    
    Vérifie que l'utilisateur a accès à ce dossier avant de le modifier.
    """
    # Vérifier l'accès
    check_dossier_access(id_dossier, current_user, db)
    
    # Récupérer le dossier
    db_dossier = db.query(DossierClient).filter(
        DossierClient.id_dossier == id_dossier
    ).first()
    
    if not db_dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé"
        )
    
    # Sauvegarder les anciennes valeurs
    old_values = {
        "statut": db_dossier.statut.value if db_dossier.statut else None,
        "priorite": db_dossier.priorite.value if db_dossier.priorite else None,
        "montant_total_du": float(db_dossier.montant_total_du) if db_dossier.montant_total_du else None
    }
    
    # Mettre à jour
    for field, value in dossier_update.dict(exclude_unset=True).items():
        setattr(db_dossier, field, value)
    
    db.commit()
    db.refresh(db_dossier)
    
    # Traçabilité
    from app.models.tracabilite import Tracabilite, ActionEnum
    from datetime import datetime
    
    trace = Tracabilite(
        table_cible="dossiers_clients",
        id_enregistrement=id_dossier,
        action=ActionEnum.MODIFICATION,
        id_utilisateur=current_user.id_utilisateur,
        date_action=datetime.now(),
        anciennes_valeurs=old_values,
        nouvelles_valeurs=dossier_update.dict(exclude_unset=True),
        description=f"Modification dossier {db_dossier.numero_dossier}"
    )
    db.add(trace)
    db.commit()
    
    return db_dossier

@router.delete("/{id_dossier}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dossier(
    id_dossier: int,
    current_user: Utilisateur = Depends(require_manager),  # Seulement managers
    db: Session = Depends(get_db)
):
    """
    Supprimer un dossier
    
    **Permissions**: Réservé aux managers (Chef d'Agence et au-dessus)
    
    Supprime également toutes les données liées (créances, interactions, etc.)
    """
    # Vérifier l'accès
    check_dossier_access(id_dossier, current_user, db)
    
    # Récupérer le dossier
    db_dossier = db.query(DossierClient).filter(
        DossierClient.id_dossier == id_dossier
    ).first()
    
    if not db_dossier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dossier non trouvé"
        )
    
    # Traçabilité avant suppression
    from app.models.tracabilite import Tracabilite, ActionEnum
    from datetime import datetime
    
    trace = Tracabilite(
        table_cible="dossiers_clients",
        id_enregistrement=id_dossier,
        action=ActionEnum.SUPPRESSION,
        id_utilisateur=current_user.id_utilisateur,
        date_action=datetime.now(),
        anciennes_valeurs={
            "numero_dossier": db_dossier.numero_dossier,
            "statut": db_dossier.statut.value if db_dossier.statut else None
        },
        description=f"Suppression dossier {db_dossier.numero_dossier}"
    )
    db.add(trace)
    
    # Supprimer
    db.delete(db_dossier)
    db.commit()
    
    return None
