from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import check_dossier_access, filter_dossiers_by_role
from app.models.creance import Creance, StatutCreanceEnum
from app.models.dossier_client import DossierClient
from app.models.utilisateur import Utilisateur
from app.schemas.creance import CreanceCreate, CreanceUpdate, CreanceResponse

router = APIRouter()

@router.get("/", response_model=List[CreanceResponse])
def get_creances(
    skip: int = 0,
    limit: int = 100,
    dossier_id: Optional[int] = None,
    statut: Optional[StatutCreanceEnum] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer les créances selon les permissions
    
    Les créances sont filtrées selon l'accès aux dossiers parents
    """
    # Filtrer les dossiers accessibles
    dossiers_query = db.query(DossierClient.id_dossier)
    dossiers_query = filter_dossiers_by_role(dossiers_query, current_user, db)
    dossiers_accessibles = [d.id_dossier for d in dossiers_query.all()]
    
    # Query créances
    query = db.query(Creance).filter(
        Creance.id_dossier.in_(dossiers_accessibles)
    )
    
    if dossier_id:
        query = query.filter(Creance.id_dossier == dossier_id)
    if statut:
        query = query.filter(Creance.statut == statut)
    
    return query.offset(skip).limit(limit).all()

@router.get("/{id_creance}", response_model=CreanceResponse)
def get_creance(
    id_creance: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer une créance par ID"""
    creance = db.query(Creance).filter(Creance.id_creance == id_creance).first()
    
    if not creance:
        raise HTTPException(status_code=404, detail="Créance non trouvée")
    
    # Vérifier l'accès au dossier parent
    check_dossier_access(creance.id_dossier, current_user, db)
    
    return creance

@router.post("/", response_model=CreanceResponse, status_code=status.HTTP_201_CREATED)
def create_creance(
    creance: CreanceCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Créer une nouvelle créance"""
    # Vérifier l'accès au dossier
    check_dossier_access(creance.id_dossier, current_user, db)
    
    db_creance = Creance(**creance.dict())
    db.add(db_creance)
    db.commit()
    db.refresh(db_creance)
    
    return db_creance

@router.put("/{id_creance}", response_model=CreanceResponse)
def update_creance(
    id_creance: int,
    creance_update: CreanceUpdate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mettre à jour une créance"""
    db_creance = db.query(Creance).filter(Creance.id_creance == id_creance).first()
    
    if not db_creance:
        raise HTTPException(status_code=404, detail="Créance non trouvée")
    
    # Vérifier l'accès au dossier parent
    check_dossier_access(db_creance.id_dossier, current_user, db)
    
    for field, value in creance_update.dict(exclude_unset=True).items():
        setattr(db_creance, field, value)
    
    db.commit()
    db.refresh(db_creance)
    
    return db_creance

@router.delete("/{id_creance}", status_code=status.HTTP_204_NO_CONTENT)
def delete_creance(
    id_creance: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Supprimer une créance"""
    db_creance = db.query(Creance).filter(Creance.id_creance == id_creance).first()
    
    if not db_creance:
        raise HTTPException(status_code=404, detail="Créance non trouvée")
    
    # Vérifier l'accès au dossier parent
    check_dossier_access(db_creance.id_dossier, current_user, db)
    
    db.delete(db_creance)
    db.commit()
    
    return None

@router.post("/{id_creance}/paiement")
def enregistrer_paiement(
    id_creance: int,
    montant: float,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    db_creance = db.query(Creance).filter(Creance.id_creance == id_creance).first()
    
    if not db_creance:
        raise HTTPException(status_code=404, detail="Créance non trouvée")
    
    check_dossier_access(db_creance.id_dossier, current_user, db)
    
    montant_paye_actuel = Decimal(str(db_creance.montant_paye or 0))
    montant_initial     = Decimal(str(db_creance.montant_initial or 0))
    nouveau_paye        = montant_paye_actuel + Decimal(str(montant))
    
    # Clamp — can't overpay
    if nouveau_paye > montant_initial:
        nouveau_paye = montant_initial

    db_creance.montant_paye    = nouveau_paye
    db_creance.montant_restant = montant_initial - nouveau_paye
    db_creance.date_dernier_paiement = datetime.now()
    
    # Update statut
    if nouveau_paye >= montant_initial:
        db_creance.statut = StatutCreanceEnum.REGLE
    elif nouveau_paye > 0:
        db_creance.statut = StatutCreanceEnum.PARTIELLEMENT_REGLE
    
    db.commit()
    db.refresh(db_creance)
    
    return {
        "message": "Paiement enregistré",
        "montant": montant,
        "montant_paye": float(nouveau_paye),
        "montant_restant": float(db_creance.montant_restant),
    }