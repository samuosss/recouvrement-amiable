from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.permissions import require_manager
from app.models.template import TypeTemplateEnum
from app.models.utilisateur import Utilisateur
from app.schemas.template import (
    TemplateCreate,
    TemplateUpdate,
    TemplateResponse,
    TemplatePreview
)
from app.crud import template as crud_template

router = APIRouter()

@router.get("/", response_model=List[TemplateResponse])
def get_templates(
    skip: int = 0,
    limit: int = 100,
    type_template: Optional[TypeTemplateEnum] = None,
    actif: Optional[bool] = None,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer tous les templates
    
    Accessible à tous les utilisateurs authentifiés
    """
    return crud_template.get_templates(
        db,
        skip=skip,
        limit=limit,
        type_template=type_template,
        actif=actif
    )

@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Récupérer un template par ID"""
    db_template = crud_template.get_template(db, template_id)
    
    if not db_template:
        raise HTTPException(status_code=404, detail="Template non trouvé")
    
    return db_template

@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    template: TemplateCreate,
    current_user: Utilisateur = Depends(require_manager),  # Managers uniquement
    db: Session = Depends(get_db)
):
    """
    Créer un nouveau template
    
    Permissions: Chef d'Agence et au-dessus
    
    Variables disponibles:
    - {nom_client}
    - {prenom_client}
    - {montant_du}
    - {numero_dossier}
    - {date_echeance}
    - {nom_agent}
    - {telephone_agence}
    """
    # Valider le template
    db_template = crud_template.create_template(db, template)
    validation = crud_template.validate_template(db_template)
    
    if not validation["valid"]:
        db.delete(db_template)
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Template invalide: {', '.join(validation['errors'])}"
        )
    
    # Mettre à jour les variables disponibles
    db_template.variables_disponibles = {
        "variables": validation["all_variables"]
    }
    db.commit()
    db.refresh(db_template)
    
    return db_template

@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    template_update: TemplateUpdate,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Mettre à jour un template"""
    db_template = crud_template.update_template(db, template_id, template_update)
    
    if not db_template:
        raise HTTPException(status_code=404, detail="Template non trouvé")
    
    # Re-valider
    validation = crud_template.validate_template(db_template)
    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Template invalide: {', '.join(validation['errors'])}"
        )
    
    # Mettre à jour les variables
    db_template.variables_disponibles = {
        "variables": validation["all_variables"]
    }
    db.commit()
    db.refresh(db_template)
    
    return db_template

@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: int,
    current_user: Utilisateur = Depends(require_manager),
    db: Session = Depends(get_db)
):
    """Supprimer un template"""
    success = crud_template.delete_template(db, template_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Template non trouvé")
    
    return None

@router.post("/{template_id}/preview", response_model=TemplatePreview)
def preview_template(
    template_id: int,
    variables: dict,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Prévisualiser un template avec des variables
    
    Body:
```json
    {
        "nom_client": "Ben Ahmed",
        "prenom_client": "Karim",
        "montant_du": "15000",
        "numero_dossier": "DOS-2024-001"
    }
```
    """
    db_template = crud_template.get_template(db, template_id)
    
    if not db_template:
        raise HTTPException(status_code=404, detail="Template non trouvé")
    
    objet_rendu, corps_rendu = crud_template.render_template(db_template, variables)
    
    return TemplatePreview(
        template_id=template_id,
        objet_rendu=objet_rendu,
        corps_rendu=corps_rendu,
        variables_utilisees=variables
    )

@router.get("/{template_id}/validate")
def validate_template(
    template_id: int,
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Valider un template et lister ses variables"""
    db_template = crud_template.get_template(db, template_id)
    
    if not db_template:
        raise HTTPException(status_code=404, detail="Template non trouvé")
    
    return crud_template.validate_template(db_template)
