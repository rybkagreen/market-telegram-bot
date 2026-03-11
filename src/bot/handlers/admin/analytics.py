"""
Admin Analytics Handlers — статистика платформы и здоровье рассылок.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import func, select

from src.bot.keyboards.admin.admin import AdminCB, get_mailing_health_kb
from src.bot.utils.safe_callback import safe_callback_edit
from src.db.models.campaign import CampaignStatus
from src.db.models.transaction import Transaction, TransactionType
from src.db.models.user import User
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.chat_analytics import ChatAnalyticsRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()


# ==================== СТАТИСТИКА ПЛАТФОРМЫ ====================


@router.callback_query(AdminCB.filter(F.action == "stats"))
async def handle_admin_stats(callback: CallbackQuery) -> None:
    """
    Показать статистику всей платформы.

    Args:
        callback: Callback query.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        campaign_repo = CampaignRepository(session)

        total_users = await user_repo.count()
        active_users = await user_repo.count(User.is_active == True)  # noqa: E712
        banned_users = await user_repo.count(User.is_banned == True)  # noqa: E712

        total_campaigns = await campaign_repo.count()
        running_campaigns = await campaign_repo.count(
            CampaignRepository.model.status == CampaignStatus.RUNNING
        )
        queued_campaigns = await campaign_repo.count(
            CampaignRepository.model.status == CampaignStatus.QUEUED
        )

        # Общая выручка (сумма всех пополнений)
        revenue_query = select(func.coalesce(func.sum(Transaction.amount), 0)).where(
            Transaction.type == TransactionType.TOPUP
        )
        revenue_result = await session.execute(revenue_query)
        total_revenue = revenue_result.scalar_one() or 0

    text = (
        "📊 <b>Статистика платформы</b>\n\n"
        f"👥 Пользователей всего: <b>{total_users}</b>\n"
        f"🟢 Активных: <b>{active_users}</b>\n"
        f"🚫 Забаненных: <b>{banned_users}</b>\n\n"
        f"📣 Кампаний всего: <b>{total_campaigns}</b>\n"
        f"🔄 Активных сейчас: <b>{running_campaigns}</b>\n"
        f"⏳ В очереди: <b>{queued_campaigns}</b>\n\n"
        f"💰 Выручка всего: <b>{total_revenue}₽</b>"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data=AdminCB(action="main"))
    builder.adjust(1)

    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
    await callback.answer()


# ==================== ДАШБОРД РАССЫЛОК ====================


@router.callback_query(AdminCB.filter(F.action == "mailing_health"))
async def show_mailing_health(callback: CallbackQuery) -> None:
    """
    Дашборд здоровья рассылок.

    Args:
        callback: Callback query.
    """
    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        chat_repo = ChatAnalyticsRepository(session)

        # Статистика кампаний по статусам
        running = await campaign_repo.count_by_status(CampaignStatus.RUNNING)
        paused = await campaign_repo.count_by_status(CampaignStatus.PAUSED)
        banned = await campaign_repo.count_by_status(CampaignStatus.ACCOUNT_BANNED)
        done_today = await campaign_repo.count_done_today()

        # Чёрный список каналов
        blacklisted = await chat_repo.count_blacklisted()

    text = (
        "📣 <b>Здоровье рассылок</b>\n\n"
        f"🔄 Активных кампаний:   <b>{running}</b>\n"
        f"⏸ На паузе:            <b>{paused}</b>\n"
        f"🚫 Забанено аккаунтов: <b>{banned}</b>\n"
        f"✅ Завершено сегодня:  <b>{done_today}</b>\n"
        f"⛔ Каналов в ЧС:       <b>{blacklisted}</b>"
    )

    await safe_callback_edit(callback, text, reply_markup=get_mailing_health_kb())
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action.in_({"paused_campaigns", "banned_campaigns"})))
async def show_problem_campaigns(
    callback: CallbackQuery,
    callback_data: AdminCB,
) -> None:
    """
    Список кампаний в статусе PAUSED или ACCOUNT_BANNED.

    Args:
        callback: Callback query.
        callback_data: Данные callback.
    """
    status = (
        CampaignStatus.PAUSED
        if callback_data.action == "paused_campaigns"
        else CampaignStatus.ACCOUNT_BANNED
    )
    label = "⏸ На паузе" if status == CampaignStatus.PAUSED else "🚫 Забанено"

    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        campaigns = await campaign_repo.get_by_status(status, limit=20)

    if not campaigns:
        await callback.answer(f"{label}: нет кампаний", show_alert=False)
        return

    lines = [f"{label} — последние {len(campaigns)}:\n"]
    for c in campaigns:
        lines.append(f"• #{c.id} {c.title[:30]} — user:{c.user_id}")

    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 К дашборду", callback_data=AdminCB(action="mailing_health"))
    builder.adjust(1)

    await safe_callback_edit(callback, "\n".join(lines), reply_markup=builder.as_markup())
    await callback.answer()
