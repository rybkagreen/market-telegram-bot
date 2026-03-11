from aiogram import Router

from . import cabinet, feedback, help, start

router = Router(name="shared")
router.include_router(start.router)
router.include_router(cabinet.router)
router.include_router(feedback.router)
router.include_router(help.router)

__all__ = ["router"]
