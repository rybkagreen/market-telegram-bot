"""
API роутеры для Mini App.
"""

from src.api.routers.analytics import router as analytics
from src.api.routers.auth import router as auth
from src.api.routers.billing import router as billing
from src.api.routers.campaigns import router as campaigns

__all__ = ["auth", "campaigns", "analytics", "billing"]
