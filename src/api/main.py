"""
FastAPI приложение для Mini App Telegram бота.
"""

import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from slowapi.errors import RateLimitExceeded

from src.api.middleware.audit_middleware import AuditMiddleware
from src.api.middleware.log_sanitizer import sanitized_validation_error_handler
from src.api.routers.acts import router as acts_router  # ДОБАВЛЕНО (S-26 F.1)
from src.api.routers.admin import router as admin_router  # ДОБАВЛЕНО (PHASE-2)
from src.api.routers.ai import router as ai_router
from src.api.routers.analytics import router as analytics_router
from src.api.routers.auth import router as auth_router
from src.api.routers.auth_login_code import router as auth_login_code_router  # ДОБАВЛЕНО (S-29)
from src.api.routers.auth_login_widget import router as auth_login_widget_router  # ДОБАВЛЕНО (S-27)
from src.api.routers.billing import router as billing_router
from src.api.routers.campaigns import router as campaigns_router
from src.api.routers.categories import router as categories_router
from src.api.routers.channel_settings import router as channel_settings_router
from src.api.routers.channels import router as channels_router
from src.api.routers.contracts import router as contracts_router
from src.api.routers.disputes import router as disputes_router
from src.api.routers.document_validation import router as document_validation_router
from src.api.routers.feedback import router as feedback_router  # ДОБАВЛЕНО (2026-03-18)
from src.api.routers.legal_profile import router as legal_profile_router
from src.api.routers.ord import router as ord_router
from src.api.routers.payouts import router as payouts_router
from src.api.routers.placements import router as placements_router
from src.api.routers.reputation import router as reputation_router
from src.api.routers.reviews import router as reviews_router
from src.api.routers.uploads import router as uploads_router
from src.api.routers.users import router as users_router
from src.api.routers.webhooks import router as webhooks_router
from src.config.settings import settings
from src.core.exceptions import RekHarborError
from src.core.middleware.rate_limit import (
    init_limiter,
    rate_limit_exceeded_handler,
)

logger = logging.getLogger(__name__)

_SENTRY_PII_KEYS = {
    "passport_series",
    "passport_number",
    "passport_issued_by",
    "bank_account",
    "bank_corr_account",
    "yoomoney_wallet",
    "inn_scan_file_id",
    "passport_scan_file_id",
    "file_id",
    "authorization",
    "x-api-key",
    "password",
    "token",
}


def _scrub_pii(event: dict, hint: dict) -> dict:
    def _clean(obj: object) -> object:
        if isinstance(obj, dict):
            return {
                k: "***" if k.lower() in _SENTRY_PII_KEYS else _clean(v) for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_clean(i) for i in obj]
        return obj

    if "request" in event:
        event["request"] = _clean(event["request"])
    return event


if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        before_send=_scrub_pii,  # type: ignore[arg-type]
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan контекст для инициализации и закрытия пула БД.
    """
    logger.info("Starting FastAPI application...")
    # Инициализация пула БД происходит лениво через async_session_factory

    # ─── ORD Provider injection (S-28 Phase 2) ────────────────
    from src.core.services.ord_service import OrdService

    if settings.ord_provider == "yandex" and settings.ord_api_key:
        try:
            from src.core.services.ord_service import OrdService
            from src.core.services.yandex_ord_provider import YandexOrdProvider

            provider = YandexOrdProvider(
                api_key=settings.ord_api_key,
                base_url=settings.ord_api_url or "https://ord.yandex.ru",
                rekharbor_org_id=settings.ord_rekharbor_org_id,
                rekharbor_inn=settings.ord_rekharbor_inn,
            )
            OrdService.set_default_provider(provider)
            logger.info(
                "ORD: YandexOrdProvider initialized (org_id=%s, key=...%s)",
                settings.ord_rekharbor_org_id,
                settings.ord_api_key[-4:],
            )
        except Exception as e:
            logger.error("ORD: failed to initialize YandexOrdProvider, falling back to stub: %s", e)
    else:
        logger.info("ORD: using StubOrdProvider (ORD_PROVIDER=%s)", settings.ord_provider)

    yield

    # ─── Cleanup ──────────────────────────────────────────────
    provider = OrdService.get_default_provider()
    if hasattr(provider, "close"):
        await provider.close()

    logger.info("Shutting down FastAPI application...")
    # Закрытие пула БД происходит автоматически


app = FastAPI(
    title="Market Telegram Bot API",
    description="API для Mini App Telegram бота",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add security headers to all responses (P5 security hardening)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store"  # Prevent caching sensitive API responses
    response.headers["Pragma"] = "no-cache"
    return response


# Audit middleware — logs access to sensitive routes (/api/legal-profile, /api/contracts, /api/ord)
app.add_middleware(AuditMiddleware)

# CORS для Mini App и Web Portal — must be added last so it executes first (LIFO order)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.rekharbor.ru",
        "https://rekharbor.ru",
        "http://localhost:5173",  # mini_app dev
        "http://localhost:5174",  # web_portal dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Роутеры
_AUTH_PREFIX = "/api/auth"
app.include_router(ai_router, prefix="/api/ai", tags=["AI"])
app.include_router(auth_router, prefix=_AUTH_PREFIX, tags=["Auth"])
app.include_router(auth_login_widget_router, prefix=_AUTH_PREFIX, tags=["Auth"])  # ДОБАВЛЕНО (S-27)
app.include_router(auth_login_code_router, prefix=_AUTH_PREFIX, tags=["Auth"])  # ДОБАВЛЕНО (S-29)
app.include_router(users_router, prefix="/api/users", tags=["Users"])
app.include_router(campaigns_router, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(billing_router, prefix="/api/billing", tags=["Billing"])
app.include_router(channels_router, prefix="/api/channels", tags=["Channels"])
app.include_router(disputes_router, prefix="/api/disputes", tags=["Disputes"])
app.include_router(
    feedback_router, prefix="/api/feedback", tags=["Feedback"]
)  # ДОБАВЛЕНО (2026-03-18)
app.include_router(admin_router, prefix="/api", tags=["Admin"])  # ДОБАВЛЕНО (PHASE-2)
app.include_router(payouts_router, prefix="/api/payouts", tags=["Payouts"])
app.include_router(placements_router, prefix="/api/placements", tags=["Placements"])
app.include_router(
    channel_settings_router, prefix="/api/channel-settings", tags=["Channel Settings"]
)
app.include_router(reputation_router, prefix="/api/reputation", tags=["Reputation"])
app.include_router(reviews_router, prefix="/api/reviews", tags=["Reviews"])
app.include_router(categories_router, prefix="/api/categories", tags=["Categories"])
app.include_router(legal_profile_router)
app.include_router(document_validation_router)
app.include_router(contracts_router)
app.include_router(acts_router)
app.include_router(ord_router)
app.include_router(uploads_router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(webhooks_router)


# ═══════════════════════════════════════════════════════════════
# Exception handlers (Спринт 4)
# ═══════════════════════════════════════════════════════════════

# Rate limiter — инициализация с Redis
_limiter = init_limiter(redis_url=settings.redis_url_sync)
app.state.limiter = _limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_exception_handler(RequestValidationError, sanitized_validation_error_handler)  # type: ignore[arg-type]


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
