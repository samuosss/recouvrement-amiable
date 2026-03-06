from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
import redis

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-me-in-production-2024")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

print("="*70)
print(f"🔐 SECRET_KEY chargée: {SECRET_KEY}")
print(f"🔑 ALGORITHM: {ALGORITHM}")
print("="*70)

# Contexte de hachage de mot de passe - CORRECTION ICI
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Redis pour blacklist
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=int(os.getenv("REDIS_DB", "0")),
    decode_responses=True
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier un mot de passe - AVEC LIMITE 72 BYTES"""
    # Tronquer le mot de passe à 72 bytes pour bcrypt
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hasher un mot de passe - AVEC LIMITE 72 BYTES"""
    # Tronquer le mot de passe à 72 bytes pour bcrypt
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Créer un token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """Décoder un token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def blacklist_token(token: str):
    """Ajouter un token à la blacklist"""
    try:
        payload = decode_access_token(token)
        if payload:
            exp = payload.get("exp")
            if exp:
                ttl = exp - int(datetime.utcnow().timestamp())
                if ttl > 0:
                    redis_client.setex(f"blacklist:{token}", ttl, "1")
    except Exception as e:
        print(f"Erreur blacklist: {e}")

def is_token_blacklisted(token: str) -> bool:
    """Vérifier si un token est blacklisté"""
    try:
        return redis_client.exists(f"blacklist:{token}") > 0
    except:
        return False

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(lambda: None)
):
    """Récupérer l'utilisateur courant"""
    from app.core.database import get_db
    from app.models.utilisateur import Utilisateur
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Vérifier blacklist
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
    
    # Obtenir la session DB
    if db is None:
        db = next(get_db())
    
    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_active_user(current_user = Depends(get_current_user)):
    """Récupérer l'utilisateur actif"""
    if not current_user.actif:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def authenticate_user(db: Session, email: str, password: str):
    """Authentifier un utilisateur"""
    from app.models.utilisateur import Utilisateur
    
    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    if not user:
        return False
    if not verify_password(password, user.mot_de_passe):
        return False
    return user
def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Créer un token de refresh JWT"""
    to_encode = data.copy()
    # Par défaut, expire dans 7 jours
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt