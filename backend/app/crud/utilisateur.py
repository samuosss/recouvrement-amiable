from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from passlib.context import CryptContext

from app.models.utilisateur import Utilisateur, RoleEnum
from app.schemas.utilisateur import UtilisateurCreate, UtilisateurUpdate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_utilisateur(db: Session, utilisateur_id: int) -> Optional[Utilisateur]:
    return db.query(Utilisateur).filter(Utilisateur.id_utilisateur == utilisateur_id).first()

def get_utilisateur_by_email(db: Session, email: str) -> Optional[Utilisateur]:
    return db.query(Utilisateur).filter(Utilisateur.email == email).first()

def get_utilisateurs(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    role: Optional[RoleEnum] = None,
    agence_id: Optional[int] = None,
    actif: Optional[bool] = None,
    search: Optional[str] = None
) -> List[Utilisateur]:
    query = db.query(Utilisateur)
    
    if role:
        query = query.filter(Utilisateur.role == role)
    if agence_id:
        query = query.filter(Utilisateur.id_agence == agence_id)
    if actif is not None:
        query = query.filter(Utilisateur.actif == actif)
    if search:
        query = query.filter(
            or_(
                Utilisateur.nom.ilike(f"%{search}%"),
                Utilisateur.prenom.ilike(f"%{search}%"),
                Utilisateur.email.ilike(f"%{search}%")
            )
        )
    
    return query.offset(skip).limit(limit).all()

def create_utilisateur(db: Session, utilisateur: UtilisateurCreate) -> Utilisateur:
    # Hasher le mot de passe
    hashed_password = get_password_hash(utilisateur.mot_de_passe)
    
    db_utilisateur = Utilisateur(
        **utilisateur.dict(exclude={'mot_de_passe'}),
        mot_de_passe=hashed_password
    )
    db.add(db_utilisateur)
    db.commit()
    db.refresh(db_utilisateur)
    return db_utilisateur

def update_utilisateur(
    db: Session,
    utilisateur_id: int,
    utilisateur_update: UtilisateurUpdate
) -> Optional[Utilisateur]:
    db_utilisateur = get_utilisateur(db, utilisateur_id)
    if not db_utilisateur:
        return None
    
    update_data = utilisateur_update.dict(exclude_unset=True)
    
    # Si le mot de passe est fourni, le hasher
    if 'mot_de_passe' in update_data and update_data['mot_de_passe']:
        update_data['mot_de_passe'] = get_password_hash(update_data['mot_de_passe'])
    
    for field, value in update_data.items():
        setattr(db_utilisateur, field, value)
    
    db.commit()
    db.refresh(db_utilisateur)
    return db_utilisateur

def delete_utilisateur(db: Session, utilisateur_id: int) -> bool:
    db_utilisateur = get_utilisateur(db, utilisateur_id)
    if not db_utilisateur:
        return False
    
    db.delete(db_utilisateur)
    db.commit()
    return True

def get_utilisateurs_by_agence(db: Session, agence_id: int) -> List[Utilisateur]:
    return db.query(Utilisateur).filter(Utilisateur.id_agence == agence_id).all()

def get_agents_actifs(db: Session, agence_id: Optional[int] = None) -> List[Utilisateur]:
    query = db.query(Utilisateur).filter(
        Utilisateur.role == RoleEnum.AGENT,
        Utilisateur.actif == True
    )
    if agence_id:
        query = query.filter(Utilisateur.id_agence == agence_id)
    return query.all()