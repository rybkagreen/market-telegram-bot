from aiogram import Router

from . import arbitration, channel_settings, placement

router = Router(name="placement")
router.include_router(placement.router)
router.include_router(arbitration.router)
router.include_router(channel_settings.router)

__all__ = ["router"]
