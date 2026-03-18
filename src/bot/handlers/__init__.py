# src/bot/handlers/__init__.py
"""Main router with all sub-routers."""

from aiogram import Router

from src.bot.handlers.admin.disputes import router as admin_disputes_router
from src.bot.handlers.admin.users import router as admin_router
from src.bot.handlers.advertiser.analytics import router as advertiser_analytics_router
from src.bot.handlers.advertiser.campaigns import router as campaigns_router
from src.bot.handlers.billing.billing import router as billing_router
from src.bot.handlers.dispute.dispute import router as dispute_router
from src.bot.handlers.owner.analytics import router as owner_analytics_router
from src.bot.handlers.owner.arbitration import router as arbitration_router
from src.bot.handlers.owner.channel_owner import router as channel_owner_router
from src.bot.handlers.owner.channel_settings import router as channel_settings_router
from src.bot.handlers.payout.payout import router as payout_router
from src.bot.handlers.placement.placement import router as placement_router
from src.bot.handlers.shared.cabinet import router as cabinet_router
from src.bot.handlers.shared.feedback import router as feedback_router
from src.bot.handlers.shared.help import router as help_router
from src.bot.handlers.shared.start import router as start_router

main_router = Router()

# Router order: shared → billing → payout → advertiser → placement → owner → admin → dispute
main_router.include_router(start_router)
main_router.include_router(cabinet_router)
main_router.include_router(help_router)
main_router.include_router(feedback_router)
main_router.include_router(billing_router)
main_router.include_router(payout_router)
main_router.include_router(advertiser_analytics_router)
main_router.include_router(campaigns_router)
main_router.include_router(placement_router)
main_router.include_router(owner_analytics_router)
main_router.include_router(channel_owner_router)
main_router.include_router(channel_settings_router)
main_router.include_router(arbitration_router)
main_router.include_router(dispute_router)
main_router.include_router(admin_router)
main_router.include_router(admin_disputes_router)
