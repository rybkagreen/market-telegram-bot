"""Advertiser analytics handler."""

from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.utils.safe_callback import safe_callback_edit
from src.core.services.analytics_service import AnalyticsService
from src.db.repositories.user_repo import UserRepository

router = Router()


@router.callback_query(lambda c: c.data == "main:analytics")
async def show_advertiser_analytics(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать статистику рекламодателя. main:analytics НЕ main:owner_analytics!"""
    user_id = callback.from_user.id
    user = await UserRepository(session).get_by_telegram_id(user_id)
    if not user:
        return

    stats = await AnalyticsService().get_advertiser_stats(user.id, session)
    text = f"📊 Статистика\nКампаний: {stats.total_placements}\nЗавершено: {stats.completed_placements}\nПотрачено: {stats.total_spent} ₽\nОхват: {stats.total_reach}\nCTR: {stats.avg_ctr:.2f}%"
    await safe_callback_edit(callback, text)
