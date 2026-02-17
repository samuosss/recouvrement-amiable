from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.crud.client import client as crud_client
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse

router = APIRouter()

@router.get("/", response_model=List[ClientResponse])
def get_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Récupérer la liste des clients avec pagination"""
    try:
        clients = crud_client.get_multi(db, skip=skip, limit=limit)
        return clients
    except Exception as e:
        logger.error(f"Error getting clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    db: Session = Depends(get_db)
):
    """Récupérer un client par son ID"""
    try:
        client = crud_client.get(db, id=client_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client avec ID {client_id} non trouvé"
            )
        return client
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    client_in: ClientCreate,
    db: Session = Depends(get_db)
):
    """Créer un nouveau client"""
    try:
        # Vérifier si le CIN existe déjà
        existing_client = crud_client.get_by_cin(db, cin=client_in.cin)
        if existing_client:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Un client avec le CIN {client_in.cin} existe déjà"
            )
        
        # Créer le client
        new_client = crud_client.create(db, obj_in=client_in)
        logger.info(f"Client created: {new_client.id_client}")
        return new_client
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db)
):
    """Mettre à jour un client"""
    try:
        client = crud_client.get(db, id=client_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client avec ID {client_id} non trouvé"
            )
        
        updated_client = crud_client.update(db, db_obj=client, obj_in=client_in)
        logger.info(f"Client updated: {updated_client.id_client}")
        return updated_client
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{client_id}", status_code=status.HTTP_200_OK)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db)
):
    """Supprimer un client"""
    try:
        client = crud_client.get(db, id=client_id)
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Client avec ID {client_id} non trouvé"
            )
        
        crud_client.delete(db, id=client_id)
        logger.info(f"Client deleted: {client_id}")
        return {"message": f"Client {client_id} supprimé avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting client {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search/", response_model=List[ClientResponse])
def search_clients(
    q: str = Query(..., min_length=2, description="Terme de recherche"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Rechercher des clients par nom, prénom ou CIN"""
    try:
        clients = crud_client.search(db, query=q, skip=skip, limit=limit)
        return clients
    except Exception as e:
        logger.error(f"Error searching clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))
