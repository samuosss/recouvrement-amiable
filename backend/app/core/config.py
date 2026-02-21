from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Système de Recouvrement Intelligent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql://recouvrement_user:recouvrement_pass_2024@postgres:5432/recouvrement_db"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # JWT Security
    SECRET_KEY: str = "your-super-secret-key-change-me-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"
    
    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

# DEBUG
print("=" * 70)
print(f"🔐 SECRET_KEY chargée: {settings.SECRET_KEY}")
print(f"🔑 ALGORITHM: {settings.ALGORITHM}")
print("=" * 70)
