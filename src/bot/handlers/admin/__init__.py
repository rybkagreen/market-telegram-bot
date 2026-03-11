"""
Admin handlers submodules.
Разбито для удобства поддержки (вместо одного файла на 1584 строки).
"""

from aiogram import Router

from src.bot.handlers.admin.ai import router as ai_router
from src.bot.handlers.admin.analytics import router as analytics_router
from src.bot.handlers.admin.campaigns import router as campaigns_router
from src.bot.handlers.admin.monitoring import router as monitoring_router
from src.bot.handlers.admin.stats import router as stats_router
from src.bot.handlers.admin.users import router as users_router

router = Router(name="admin")
router.include_router(users_router)
router.include_router(campaigns_router)
router.include_router(analytics_router)
router.include_router(ai_router)
router.include_router(stats_router)
router.include_router(monitoring_router)

__all__ = [
    "router",
    "analytics_router",
    "campaigns_router",
    "users_router",
    "ai_router",
    "stats_router",
    "monitoring_router",
]
