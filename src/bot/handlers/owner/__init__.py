from aiogram import Router

from . import channel_owner, channels_db, channels_db_mediakit

router = Router(name="owner")
router.include_router(channel_owner.router)
router.include_router(channels_db.router)
router.include_router(channels_db_mediakit.router)

__all__ = ["router"]
