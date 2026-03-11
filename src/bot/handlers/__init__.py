from aiogram import Router

from . import admin, advertiser, billing, infra, owner, placement, shared

router = Router(name="root")
router.include_router(shared.router)
router.include_router(advertiser.router)
router.include_router(owner.router)
router.include_router(placement.router)
router.include_router(billing.router)
router.include_router(infra.router)
router.include_router(admin.router)  # admin — всегда последним!

__all__ = ["router"]
