from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.token_blacklist import is_token_blacklisted, is_user_logged_out
from app.models.utilisateur import Utilisateur

# Context pour le hashage de mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# ========================
# PASSWORD HASHING
# ========================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifier si le mot de passe correspond au hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hasher un mot de passe avec bcrypt"""
    return pwd_context.hash(password)

# ========================
# JWT TOKEN CREATION
# ========================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Créer un access token JWT
    
    Structure du token:
        {
            "sub": "1",              # User ID (string)
            "email": "user@email",   # Email utilisateur
            "role": "Admin",         # Rôle
            "agence_id": 1,         # ID agence
            "exp": 1234567890,      # Expiration timestamp
            "iat": 1234567890,      # Émission timestamp
            "type": "access"        # Type de token
        }
    """
    to_encode = data.copy()
    
    # JWT nécessite que "sub" soit un string
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict[str, Any]) -> str:
    """Créer un refresh token JWT (durée de vie plus longue)"""
    to_encode = data.copy()
    
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# ========================
# TOKEN VERIFICATION
# ========================

def decode_token(token: str) -> Dict[str, Any]:
    """Décoder et vérifier un token JWT"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

# ========================
# AUTHENTICATION DEPENDENCIES - SÉCURISÉ
# ========================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Utilisateur:
    """
    Récupérer l'utilisateur actuellement connecté avec vérifications de sécurité
    
    Vérifications effectuées:
    1. Token valide et non expiré
    2. Token non blacklisté
    3. Utilisateur non déconnecté globalement
    4. Utilisateur existe en DB
    5. Utilisateur est actif
    
    Raises:
        HTTPException 401: Si l'une des vérifications échoue
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # SÉCURITÉ 1: Vérifier si le token est blacklisté
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token révoqué. Veuillez vous reconnecter.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # SÉCURITÉ 2: Décoder et valider le token
        payload = decode_token(token)
        user_id_str: str = payload.get("sub")
        token_type: str = payload.get("type")
        token_iat: int = payload.get("iat")
        
        if user_id_str is None or token_type != "access":
            raise credentials_exception
        
        user_id = int(user_id_str)
        
        # SÉCURITÉ 3: Vérifier si l'utilisateur s'est déconnecté globalement
        if token_iat and is_user_logged_out(user_id, datetime.fromtimestamp(token_iat)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expirée. Veuillez vous reconnecter.",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except (JWTError, ValueError):
        raise credentials_exception
    
    # SÉCURITÉ 4: Récupérer l'utilisateur depuis la DB
    user = db.query(Utilisateur).filter(Utilisateur.id_utilisateur == user_id).first()
    
    if user is None:
        raise credentials_exception
    
    # SÉCURITÉ 5: Vérifier que l'utilisateur est actif
    if not user.actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé"
        )
    
    return user

async def get_current_active_user(
    current_user: Utilisateur = Depends(get_current_user)
) -> Utilisateur:
    """Alias pour get_current_user (déjà vérifié)"""
    return current_user

# ========================
# AUTHENTICATION FUNCTION
# ========================

def authenticate_user(db: Session, email: str, password: str) -> Optional[Utilisateur]:
    """Authentifier un utilisateur avec email et mot de passe"""
    user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.mot_de_passe):
        return None
    
    return user