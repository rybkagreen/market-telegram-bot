"""Owner analytics handler."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.analytics_service import AnalyticsService
from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.models.transaction import Transaction, TransactionType
from src.db.repositories.telegram_chat_repo import TelegramChatRepository
from src.db.repositories.user_repo import UserRepository

router = Router()


@router.callback_query(lambda c: c.data == "main:owner_analytics")
async def show_owner_analytics(callback: CallbackQuery, session: AsyncSession) -> None:
    """Показать расширенную статистику владельца."""
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    channels = await TelegramChatRepository(session).get_by_owner(user.id)
    channels_count = len(channels)

    if not channels_count:
        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить канал", callback_data="own:add_channel")
        builder.button(text="🔙 Меню владельца", callback_data="main:own_menu")
        builder.adjust(1)
        await callback.message.edit_text(
            "📊 *Статистика владельца*\n\nУ вас пока нет каналов.",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown",
        )
        await callback.answer()
        return

    # Базовая статистика через AnalyticsService
    stats = await AnalyticsService().get_owner_stats(user.id, session)

    # Заработок за периоды — по транзакциям escrow_release
    now = datetime.now(UTC)

    async def _earned_since(since: datetime) -> Decimal:
        r = await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user.id,
                Transaction.type == TransactionType.escrow_release,
                Transaction.created_at >= since,
            )
        )
        return Decimal(str(r.scalar_one()))

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_earned = await _earned_since(today_start)
    week_earned = await _earned_since(now - timedelta(days=7))
    month_earned = await _earned_since(now - timedelta(days=30))

    avg_rating = sum(ch.rating for ch in channels) / channels_count

    # Разбивка по каналам (до 5)
    breakdown_lines = []
    for ch in channels[:5]:
        r = await session.execute(
            select(func.count()).where(
                PlacementRequest.channel_id == ch.id,
                PlacementRequest.status == PlacementStatus.published,
            )
        )
        ch_pubs = r.scalar_one()
        breakdown_lines.append(f"📺 @{ch.username}: {ch_pubs} публ. | ⭐{ch.rating:.1f}")
    channels_breakdown = "\n".join(breakdown_lines) if breakdown_lines else "Нет данных"

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Меню владельца", callback_data="main:own_menu")

    await callback.message.edit_text(
        f"📊 *Статистика владельца*\n\n"
        f"📺 Каналов: *{channels_count}*\n"
        f"✅ Публикаций: *{stats.total_published}*\n"
        f"💰 Заработано всего: *{stats.total_earned:.0f} ₽*\n"
        f"💰 Средний чек: *{stats.avg_check:.0f} ₽*\n"
        f"⭐ Средний рейтинг: *{avg_rating:.1f}*\n\n"
        f"─── По периодам ───\n"
        f"📅 Сегодня: *{today_earned:.0f} ₽*\n"
        f"📅 Неделя: *{week_earned:.0f} ₽*\n"
        f"📅 Месяц: *{month_earned:.0f} ₽*\n\n"
        f"─── По каналам ───\n{channels_breakdown}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
    )
    await callback.answer()
