from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from loguru import logger

from app.core.config import settings
from app.api.v1.api import api_router
from app.models import comite  # add to imports
from app.core.database import Base, engine

app = FastAPI(
    title=os.getenv("APP_NAME", "Système de Recouvrement"),
    version=os.getenv("APP_VERSION", "1.0.0"),
    description="API Backend - Banque Zitouna",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
     allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # fallback
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    logger.info(f"🚀 Starting {os.getenv('APP_NAME')} v{os.getenv('APP_VERSION')}")

@app.get("/")
async def root():
    return {
        "app": os.getenv("APP_NAME"),
        "version": os.getenv("APP_VERSION"),
        "status": "running",
        "docs": "/api/docs"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}