"""
API роутеры для Mini App.
"""

from src.api.routers.analytics import router as analytics
from src.api.routers.auth import router as auth
from src.api.routers.billing import router as billing
from src.api.routers.campaigns import router as campaigns
from src.api.routers.channel_settings import router as channel_settings
from src.api.routers.placements import router as placements
from src.api.routers.reputation import router as reputation

__all__ = [
    "auth",
    "campaigns",
    "analytics",
    "billing",
    "placements",
    "channel_settings",
    "reputation",
]
