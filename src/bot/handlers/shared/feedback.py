"""Shared feedback handler."""

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.bot.states.feedback import FeedbackStates

router = Router()


@router.callback_query(lambda c: c.data == "main:feedback")
async def feedback_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать обратную связь."""
    await state.set_state(FeedbackStates.entering_text)
    await callback.answer("Отправьте ваше сообщение", show_alert=True)
    await callback.message.answer("📝 Напишите ваше сообщение и отправьте:")


@router.message(FeedbackStates.entering_text)
async def feedback_text(message: Message, state: FSMContext) -> None:
    """Получить текст обратной связи."""
    await state.clear()
    await message.answer("✅ Сообщение отправлено! Спасибо за обратную связь.")
