"""
FastAPI приложение для Mini App Telegram бота.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routers.analytics import router as analytics_router
from src.api.routers.auth import router as auth_router
from src.api.routers.billing import router as billing_router
from src.api.routers.campaigns import router as campaigns_router
from src.api.routers.channel_settings import router as channel_settings_router
from src.api.routers.channels import router as channels_router
from src.api.routers.disputes import router as disputes_router
from src.api.routers.feedback import router as feedback_router  # ДОБАВЛЕНО (2026-03-18)
from src.api.routers.admin import router as admin_router  # ДОБАВЛЕНО (PHASE-2)
from src.api.routers.payouts import router as payouts_router
from src.api.routers.placements import router as placements_router
from src.api.routers.reputation import router as reputation_router
from src.api.routers.users import router as users_router
from src.config.settings import settings
from src.core.exceptions import RekHarborError

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
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(campaigns_router, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(billing_router, prefix="/api/billing", tags=["Billing"])
app.include_router(channels_router, prefix="/api/channels", tags=["Channels"])
app.include_router(disputes_router, prefix="/api/disputes", tags=["Disputes"])
app.include_router(feedback_router, prefix="/api/feedback", tags=["Feedback"])  # ДОБАВЛЕНО (2026-03-18)
app.include_router(admin_router, prefix="/api", tags=["Admin"])  # ДОБАВЛЕНО (PHASE-2)
app.include_router(payouts_router, prefix="/api/payouts", tags=["Payouts"])
app.include_router(placements_router, prefix="/api/placements", tags=["Placements"])
app.include_router(channel_settings_router, prefix="/api/channel-settings", tags=["Channel Settings"])
app.include_router(reputation_router, prefix="/api/reputation", tags=["Reputation"])


# ═══════════════════════════════════════════════════════════════
# Exception handlers (Спринт 4)
# ═══════════════════════════════════════════════════════════════


@app.exception_handler(RekHarborError)
async def rekharbor_error_handler(request, exc: RekHarborError):
    """Handler для бизнес-ошибок проекта."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_type": type(exc).__name__},
    )


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
