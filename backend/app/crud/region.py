from sqlalchemy.orm import Session
from typing import Optional, List

from app.models.region import Region
from app.schemas.region import RegionCreate, RegionUpdate

def get_region(db: Session, region_id: int) -> Optional[Region]:
    return db.query(Region).filter(Region.id_region == region_id).first()

def get_region_by_code(db: Session, code: str) -> Optional[Region]:
    return db.query(Region).filter(Region.code_region == code).first()

def get_regions(db: Session, skip: int = 0, limit: int = 100) -> List[Region]:
    return db.query(Region).offset(skip).limit(limit).all()

def create_region(db: Session, region: RegionCreate) -> Region:
    db_region = Region(**region.dict())
    db.add(db_region)
    db.commit()
    db.refresh(db_region)
    return db_region

def update_region(db: Session, region_id: int, region_update: RegionUpdate) -> Optional[Region]:
    db_region = get_region(db, region_id)
    if not db_region:
        return None
    
    for field, value in region_update.dict(exclude_unset=True).items():
        setattr(db_region, field, value)
    
    db.commit()
    db.refresh(db_region)
    return db_region

def delete_region(db: Session, region_id: int) -> bool:
    db_region = get_region(db, region_id)
    if not db_region:
        return False
    
    db.delete(db_region)
    db.commit()
    return True