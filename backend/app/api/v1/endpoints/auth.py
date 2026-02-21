from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.database import get_db
from app.core.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_active_user,
    oauth2_scheme  # ← AJOUTÉ

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
from app.core.token_blacklist import blacklist_token  # ← AJOUTÉ
from app.core.token_blacklist import revoke_all_user_tokens


router = APIRouter()

# ========================
# ENDPOINT OAUTH2 POUR SWAGGER
# ========================

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
    
    Retourne uniquement les tokens (format OAuth2 standard)
    """
    # OAuth2 utilise "username" mais nous utilisons "email"
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
            detail="Compte désactivé. Contactez l'administrateur.",
        )
    
    # Créer les tokens
    access_token = create_access_token(
        data={
            "sub": user.id_utilisateur,
            "email": user.email,
            "role": user.role.value,
            "agence_id": user.id_agence
        }
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.id_utilisateur}
    )
    
    # Traçabilité (optionnel)
    from app.models.tracabilite import Tracabilite, ActionEnum
    from datetime import datetime
    
    trace = Tracabilite(
        table_cible="utilisateurs",
        id_enregistrement=user.id_utilisateur,
        action=ActionEnum.CONSULTATION,
        id_utilisateur=user.id_utilisateur,
        date_action=datetime.now(),
        description=f"Connexion OAuth2: {user.email}"
    )
    db.add(trace)
    db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

# ========================
# ENDPOINT JSON ALTERNATIF (optionnel)
# ========================

@router.post("/login-json", response_model=LoginResponse)
def login_json(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login avec JSON (alternative au formulaire OAuth2)
    
    Retourne les tokens + informations utilisateur
    """
    user = authenticate_user(db, login_data.email, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé. Contactez l'administrateur.",
        )
    
    # Créer les tokens
    access_token = create_access_token(
        data={
            "sub": user.id_utilisateur,
            "email": user.email,
            "role": user.role.value,
            "agence_id": user.id_agence
        }
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.id_utilisateur}
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
    Rafraîchir un access token avec un refresh token
    """
    try:
        payload = decode_token(refresh_data.refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide"
            )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide"
            )
        
        user = db.query(Utilisateur).filter(
            Utilisateur.id_utilisateur == user_id
        ).first()
        
        if not user or not user.actif:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur invalide ou inactif"
            )
        
        new_access_token = create_access_token(
            data={
                "sub": user.id_utilisateur,
                "email": user.email,
                "role": user.role.value,
                "agence_id": user.id_agence
            }
        )
        
        new_refresh_token = create_refresh_token(
            data={"sub": user.id_utilisateur}
        )
        
        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )
        
    except HTTPException:
        raise
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
    Récupérer le profil de l'utilisateur actuellement connecté
    """
    return UserProfile.from_orm(current_user)

@router.post("/logout")
def logout(
    token: str = Depends(oauth2_scheme),  # ← AJOUTÉ : récupérer le token
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Déconnecter l'utilisateur et révoquer le token
    """
    try:
        # Décoder le token pour obtenir l'expiration
        payload = decode_token(token)
        exp = payload.get("exp")
        
        if exp:
            import time
            current_time = int(time.time())
            expires_in = exp - current_time
            
            if expires_in > 0:
                # Blacklister le token
                success = blacklist_token(token, expires_in)
                
                if not success:
                    print("❌ Échec du blacklist, mais logout enregistré")
        
        # Traçabilité
        from app.models.tracabilite import Tracabilite, ActionEnum
        from datetime import datetime
        
        trace = Tracabilite(
            table_cible="utilisateurs",
            id_enregistrement=current_user.id_utilisateur,
            action=ActionEnum.CONSULTATION,
            id_utilisateur=current_user.id_utilisateur,
            date_action=datetime.now(),
            description=f"Déconnexion: {current_user.email}"
        )
        db.add(trace)
        db.commit()
        
        return {
            "message": "Déconnexion réussie",
            "detail": "Votre token a été révoqué"
        }
        
    except Exception as e:
        print(f"❌ Erreur logout: {e}")
        return {"message": "Déconnexion réussie"}
    
@router.post("/logout-all")
def logout_all_devices(
    current_user: Utilisateur = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Déconnecter l'utilisateur de TOUS ses appareils
    
    Utile en cas de :
    - Changement de mot de passe
    - Compromission de sécurité
    """
    success = revoke_all_user_tokens(current_user.id_utilisateur)
    
    if success:
        from app.models.tracabilite import Tracabilite, ActionEnum
        from datetime import datetime
        
        trace = Tracabilite(
            table_cible="utilisateurs",
            id_enregistrement=current_user.id_utilisateur,
            action=ActionEnum.MODIFICATION,
            id_utilisateur=current_user.id_utilisateur,
            date_action=datetime.now(),
            description=f"Déconnexion globale (tous appareils): {current_user.email}"
        )
        db.add(trace)
        db.commit()
        
        return {
            "message": "Déconnexion réussie sur tous les appareils",
            "detail": "Tous vos tokens ont été révoqués"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la révocation des tokens"
        )