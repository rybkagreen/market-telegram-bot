"""
Handlers для мониторинга сервера (диск, память, CPU).
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from src.bot.filters.admin import AdminFilter
from src.bot.keyboards.admin import AdminCB
from src.bot.utils.safe_callback import safe_callback_edit

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())


@router.callback_query(AdminCB.filter(F.action == "server_monitoring"))
async def show_server_monitoring(callback: CallbackQuery) -> None:
    """
    Показать мониторинг сервера.
    """
    # Получаем информацию через SSH
    try:
        # Это заглушка — в реальности нужно выполнять SSH команды
        # Для безопасности лучше сделать отдельный API endpoint
        text = (
            "🖥 <b>Мониторинг сервера</b>\n\n"
            "ℹ️ Мониторинг доступен через SSH:\n"
            "<code>ssh zerodolg-server 'df -h / && free -h'</code>\n\n"
            "Или через веб-интерфейс Flower:\n"
            "http://<server-ip>:5555"
        )

        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
        builder.adjust(1)

        await safe_callback_edit(callback, text, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"Server monitoring error: {e}")
        await callback.answer("Ошибка получения данных", show_alert=True)


@router.callback_query(AdminCB.filter(F.action == "celery_tasks"))
async def show_celery_tasks(callback: CallbackQuery) -> None:
    """
    Показать задачи Celery.
    """
    try:
        text = (
            "📋 <b>Задачи Celery</b>\n\n"
            "ℹ️ Управление задачами доступно через Flower:\n"
            "http://<server-ip>:5555\n\n"
            "<b>Планировщик (Celery Beat):</b>\n"
            "• refresh-chat-database — каждые 24ч\n"
            "• check-scheduled-campaigns — каждые 5мин\n"
            "• delete-old-logs — каждое воскресенье\n"
            "• check-low-balance — каждый час\n"
            "• update-chat-statistics — каждые 6ч\n"
            "• archive-old-campaigns — 1-го числа месяца\n"
            "• check-plan-renewals — ежедневно в 03:00\n"
            "• check-pending-invoices — каждые 5мин\n"
        )

        from aiogram.utils.keyboard import InlineKeyboardBuilder

        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
        builder.adjust(1)

        await safe_callback_edit(callback, text, reply_markup=builder.as_markup())

    except Exception as e:
        logger.error(f"Celery tasks error: {e}")
        await callback.answer("Ошибка получения данных", show_alert=True)
