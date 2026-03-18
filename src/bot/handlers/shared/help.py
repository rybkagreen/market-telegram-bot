"""Shared help handler."""

from aiogram import Router
from aiogram.types import CallbackQuery

router = Router()


@router.callback_query(lambda c: c.data == "main:help")
async def show_help(callback: CallbackQuery) -> None:
    """Показать помощь."""
    text = "ℹ️ Помощь\n\nРекламодатель: создание кампаний, аналитика\nВладелец: каналы, заявки, выплаты\n\n/support - поддержка"
    await callback.answer(text, show_alert=True)
