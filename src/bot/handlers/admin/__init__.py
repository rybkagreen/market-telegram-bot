"""
Admin handlers submodules.
Разбито для удобства поддержки (вместо одного файла на 1584 строки).
"""

from src.bot.handlers.admin.ai import router as ai_router
from src.bot.handlers.admin.analytics import router as analytics_router
from src.bot.handlers.admin.campaigns import router as campaigns_router
from src.bot.handlers.admin.users import router as users_router

__all__ = ["analytics_router", "campaigns_router", "users_router", "ai_router"]
