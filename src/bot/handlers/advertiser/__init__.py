from aiogram import Router

from . import (
    analytics,
    analytics_chats,
    b2b,
    campaign_analytics,
    campaign_create_ai,
    campaigns,
    comparison,
)

router = Router(name="advertiser")
router.include_router(campaigns.router)
router.include_router(campaign_analytics.router)
router.include_router(campaign_create_ai.router)
router.include_router(analytics.router)
router.include_router(analytics_chats.router)
router.include_router(comparison.router)
router.include_router(b2b.router)

__all__ = ["router"]
