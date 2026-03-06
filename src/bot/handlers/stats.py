"""
Handlers для команды /stats — публичная статистика платформы.
Спринт 0: доступно без авторизации (гостям).
"""
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from src.core.services.analytics_service import PlatformStats, analytics_service

logger = logging.getLogger(__name__)
router = Router(name="stats")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    """
    Показать публичную статистику платформы.

    Команда доступна всем пользователям (гостям).
    """
    try:
        stats: PlatformStats = await analytics_service.get_platform_stats()

        text = (
            "📊 <b>Статистика платформы RekHarbor</b>\n\n"
            f"✅ <b>Активных каналов:</b> {stats.active_channels:,}\n"
            f"👥 <b>Суммарный охват:</b> {stats.total_reach:,}\n"
            f"🚀 <b>Запущено кампаний:</b> {stats.campaigns_launched:,}\n"
            f"✅ <b>Завершено успешно:</b> {stats.campaigns_completed:,}\n"
            f"⭐ <b>Средний рейтинг каналов:</b> {stats.avg_channel_rating:.1f}/10\n"
            f"💰 <b>Выплачено владельцам:</b> {stats.total_payouts:,.2f} ₽\n\n"
            "🔗 <i>Присоединяйтесь к платформе: /start</i>"
        )

        await message.answer(text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in /stats: {e}")
        await message.answer(
            "❌ Не удалось загрузить статистику. Попробуйте позже.",
            parse_mode="HTML",
        )
