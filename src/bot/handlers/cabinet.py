"""
Handlers личного кабинета пользователя.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.billing import BillingCB, get_amount_kb, get_plans_kb
from src.bot.keyboards.main_menu import MainMenuCB, get_main_menu
from src.bot.keyboards.pagination import PaginationCB, get_pagination_kb
from src.core.services.analytics_service import analytics_service
from src.db.models.campaign import CampaignStatus
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()

# Эмодзи статусов кампании
STATUS_EMOJI = {
    CampaignStatus.DRAFT: "📝",
    CampaignStatus.QUEUED: "⏳",
    CampaignStatus.RUNNING: "🔄",
    CampaignStatus.DONE: "✅",
    CampaignStatus.ERROR: "❌",
    CampaignStatus.PAUSED: "⏸️",
    CampaignStatus.CANCELLED: "🚫",
}


async def show_cabinet(message: Message | CallbackQuery) -> None:
    """
    Показать личный кабинет пользователя.

    Args:
        message: Сообщение или callback query.
    """
    # Получаем telegram_id
    if isinstance(message, CallbackQuery):
        telegram_id = message.from_user.id
        answer_method = message.message.answer if message.message else message.answer
    else:
        telegram_id = message.from_user.id
        answer_method = message.answer

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(telegram_id)

        if not user:
            await answer_method("❌ Пользователь не найден. Нажмите /start")
            return

        # Получаем статистику кампаний
        stats = await user_repo.get_with_stats(user.id)

        # Форматируем дату регистрации
        created_at = user.created_at.strftime("%d.%m.%Y") if user.created_at else "—"

        # Формируем карточку кабинета
        text = (
            f"👤 <b>Ваш кабинет</b>\n\n"
            f"💳 Баланс: <b>{user.balance}₽</b>  |  📦 Тариф: <b>{user.plan.value}</b>\n"
            f"📊 Кампаний: <b>{stats['total_campaigns']}</b>  |  🔄 Активных: <b>{stats['active_campaigns']}</b>\n"
            f"📅 Дата регистрации: <b>{created_at}</b>\n\n"
            f"👤 <b>Профиль:</b>\n"
            f"Имя: {user.full_name}\n"
            f"Telegram: @{user.username or 'не указан'}\n"
        )

        # Кнопки действий
        builder = InlineKeyboardBuilder()
        builder.button(text="💳 Пополнить", callback_data=BillingCB(action="topup", value="0"))
        builder.button(text="📊 История транзакций", callback_data=BillingCB(action="history", value="0"))
        builder.button(text="👥 Рефералы", callback_data=BillingCB(action="referral", value="0"))
        builder.button(text="🔄 Сменить тариф", callback_data=BillingCB(action="plans", value="0"))
        builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
        builder.adjust(2, 2, 1)

        await answer_method(text, reply_markup=builder.as_markup())


@router.callback_query(MainMenuCB.filter(lambda cb: cb.action == "cabinet"))
async def cabinet_callback(callback: CallbackQuery) -> None:
    """
    Callback handler для открытия кабинета.

    Args:
        callback: Callback query.
    """
    await show_cabinet(callback)


@router.callback_query(BillingCB.filter(lambda cb: cb.action == "referral"))
async def referral_callback(callback: CallbackQuery) -> None:
    """
    Показать реферальную информацию.

    Args:
        callback: Callback query.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Считаем количество рефералов (заглушка - нужен отдельный метод в репозитории)
        referrer_count = 0  # TODO: реализовать user_repo.get_referrers_count(user.id)

        # Реферальная ссылка
        ref_link = f"https://t.me/{bot_username}?start=ref_{user.referral_code}" if bot_username else f"t.me/yourbot?start=ref_{user.referral_code}"

        text = (
            f"👥 <b>Реферальная программа</b>\n\n"
            f"Ваша ссылка:\n"
            f"<code>{ref_link}</code>\n\n"
            f"🎁 Бонус за каждого друга: <b>50₽</b>\n"
            f"👥 Приглашено пользователей: <b>{referrer_count}</b>\n\n"
            f"💡 <b>Как это работает:</b>\n"
            f"1. Отправьте ссылку другу\n"
            f"2. Друг нажимает /start и регистрируется\n"
            f"3. Вы получаете 50₽ на баланс\n\n"
            f"🏆 <b>Ваш реферальный код:</b>\n"
            f"<code>{user.referral_code}</code>"
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="🔗 Копировать ссылку", url=ref_link)
        builder.button(text="🔙 Назад", callback_data=MainMenuCB(action="cabinet"))
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(BillingCB.filter(lambda cb: cb.action == "plans"))
async def plans_callback(callback: CallbackQuery) -> None:
    """
    Показать тарифные планы.

    Args:
        callback: Callback query.
    """
    text = (
        "📦 <b>Тарифные планы</b>\n\n"
        "🆓 <b>FREE</b> — 0₽/мес\n"
        "  • 0 кампаний в месяц\n"
        "  • 0 чатов на кампанию\n\n"
        "🚀 <b>STARTER</b> — 299₽/мес\n"
        "  • 5 кампаний в месяц\n"
        "  • 50 чатов на кампанию\n\n"
        "💎 <b>PRO</b> — 999₽/мес\n"
        "  • 20 кампаний в месяц\n"
        "  • 200 чатов на кампанию\n\n"
        "🏢 <b>BUSINESS</b> — 2999₽/мес\n"
        "  • 100 кампаний в месяц\n"
        "  • 1000 чатов на кампанию\n\n"
        "Выберите тариф для перехода:"
    )

    await callback.message.edit_text(text, reply_markup=get_plans_kb())


