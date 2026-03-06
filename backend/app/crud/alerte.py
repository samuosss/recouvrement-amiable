from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.alerte import Alerte, TypeAlerteEnum, NiveauAlerteEnum
from app.schemas.alerte import AlerteCreate, AlerteUpdate

def get_alerte(db: Session, alerte_id: int) -> Optional[Alerte]:
    return db.query(Alerte).filter(Alerte.id_alerte == alerte_id).first()

def get_alertes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    utilisateur_id: Optional[int] = None,
    niveau: Optional[NiveauAlerteEnum] = None,
    type_alerte: Optional[TypeAlerteEnum] = None,
    lue: Optional[bool] = None,
    traitee: Optional[bool] = None
) -> List[Alerte]:
    query = db.query(Alerte)
    
    if utilisateur_id:
        query = query.filter(Alerte.id_utilisateur == utilisateur_id)
    if niveau:
        query = query.filter(Alerte.niveau == niveau)
    if type_alerte:
        query = query.filter(Alerte.type == type_alerte)
    if lue is not None:
        query = query.filter(Alerte.lue == lue)
    if traitee is not None:
        query = query.filter(Alerte.traitee == traitee)
    
    return query.order_by(Alerte.date_creation.desc()).offset(skip).limit(limit).all()

def create_alerte(db: Session, alerte: AlerteCreate) -> Alerte:
    db_alerte = Alerte(
        **alerte.dict(),
        date_creation=datetime.now(),
        lue=False,
        traitee=False
    )
    db.add(db_alerte)
    db.commit()
    db.refresh(db_alerte)
    return db_alerte

def update_alerte(
    db: Session,
    alerte_id: int,
    alerte_update: AlerteUpdate
) -> Optional[Alerte]:
    db_alerte = get_alerte(db, alerte_id)
    if not db_alerte:
        return None
    
    for field, value in alerte_update.dict(exclude_unset=True).items():
        setattr(db_alerte, field, value)
    
    db.commit()
    db.refresh(db_alerte)
    return db_alerte

def marquer_lue(db: Session, alerte_id: int) -> Optional[Alerte]:
    db_alerte = get_alerte(db, alerte_id)
    if not db_alerte:
        return None
    
    db_alerte.lue = True
    db_alerte.date_lecture = datetime.now()
    
    db.commit()
    db.refresh(db_alerte)
    return db_alerte

def marquer_traitee(db: Session, alerte_id: int) -> Optional[Alerte]:
    db_alerte = get_alerte(db, alerte_id)
    if not db_alerte:
        return None
    
    db_alerte.traitee = True
    db_alerte.date_traitement = datetime.now()
    
    # Marquer comme lue aussi
    if not db_alerte.lue:
        db_alerte.lue = True
        db_alerte.date_lecture = datetime.now()
    
    db.commit()
    db.refresh(db_alerte)
    return db_alerte

def get_alertes_non_lues(
    db: Session,
    utilisateur_id: Optional[int] = None
) -> List[Alerte]:
    """Récupérer les alertes non lues"""
    query = db.query(Alerte).filter(Alerte.lue == False)
    
    if utilisateur_id:
        query = query.filter(Alerte.id_utilisateur == utilisateur_id)
    
    return query.order_by(
        Alerte.niveau.desc(),
        Alerte.date_creation.desc()
    ).all()

def get_alertes_non_traitees(
    db: Session,
    utilisateur_id: Optional[int] = None
) -> List[Alerte]:
    """Récupérer les alertes non traitées"""
    query = db.query(Alerte).filter(Alerte.traitee == False)
    
    if utilisateur_id:
        query = query.filter(Alerte.id_utilisateur == utilisateur_id)
    
    return query.order_by(
        Alerte.niveau.desc(),
        Alerte.date_creation.desc()
    ).all()

def get_alertes_critiques(db: Session) -> List[Alerte]:
    """Récupérer toutes les alertes critiques non traitées"""
    return db.query(Alerte).filter(
        Alerte.niveau == NiveauAlerteEnum.CRITIQUE,
        Alerte.traitee == False
    ).order_by(Alerte.date_creation.desc()).all()

def get_alertes_dossier(
    db: Session,
    dossier_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[Alerte]:
    """Récupérer toutes les alertes d'un dossier"""
    return db.query(Alerte).filter(
        Alerte.id_dossier == dossier_id
    ).order_by(
        Alerte.date_creation.desc()
    ).offset(skip).limit(limit).all()

def get_stats_alertes(db: Session, utilisateur_id: Optional[int] = None) -> dict:
    """Statistiques des alertes"""
    from sqlalchemy import func
    
    query = db.query(Alerte)
    if utilisateur_id:
        query = query.filter(Alerte.id_utilisateur == utilisateur_id)
    
    total = query.count()
    non_lues = query.filter(Alerte.lue == False).count()
    non_traitees = query.filter(Alerte.traitee == False).count()
    
    # Par niveau
    stats_niveau = db.query(
        Alerte.niveau,
        func.count(Alerte.id_alerte).label('count')
    )
    if utilisateur_id:
        stats_niveau = stats_niveau.filter(Alerte.id_utilisateur == utilisateur_id)
    stats_niveau = stats_niveau.group_by(Alerte.niveau).all()
    
    # Par type
    stats_type = db.query(
        Alerte.type,
        func.count(Alerte.id_alerte).label('count')
    )
    if utilisateur_id:
        stats_type = stats_type.filter(Alerte.id_utilisateur == utilisateur_id)
    stats_type = stats_type.group_by(Alerte.type).all()
    
    return {
        "total_alertes": total,
        "non_lues": non_lues,
        "non_traitees": non_traitees,
        "par_niveau": {stat.niveau.value: stat.count for stat in stats_niveau},
        "par_type": {stat.type.value: stat.count for stat in stats_type}
    }
