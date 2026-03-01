from sqlalchemy.orm import Session
from typing import List, Optional
import re

from app.models.template import Template, TypeTemplateEnum
from app.schemas.template import TemplateCreate, TemplateUpdate

def get_template(db: Session, template_id: int) -> Optional[Template]:
    return db.query(Template).filter(Template.id_template == template_id).first()

def get_templates(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    type_template: Optional[TypeTemplateEnum] = None,
    actif: Optional[bool] = None
) -> List[Template]:
    query = db.query(Template)
    
    if type_template:
        query = query.filter(Template.type_template == type_template)
    if actif is not None:
        query = query.filter(Template.actif == actif)
    
    return query.offset(skip).limit(limit).all()

def create_template(db: Session, template: TemplateCreate) -> Template:
    db_template = Template(**template.dict())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

def update_template(
    db: Session,
    template_id: int,
    template_update: TemplateUpdate
) -> Optional[Template]:
    db_template = get_template(db, template_id)
    if not db_template:
        return None
    
    for field, value in template_update.dict(exclude_unset=True).items():
        setattr(db_template, field, value)
    
    db.commit()
    db.refresh(db_template)
    return db_template

def delete_template(db: Session, template_id: int) -> bool:
    db_template = get_template(db, template_id)
    if not db_template:
        return False
    
    db.delete(db_template)
    db.commit()
    return True

def render_template(template: Template, variables: dict) -> tuple[Optional[str], str]:
    """
    Rendre un template avec les variables fournies
    
    Variables supportées:
    - {nom_client}
    - {prenom_client}
    - {montant_du}
    - {numero_dossier}
    - {date_echeance}
    - etc.
    
    Returns:
        tuple (objet_rendu, corps_rendu)
    """
    objet_rendu = None
    if template.objet:
        objet_rendu = template.objet
        for key, value in variables.items():
            objet_rendu = objet_rendu.replace(f"{{{key}}}", str(value))
    
    corps_rendu = template.corps
    for key, value in variables.items():
        corps_rendu = corps_rendu.replace(f"{{{key}}}", str(value))
    
    return objet_rendu, corps_rendu

def extract_variables(text: str) -> List[str]:
    """Extraire toutes les variables d'un template (format {variable})"""
    return re.findall(r'\{(\w+)\}', text)

def validate_template(template: Template) -> dict:
    """
    Valider un template et retourner les variables trouvées
    
    Returns:
        {
            "valid": bool,
            "variables_objet": list,
            "variables_corps": list,
            "errors": list
        }
    """
    errors = []
    variables_objet = []
    variables_corps = []
    
    # Extraire les variables
    if template.objet:
        variables_objet = extract_variables(template.objet)
    
    variables_corps = extract_variables(template.corps)
    
    # Vérifier que le corps n'est pas vide
    if not template.corps or len(template.corps.strip()) < 10:
        errors.append("Le corps du template doit contenir au moins 10 caractères")
    
    # Pour les emails, l'objet est obligatoire
    if template.type_template == TypeTemplateEnum.EMAIL and not template.objet:
        errors.append("L'objet est obligatoire pour les templates Email")
    
    return {
        "valid": len(errors) == 0,
        "variables_objet": variables_objet,
        "variables_corps": variables_corps,
        "all_variables": list(set(variables_objet + variables_corps)),
        "errors": errors
    }