@router.callback_query(MainMenuCB.filter(lambda cb: cb.action == "my_campaigns"))
async def my_campaigns_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Показать список кампаний пользователя.

    Args:
        callback: Callback query.
        state: FSM контекст.
    """
    await show_campaigns_list(callback, page=1)


async def show_campaigns_list(callback: CallbackQuery, page: int = 1) -> None:
    """
    Показать список кампаний с пагинацией.

    Args:
        callback: Callback query.
        page: Номер страницы.
    """
    page_size = 5

    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        campaign_repo = CampaignRepository(session)
        campaigns, total = await campaign_repo.get_by_user(
            user_id=user.id,
            page=page,
            page_size=page_size,
        )

        total_pages = max(1, (total + page_size - 1) // page_size)

        if not campaigns:
            text = "📋 <b>У вас пока нет кампаний</b>\n\nСоздайте первую кампанию через главное меню!"
            builder = InlineKeyboardBuilder()
            builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
            builder.adjust(1)
            await callback.message.edit_text(text, reply_markup=builder.as_markup())
            return

        # Формируем список кампаний
        text = f"📋 <b>Ваши кампании</b> ({total} всего)\n\n"

        for campaign in campaigns:
            emoji = STATUS_EMOJI.get(campaign.status, "📝")
            status_text = campaign.status.value
            progress = campaign.progress

            # Форматируем дату
            created = campaign.created_at.strftime("%d.%m.%Y") if campaign.created_at else "—"

            text += (
                f"{emoji} <b>{campaign.title}</b>\n"
                f"   Статус: {status_text}  |  Прогресс: {progress:.0f}%\n"
                f"   Создана: {created}\n"
                f"   Отправлено: {campaign.sent_count}/{campaign.total_chats}\n\n"
            )

        # Кнопки навигации
        builder = InlineKeyboardBuilder()

        if page > 1:
            builder.button(
                text="◀ Пред",
                callback_data=PaginationCB(prefix="campaigns", page=page - 1)
            )

        builder.button(
            text=f"{page}/{total_pages}",
            callback_data=PaginationCB(prefix="campaigns", page=page)
        )

        if page < total_pages:
            builder.button(
                text="След ▶",
                callback_data=PaginationCB(prefix="campaigns", page=page + 1)
            )

        builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
        builder.adjust(2, 1, 1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(PaginationCB.filter(lambda cb: cb.prefix == "campaigns"))
async def campaigns_pagination_callback(callback: CallbackQuery, callback_data: PaginationCB) -> None:
    """
    Callback handler для пагинации кампаний.

    Args:
        callback: Callback query.
        callback_data: Данные пагинации.
    """
    await show_campaigns_list(callback, page=callback_data.page)


# Глобальная переменная для bot_username (заполняется при старте)
bot_username: str = ""


def set_bot_username(username: str) -> None:
    """
    Установить username бота для генерации реферальных ссылок.

    Args:
        username: Username бота.
    """
    global bot_username
    bot_username = username
