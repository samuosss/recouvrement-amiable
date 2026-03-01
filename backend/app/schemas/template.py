from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.template import TypeTemplateEnum

class TemplateBase(BaseModel):
    nom_template: str
    type_template: TypeTemplateEnum
    objet: Optional[str] = None
    corps: str
    variables_disponibles: Optional[dict] = None
    actif: bool = True

class TemplateCreate(TemplateBase):
    pass

class TemplateUpdate(BaseModel):
    nom_template: Optional[str] = None
    type_template: Optional[TypeTemplateEnum] = None
    objet: Optional[str] = None
    corps: Optional[str] = None
    variables_disponibles: Optional[dict] = None
    actif: Optional[bool] = None

class TemplateResponse(TemplateBase):
    id_template: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TemplatePreview(BaseModel):
    """Prévisualisation d'un template avec variables remplacées"""
    template_id: int
    objet_rendu: Optional[str] = None
    corps_rendu: str
    variables_utilisees: dict
