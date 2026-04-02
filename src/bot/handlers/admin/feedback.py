"""Admin feedback handlers — просмотр и ответы на feedback."""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.filters.admin import AdminFilter
from src.bot.states.admin_feedback import AdminFeedbackStates
from src.db.models.feedback import FeedbackStatus
from src.db.repositories.feedback_repo import FeedbackRepository
from src.db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)
router = Router()

BACK_BTN = "🔙 Назад"
FEEDBACK_NOT_FOUND = "❌ Feedback не найден"

_STATUS_LABELS = {
    "new": "🆕 Новый",
    "in_progress": "🟡 В работе",
    "resolved": "✅ Решён",
    "rejected": "❌ Отклонён",
}


# ---------------------------------------------------------------------------
# admin:feedback — список всех feedback
# ---------------------------------------------------------------------------


@router.callback_query(F.data == "admin:feedback", AdminFilter())
async def admin_feedback_list(callback: CallbackQuery, session: AsyncSession) -> None:
    """Список всех feedback."""
    feedbacks = await FeedbackRepository(session).get_by_status(
        FeedbackStatus.NEW,
        limit=20,
    )

    builder = InlineKeyboardBuilder()
    for fb in feedbacks[:15]:
        icon = "🔴" if fb.status == FeedbackStatus.NEW else "🟢"
        builder.button(
            text=f"{icon} Feedback #{fb.id}",
            callback_data=f"admin:feedback:{fb.id}",
        )
    builder.button(text=BACK_BTN, callback_data="admin:panel")
    builder.adjust(1)

    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(
        f"📬 *Feedback пользователей*\n\nНовых: *{len(feedbacks)}*\n\nПоследние 15:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# admin:feedback:{id} — детали feedback
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^admin:feedback:(\d+)$"), AdminFilter())
async def admin_view_feedback(callback: CallbackQuery, session: AsyncSession) -> None:
    """Детали feedback для ответа."""
    feedback_id = int((callback.data or "").split(":")[-1])

    feedback = await FeedbackRepository(session).get_by_id(feedback_id)
    if not feedback:
        await callback.answer(FEEDBACK_NOT_FOUND, show_alert=True)
        return

    # Получаем данные пользователя
    user = await UserRepository(session).get_by_id(feedback.user_id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return
    username = f"@{user.username}" if user.username else f"ID: {user.telegram_id}"

    status_label = _STATUS_LABELS.get(feedback.status, feedback.status)

    text = (
        f"📬 *Feedback #{feedback.id}*\n\n"
        f"👤 Пользователь: {username}\n"
        f"📅 Создан: {feedback.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"📊 Статус: {status_label}\n\n"
        f"📝 *Текст:*\n"
        f"_{feedback.text}_\n\n"
    )

    if feedback.admin_response:
        text += f"✅ *Ответ:*\n_{feedback.admin_response}_\n\n"

    builder = InlineKeyboardBuilder()
    if feedback.status == FeedbackStatus.NEW:
        builder.button(
            text="✏️ Ответить",
            callback_data=f"admin:feedback:respond:{feedback.id}",
        )
        builder.button(
            text="🟡 В работу",
            callback_data=f"admin:feedback:status:in_progress:{feedback.id}",
        )
    elif feedback.status == FeedbackStatus.IN_PROGRESS:
        builder.button(
            text="✏️ Ответить",
            callback_data=f"admin:feedback:respond:{feedback.id}",
        )
        builder.button(
            text="✅ Решён",
            callback_data=f"admin:feedback:status:resolved:{feedback.id}",
        )
    else:
        builder.button(
            text="🔁 Открыть заново",
            callback_data=f"admin:feedback:status:new:{feedback.id}",
        )

    builder.button(text=BACK_BTN, callback_data="admin:feedback")
    builder.adjust(1)

    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# admin:feedback:respond:{id} — начать ответ
# ---------------------------------------------------------------------------


@router.callback_query(F.data.regexp(r"^admin:feedback:respond:(\d+)$"), AdminFilter())
async def admin_start_respond(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Начать ответ на feedback."""
    feedback_id = int((callback.data or "").split(":")[-1])

    feedback = await FeedbackRepository(session).get_by_id(feedback_id)
    if not feedback:
        await callback.answer(FEEDBACK_NOT_FOUND, show_alert=True)
        return

    await state.set_data({"feedback_id": feedback_id})
    await state.set_state(AdminFeedbackStates.waiting_for_response)

    if not isinstance(callback.message, Message):
        return
    await callback.message.edit_text(
        f"✏️ *Ответ на feedback #{feedback_id}*\n\nОтправьте текст ответа:",
        reply_markup=None,
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(AdminFeedbackStates.waiting_for_response, AdminFilter())
async def admin_save_response(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Сохранить ответ админа."""
    data = await state.get_data()
    feedback_id = data.get("feedback_id")

    if not feedback_id:
        await message.answer("❌ Ошибка: feedback_id не найден")
        await state.clear()
        return

    response_text = message.text or ""
    if message.from_user is None:
        return
    admin_db_user = await UserRepository(session).get_by_telegram_id(message.from_user.id)
    if admin_db_user is None:
        await message.answer("❌ Ошибка: администратор не найден")
        await state.clear()
        return
    admin_user_id = admin_db_user.id

    repo = FeedbackRepository(session)
    feedback = await repo.respond_to_feedback(
        feedback_id=feedback_id,
        admin_user_id=admin_user_id,
        response_text=response_text,
        status=FeedbackStatus.RESOLVED,
    )

    if not feedback:
        await message.answer("❌ Ошибка при сохранении ответа")
        await state.clear()
        return

    await message.answer(
        f"✅ *Ответ сохранён!*\n\nFeedback #{feedback_id} помечен как решённый.",
        parse_mode="Markdown",
    )

    await state.clear()

    # Возвращаемся к списку
    builder = InlineKeyboardBuilder()
    builder.button(text=BACK_BTN, callback_data="admin:feedback")
    builder.adjust(1)

    await message.answer(
        "Выберите действие:",
        reply_markup=builder.as_markup(),
    )


# ---------------------------------------------------------------------------
# admin:feedback:status:{status}:{id} — изменить статус
# ---------------------------------------------------------------------------


@router.callback_query(
    F.data.regexp(r"^admin:feedback:status:(new|in_progress|resolved):(\d+)$"),
    AdminFilter(),
)
async def admin_change_status(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Изменить статус feedback."""
    parts = (callback.data or "").split(":")
    new_status_str = parts[3]
    feedback_id = int(parts[4])

    status_map = {
        "new": FeedbackStatus.NEW,
        "in_progress": FeedbackStatus.IN_PROGRESS,
        "resolved": FeedbackStatus.RESOLVED,
    }
    new_status = status_map.get(new_status_str)

    if not new_status:
        await callback.answer("❌ Неверный статус", show_alert=True)
        return

    feedback = await FeedbackRepository(session).get_by_id(feedback_id)
    if not feedback:
        await callback.answer(FEEDBACK_NOT_FOUND, show_alert=True)
        return

    feedback.status = new_status
    await session.flush()

    status_label = _STATUS_LABELS.get(new_status_str, new_status_str)
    await callback.answer(f"✅ Статус изменён: {status_label}")

    # Обновляем сообщение
    await admin_view_feedback(callback, session)
