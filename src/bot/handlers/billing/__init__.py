from aiogram import Router

from . import billing, templates

router = Router(name="billing")
router.include_router(billing.router)
router.include_router(templates.router)

__all__ = ["router"]
