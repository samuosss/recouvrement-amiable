from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_access_token,  # ← CORRIGÉ
    get_current_active_user,
    blacklist_token,
    oauth2_scheme
)
from app.core.config import settings
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    Token,
    RefreshTokenRequest,
    UserProfile
)
from app.models.utilisateur import Utilisateur

router = APIRouter()

@router.post("/login", response_model=Token)
def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Endpoint OAuth2 compatible avec le formulaire Swagger
    
    **IMPORTANT pour Swagger:**
    - Username = votre email
    - Password = votre mot de passe
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )
    
    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role.value,
            "user_id": user.id_utilisateur
        }
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.email}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

@router.post("/login-json", response_model=LoginResponse)
def login_json(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login avec JSON
    """
    user = authenticate_user(db, login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )
    
    if not user.actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )
    
    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role.value,
            "user_id": user.id_utilisateur
        }
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.email}
    )
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserProfile.from_orm(user)
    )

@router.post("/refresh", response_model=Token)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Rafraîchir un access token
    """
    try:
        payload = decode_access_token(refresh_data.refresh_token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide"
            )
        
        email = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide"
            )
        
        user = db.query(Utilisateur).filter(Utilisateur.email == email).first()
        
        if not user or not user.actif:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur invalide"
            )
        
        new_access_token = create_access_token(
            data={
                "sub": user.email,
                "role": user.role.value,
                "user_id": user.id_utilisateur
            }
        )
        
        new_refresh_token = create_refresh_token(
            data={"sub": user.email}
        )
        
        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré"
        )

@router.get("/me", response_model=UserProfile)
def get_current_user_profile(
    current_user: Utilisateur = Depends(get_current_active_user)
):
    """
    Récupérer le profil de l'utilisateur connecté
    """
    return UserProfile.from_orm(current_user)

@router.post("/logout")
def logout(
    token: str = Depends(oauth2_scheme),
    current_user: Utilisateur = Depends(get_current_active_user)
):
    """
    Déconnecter l'utilisateur
    """
    blacklist_token(token)
    
    return {
        "message": "Déconnexion réussie",
        "detail": "Votre token a été révoqué"
    }
