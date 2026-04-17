from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from app.models.campagne import Campagne, TypeCampagneEnum, StatutCampagneEnum
from app.models.campagne_client import CampagneClient, StatutEnvoiEnum
from app.models.dossier_client import DossierClient, StatutDossierEnum, PrioriteEnum
from app.schemas.campagne import CampagneCreate, CampagneUpdate

def get_campagne(db: Session, campagne_id: int) -> Optional[Campagne]:
    return db.query(Campagne).filter(Campagne.id_campagne == campagne_id).first()

def get_campagnes(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    statut: Optional[StatutCampagneEnum] = None,
    type_campagne: Optional[TypeCampagneEnum] = None
) -> List[Campagne]:
    query = db.query(Campagne)
    
    if statut:
        query = query.filter(Campagne.statut == statut)
    if type_campagne:
        query = query.filter(Campagne.type == type_campagne)
    
    return query.order_by(Campagne.created_at.desc()).offset(skip).limit(limit).all()

def create_campagne(
    db: Session,
    campagne: CampagneCreate,
    created_by: int = None
) -> Campagne:
    db_campagne = Campagne(
        **campagne.dict(),
        statut=StatutCampagneEnum.PLANIFIEE,
        nombre_cibles=0,
        nombre_envoyes=0,
        nombre_delivres=0,
        nombre_ouverts=0,
        nombre_cliques=0
    )
    db.add(db_campagne)
    db.commit()
    db.refresh(db_campagne)
    return db_campagne

def update_campagne(
    db: Session,
    campagne_id: int,
    campagne_update: CampagneUpdate
) -> Optional[Campagne]:
    db_campagne = get_campagne(db, campagne_id)
    if not db_campagne:
        return None
    
    for field, value in campagne_update.dict(exclude_unset=True).items():
        setattr(db_campagne, field, value)
    
    db.commit()
    db.refresh(db_campagne)
    return db_campagne

def delete_campagne(db: Session, campagne_id: int) -> bool:
    db_campagne = get_campagne(db, campagne_id)
    if not db_campagne:
        return False
    
    db.delete(db_campagne)
    db.commit()
    return True

def get_dossiers_cibles(db: Session, criteres: dict) -> List[int]:
    query = db.query(DossierClient.id_dossier).distinct()
    
    if "statut" in criteres:
        statuts = [StatutDossierEnum(s) for s in criteres["statut"]]
        query = query.filter(DossierClient.statut.in_(statuts))
    
    if "priorite" in criteres:
        priorites = [PrioriteEnum(p) for p in criteres["priorite"]]
        query = query.filter(DossierClient.priorite.in_(priorites))
    
    if "montant_min" in criteres:
        query = query.filter(DossierClient.montant_total_du >= criteres["montant_min"])
    
    if "montant_max" in criteres:
        query = query.filter(DossierClient.montant_total_du <= criteres["montant_max"])
    
    return [d.id_dossier for d in query.all()]

def lancer_campagne(db: Session, campagne_id: int) -> dict:
    campagne = get_campagne(db, campagne_id)
    
    if not campagne:
        return {"success": False, "message": "Campagne non trouvée"}
    
    if campagne.statut != StatutCampagneEnum.PLANIFIEE:
        return {"success": False, "message": "La campagne doit être planifiée"}
    
    dossiers_ids = get_dossiers_cibles(db, campagne.criteres_segmentation)
    
    if not dossiers_ids:
        return {"success": False, "message": "Aucun dossier ne correspond aux critères"}
    
    canal = "SMS" if campagne.type == TypeCampagneEnum.SMS else "Email"
    if campagne.type == TypeCampagneEnum.MIXTE:
        canal = "MIXTE"
    
    for dossier_id in dossiers_ids:
        campagne_client = CampagneClient(
            id_campagne=campagne_id,
            id_dossier=dossier_id,
            statut=StatutEnvoiEnum.EN_ATTENTE,
            canal=canal
        )
        db.add(campagne_client)
    
    campagne.statut = StatutCampagneEnum.EN_COURS
    campagne.nombre_cibles = len(dossiers_ids)
    
    db.commit()
    
    return {
        "success": True,
        "campagne_id": campagne_id,
        "nombre_cibles": len(dossiers_ids),
        "message": f"Campagne lancée pour {len(dossiers_ids)} dossiers"
    }

def get_campagne_stats(db: Session, campagne_id: int) -> dict:
    stats = db.query(
        CampagneClient.statut,
        func.count(CampagneClient.id).label('count')
    ).filter(
        CampagneClient.id_campagne == campagne_id
    ).group_by(CampagneClient.statut).all()
    
    stats_dict = {stat.statut.value: stat.count for stat in stats}
    
    total = sum(stats_dict.values())
    envoyes = stats_dict.get('Envoye', 0)
    delivres = stats_dict.get('Delivre', 0)
    ouverts = stats_dict.get('Ouvert', 0)
    cliques = stats_dict.get('Clique', 0)
    
    taux_delivrance = (delivres / envoyes * 100) if envoyes > 0 else 0
    taux_ouverture = (ouverts / delivres * 100) if delivres > 0 else 0
    taux_clic = (cliques / ouverts * 100) if ouverts > 0 else 0
    
    return {
        "total_cibles": total,
        "envoyes": envoyes,
        "delivres": delivres,
        "ouverts": ouverts,
        "cliques": cliques,
        "taux_delivrance": round(taux_delivrance, 2),
        "taux_ouverture": round(taux_ouverture, 2),
        "taux_clic": round(taux_clic, 2)
    }