"""
Handler для управления списком отслеживаемых чатов.
Пользователь добавляет чат → немедленный парсинг → результат.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from src.bot.utils.safe_callback import safe_callback_edit
from src.tasks.parser_tasks import parse_single_chat

router = Router()


class AddChatStates(StatesGroup):
    waiting_username = State()


@router.message(Command("addchat"))
async def handle_add_chat_start(message: Message, state: FSMContext) -> None:
    """Начать процесс добавления чата для отслеживания."""
    await state.set_state(AddChatStates.waiting_username)
    await message.answer(
        "📊 <b>Добавить канал/группу для отслеживания</b>\n\n"
        "Введите username канала или группы:\n"
        "<code>@username</code> или просто <code>username</code>\n\n"
        "Например: @durov, @tchannel, breakingnews"
    )


@router.message(AddChatStates.waiting_username)
async def handle_add_chat_username(message: Message, state: FSMContext) -> None:
    """Обработать введенный username и запустить парсинг."""
    if not message.text:
        await message.answer("Пожалуйста, введите username.")
        return
    username = message.text.lstrip("@").strip()
    if not username or len(username) < 3:
        await message.answer(
            "❌ Некорректный username. Попробуй ещё раз.\n"
            "Username должен содержать минимум 3 символа."
        )
        return

    await state.clear()
    status_msg = await message.answer(f"⏳ Парсю <b>@{username}</b>...")

    # Запустить парсинг асинхронно через Celery
    task = parse_single_chat.delay(username)

    # Ждём результат (с таймаутом 60 сек)
    try:
        result = task.get(timeout=60)
        if result["success"]:
            icon = "✅" if not result["is_new"] else "🆕"
            can_post_text = (
                "✅ Открыт для постинга" if result["can_post"] else "🔒 Закрыт для постинга"
            )
            text = (
                f"{icon} <b>{result['title']}</b> (@{username})\n\n"
                f"👥 Подписчиков: <b>{result['subscribers']:,}</b>\n"
                f"📊 ER: <b>{result['er']}%</b>\n"
                f"📝 Постинг: {can_post_text}\n\n"
                f"{'🎉 Добавлен в отслеживание!' if result['is_new'] else '📈 Данные обновлены.'}"
            )
        else:
            text = (
                f"❌ Не удалось получить данные:\n"
                f"<code>{result.get('error', 'неизвестная ошибка')}</code>"
            )
    except Exception:
        text = (
            "⏳ Парсинг занял слишком много времени.\n"
            "Данные появятся в течение суток после автоматического сбора статистики."
        )

    await status_msg.edit_text(text)


@router.callback_query(F.data == "cancel_add_chat")
async def handle_cancel_add_chat(callback: CallbackQuery, state: FSMContext) -> None:
    """Отменить добавление чата."""
    await state.clear()
    await safe_callback_edit(callback, "❌ Добавление чата отменено.")
