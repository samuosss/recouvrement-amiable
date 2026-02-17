from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RegionBase(BaseModel):
    nom_region: str
    code_region: str
    description: Optional[str] = None

class RegionCreate(RegionBase):
    pass

class RegionUpdate(BaseModel):
    nom_region: Optional[str] = None
    code_region: Optional[str] = None
    description: Optional[str] = None

class RegionResponse(RegionBase):
    id_region: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True