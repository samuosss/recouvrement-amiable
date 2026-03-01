from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import filter_dossiers_by_role
from app.models.client import Client
from app.models.dossier_client import DossierClient
from app.models.utilisateur import Utilisateur
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from app.crud import client as crud_client

router = APIRouter()

@router.get("/", response_model=List[ClientResponse])
def get_clients(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer les clients selon les permissions
    
    Un utilisateur ne voit que les clients ayant des dossiers accessibles
    """
    # Récupérer les IDs des dossiers accessibles
    dossiers_query = db.query(DossierClient.id_client).distinct()
    dossiers_query = filter_dossiers_by_role(dossiers_query, current_user, db)
    clients_accessibles = [d.id_client for d in dossiers_query.all()]
    
    # Query clients
    query = db.query(Client).filter(Client.id_client.in_(clients_accessibles))
    
    if search:
        from sqlalchemy import or_
        query = query.filter(
            or_(
                Client.nom.ilike(f"%{search}%"),
                Client.prenom.ilike(f"%{search}%"),
                Client.cin.ilike(f"%{search}%"),
                Client.email.ilike(f"%{search}%")
            )
        )
    
    return query.offset(skip).limit(limit).all()

@router.get("/{id_client}", response_model=ClientResponse)
def get_client(
    id_client: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer un client par ID"""
    # Vérifier que l'utilisateur a accès à au moins un dossier de ce client
    dossiers_query = db.query(DossierClient).filter(
        DossierClient.id_client == id_client
    )
    dossiers_query = filter_dossiers_by_role(dossiers_query, current_user, db)
    
    if not dossiers_query.first():
        raise HTTPException(
            status_code=403,
            detail="Vous n'avez pas accès à ce client"
        )
    
    client = crud_client.get_client(db, id_client)
    
    if not client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    return client

@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client: ClientCreate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Créer un nouveau client"""
    # Vérifier si le CIN existe déjà
    existing = crud_client.get_client_by_cin(db, client.cin)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Un client avec ce CIN existe déjà"
        )
    
    return crud_client.create_client(db, client)

@router.put("/{id_client}", response_model=ClientResponse)
def update_client(
    id_client: int,
    client_update: ClientUpdate,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mettre à jour un client"""
    # Vérifier l'accès
    dossiers_query = db.query(DossierClient).filter(
        DossierClient.id_client == id_client
    )
    dossiers_query = filter_dossiers_by_role(dossiers_query, current_user, db)
    
    if not dossiers_query.first():
        raise HTTPException(
            status_code=403,
            detail="Vous n'avez pas accès à ce client"
        )
    
    db_client = crud_client.update_client(db, id_client, client_update)
    
    if not db_client:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    return db_client

@router.delete("/{id_client}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    id_client: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Supprimer un client"""
    # Vérifier l'accès
    dossiers_query = db.query(DossierClient).filter(
        DossierClient.id_client == id_client
    )
    dossiers_query = filter_dossiers_by_role(dossiers_query, current_user, db)
    
    if not dossiers_query.first():
        raise HTTPException(
            status_code=403,
            detail="Vous n'avez pas accès à ce client"
        )
    
    success = crud_client.delete_client(db, id_client)
    
    if not success:
        raise HTTPException(status_code=404, detail="Client non trouvé")
    
    return None
