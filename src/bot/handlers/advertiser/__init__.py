from aiogram import Router

from . import (
    analytics,
    analytics_chats,
    campaign_analytics,
    campaign_create_ai,
    campaigns,
    comparison,
    placement_entry,  # S-PLACEMENT-ENTRY: MUST BE FIRST to intercept main:create_campaign
)

router = Router(name="advertiser")
router.include_router(placement_entry.router)  # FIRST — intercepts main:create_campaign
router.include_router(campaigns.router)
router.include_router(campaign_analytics.router)
router.include_router(campaign_create_ai.router)
router.include_router(analytics.router)
router.include_router(analytics_chats.router)
router.include_router(comparison.router)

# v4.3: B2B packages removed — b2b.router removed

__all__ = ["router"]
