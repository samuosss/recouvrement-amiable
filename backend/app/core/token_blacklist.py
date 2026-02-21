"""
Système de blacklist de tokens JWT avec Redis

Ce module gère la révocation des tokens JWT en les stockant dans Redis
avec une expiration automatique correspondant à la durée de vie du token.

Architecture:
    - Clé Redis: "blacklist:{token_hash}"
    - Valeur: "revoked"
    - TTL: Temps restant avant expiration du token

Sécurité:
    - Tokens révoqués automatiquement supprimés après expiration
    - Pas de stockage permanent des tokens
    - Performance optimisée avec Redis
"""

import redis
import hashlib
from typing import Optional
from datetime import datetime, timedelta
from app.core.config import settings

# Connexion Redis avec pool de connexions
redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
    socket_keepalive=True,
    socket_connect_timeout=5
)

def _hash_token(token: str) -> str:
    """
    Hasher le token pour éviter de stocker le token complet en Redis
    
    Sécurité: On ne stocke que le hash SHA256 du token, pas le token lui-même
    
    Args:
        token: Token JWT complet
        
    Returns:
        Hash SHA256 du token (64 caractères hexadécimaux)
    """
    return hashlib.sha256(token.encode()).hexdigest()

def blacklist_token(token: str, expires_in_seconds: int) -> bool:
    """
    Ajouter un token à la blacklist avec expiration automatique
    
    Le token est hashé avant stockage pour des raisons de sécurité.
    Redis supprimera automatiquement l'entrée après expiration.
    
    Args:
        token: Le token JWT à blacklister
        expires_in_seconds: Durée de vie restante du token en secondes
        
    Returns:
        True si l'opération a réussi, False sinon
        
    Exemple:
        >>> blacklist_token("eyJhbGci...", 1800)  # Révoque pour 30 min
        True
    """
    try:
        token_hash = _hash_token(token)
        
        # Stocker dans Redis avec expiration automatique
        redis_client.setex(
            name=f"blacklist:{token_hash}",
            time=expires_in_seconds,
            value="revoked"
        )
        
        # Log pour audit
        print(f"🚫 Token révoqué (expire dans {expires_in_seconds}s)")
        
        return True
        
    except redis.RedisError as e:
        print(f"❌ Erreur Redis lors de la blacklist: {e}")
        return False

def is_token_blacklisted(token: str) -> bool:
    """
    Vérifier si un token est dans la blacklist
    
    Args:
        token: Le token JWT à vérifier
        
    Returns:
        True si le token est révoqué, False sinon
        
    Exemple:
        >>> is_token_blacklisted("eyJhbGci...")
        False
    """
    try:
        token_hash = _hash_token(token)
        exists = redis_client.exists(f"blacklist:{token_hash}")
        return exists > 0
        
    except redis.RedisError as e:
        print(f"❌ Erreur Redis lors de la vérification: {e}")
        # En cas d'erreur Redis, on refuse l'accès par sécurité
        return True

def revoke_all_user_tokens(user_id: int) -> bool:
    """
    Révoquer tous les tokens d'un utilisateur spécifique
    
    Utile pour:
    - Changement de mot de passe
    - Désactivation de compte
    - Compromission de sécurité
    
    Args:
        user_id: ID de l'utilisateur
        
    Returns:
        True si l'opération a réussi
        
    Note:
        Cette fonction nécessite de maintenir une liste des tokens actifs par utilisateur
    """
    try:
        # Stocker un flag indiquant que tous les tokens de cet utilisateur sont invalides
        redis_client.setex(
            name=f"user_logout:{user_id}",
            time=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            value=str(datetime.utcnow().timestamp())
        )
        
        print(f"🚫 Tous les tokens de l'utilisateur {user_id} révoqués")
        return True
        
    except redis.RedisError as e:
        print(f"❌ Erreur lors de la révocation globale: {e}")
        return False

def is_user_logged_out(user_id: int, token_issued_at: datetime) -> bool:
    """
    Vérifier si un utilisateur s'est déconnecté globalement après l'émission du token
    
    Args:
        user_id: ID de l'utilisateur
        token_issued_at: Date d'émission du token (claim 'iat')
        
    Returns:
        True si l'utilisateur s'est déconnecté après l'émission de ce token
    """
    try:
        logout_timestamp = redis_client.get(f"user_logout:{user_id}")
        
        if logout_timestamp:
            logout_time = float(logout_timestamp)
            token_time = token_issued_at.timestamp()
            
            # Si la déconnexion est après l'émission du token, le token est invalide
            return logout_time > token_time
            
        return False
        
    except (redis.RedisError, ValueError) as e:
        print(f"❌ Erreur lors de la vérification de logout global: {e}")
        return False

def get_blacklist_stats() -> dict:
    """
    Obtenir des statistiques sur la blacklist (pour monitoring)
    
    Returns:
        Dictionnaire avec les statistiques
    """
    try:
        # Compter les tokens blacklistés
        pattern = "blacklist:*"
        cursor = 0
        count = 0
        
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
            count += len(keys)
            if cursor == 0:
                break
        
        return {
            "tokens_blacklisted": count,
            "redis_connected": True
        }
        
    except redis.RedisError as e:
        return {
            "error": str(e),
            "redis_connected": False
        }