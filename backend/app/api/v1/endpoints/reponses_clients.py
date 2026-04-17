from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import check_dossier_access, filter_dossiers_by_role
from app.models.reponse_client import ReponseClient, CanalReponseEnum
from app.models.dossier_client import DossierClient
from app.models.utilisateur import Utilisateur
from pydantic import BaseModel

router = APIRouter()

# ── Schemas (inline for simplicity) ──────────────────────────────────────────
class ReponseClientCreate(BaseModel):
    id_dossier: int
    id_message: Optional[int] = None
    contenu_brut: str
    canal: CanalReponseEnum
    expediteur: Optional[str] = None

class ReponseClientResponse(BaseModel):
    id_reponse: int
    id_dossier: int
    id_message: Optional[int] = None
    contenu_brut: str
    date_reponse: datetime
    canal: CanalReponseEnum
    expediteur: Optional[str] = None

    class Config:
        from_attributes = True

# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/dossier/{dossier_id}", response_model=List[ReponseClientResponse])
def get_reponses_dossier(
    dossier_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer toutes les réponses client d'un dossier"""
    check_dossier_access(dossier_id, current_user, db)
    
    return db.query(ReponseClient).filter(
        ReponseClient.id_dossier == dossier_id
    ).order_by(ReponseClient.date_reponse.desc()).all()

@router.post("/", response_model=ReponseClientResponse, status_code=status.HTTP_201_CREATED)
def create_reponse(
    reponse: ReponseClientCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Enregistrer une réponse client"""
    check_dossier_access(reponse.id_dossier, current_user, db)
    
    db_reponse = ReponseClient(
        **reponse.dict(),
        date_reponse=datetime.now()
    )
    db.add(db_reponse)
    db.commit()
    db.refresh(db_reponse)
    return db_reponse

@router.delete("/{reponse_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reponse(
    reponse_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Supprimer une réponse"""
    db_reponse = db.query(ReponseClient).filter(
        ReponseClient.id_reponse == reponse_id
    ).first()
    
    if not db_reponse:
        raise HTTPException(status_code=404, detail="Réponse non trouvée")
    
    check_dossier_access(db_reponse.id_dossier, current_user, db)
    db.delete(db_reponse)
    db.commit()
    return None