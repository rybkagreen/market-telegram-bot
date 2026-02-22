"""
FastAPI приложение для Mini App Telegram бота.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers import auth, campaigns, analytics, billing
from src.config.settings import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan контекст для инициализации и закрытия пула БД.
    """
    logger.info("Starting FastAPI application...")
    # Инициализация пула БД происходит лениво через async_session_factory

    yield

    logger.info("Shutting down FastAPI application...")
    # Закрытие пула БД происходит автоматически


app = FastAPI(
    title="Market Telegram Bot API",
    description="API для Mini App Telegram бота",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS для Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production заменить на конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
app.include_router(auth, prefix="/api/auth", tags=["Auth"])
app.include_router(campaigns, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(analytics, prefix="/api/analytics", tags=["Analytics"])
app.include_router(billing, prefix="/api/billing", tags=["Billing"])


@app.get("/health")
async def health_check():
    """Проверка здоровья API."""
    return {"status": "healthy", "environment": settings.environment}


@app.get("/")
async def root():
    """Корневой эндпоинт."""
    return {
        "message": "Market Telegram Bot API",
        "docs": "/docs",
        "health": "/health",
    }
