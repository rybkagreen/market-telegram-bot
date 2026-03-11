from aiogram import Router

from . import callback_schemas

router = Router(name="infra")
router.include_router(callback_schemas.router)

__all__ = ["router"]
