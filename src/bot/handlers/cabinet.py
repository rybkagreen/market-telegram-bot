"""
Handlers личного кабинета пользователя.
"""

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.billing import BillingCB, get_plans_kb
from src.bot.keyboards.cabinet import CabinetCB, get_cabinet_kb
from src.bot.keyboards.main_menu import MainMenuCB
from src.bot.keyboards.pagination import PaginationCB
from src.bot.utils.message_utils import safe_edit_message
from src.db.models.campaign import CampaignStatus
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory
from src.services import get_user_service

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

    async with get_user_service() as svc:
        cabinet_data = await svc.get_cabinet_data(telegram_id)
        user = await svc._user_repo.get_by_telegram_id(telegram_id)

        if not user:
            await answer_method("❌ Пользователь не найден. Нажмите /start")
            return

        # Формируем карточку кабинета
        text = (
            f"👤 <b>Ваш кабинет</b>\n\n"
            f"💳 Баланс: <b>{user.credits:,} кр</b>  |  📦 Тариф: <b>{cabinet_data.plan}</b>\n"
            f"📊 Кампаний: <b>{cabinet_data.total_campaigns}</b>  |  🔄 Активных: <b>{cabinet_data.active_campaigns}</b>\n"
            f"📅 Дата регистрации: <b>{cabinet_data.created_at}</b>\n\n"
            f"👤 <b>Профиль:</b>\n"
            f"Имя: {user.full_name}\n"
            f"Telegram: @{user.username or 'не указан'}\n"
        )

        # Кнопки действий с переключателем уведомлений
        await answer_method(text, reply_markup=get_cabinet_kb(user.notifications_enabled))


@router.callback_query(MainMenuCB.filter(F.action == "cabinet"))
async def cabinet_callback(callback: CallbackQuery) -> None:
    """
    Callback handler для открытия кабинета.

    Args:
        callback: Callback query.
    """
    await show_cabinet(callback)


@router.callback_query(CabinetCB.filter(F.action == "toggle_notifications"))
async def toggle_notifications_handler(callback: CallbackQuery) -> None:
    """
    Переключить уведомления пользователя.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        new_state = await user_repo.toggle_notifications(callback.from_user.id)

    status_text = "включены 🔔" if new_state else "выключены 🔕"
    await callback.answer(f"Уведомления {status_text}", show_alert=False)

    # Обновить кнопку без перерисовки всего сообщения
    await callback.message.edit_reply_markup(
        reply_markup=get_cabinet_kb(notifications_enabled=new_state)
    )


@router.callback_query(BillingCB.filter(F.action == "referral"))
async def referral_callback(callback: CallbackQuery) -> None:
    """
    Показать реферальную информацию.

    Args:
        callback: Callback query.
    """
    async with get_user_service() as svc:
        user = await svc._user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем количество рефералов
        referrer_count = await svc._user_repo.get_referrers_count(user.id)

        # Получаем список рефералов для отображения
        referrers = await svc._user_repo.get_referrers(user.id, limit=5)
        referrers_text = ""
        if referrers:
            referrers_text = "\n\n" + "\n".join(
                [f"• {r.full_name or r.username or 'User'}" for r in referrers]
            )
            if referrer_count > 5:
                referrers_text += f"\n... и ещё {referrer_count - 5}"

        # Реферальная ссылка
        bot_info = await callback.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user.referral_code}"

        text = (
            f"👥 <b>Реферальная программа</b>\n\n"
            f"Ваша ссылка:\n"
            f"<code>{ref_link}</code>\n\n"
            f"🎁 Бонус за каждого друга: <b>50₽</b>\n"
            f"👥 Приглашено пользователей: <b>{referrer_count}</b>"
            f"{referrers_text}\n\n"
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

        await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())


@router.callback_query(BillingCB.filter(F.action == "plans"))
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

    await safe_edit_message(callback.message, text, reply_markup=get_plans_kb())


@router.callback_query(MainMenuCB.filter(F.action == "my_campaigns"))
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

    async with get_user_service() as svc:
        campaigns, total = await svc.get_campaigns_page(
            telegram_id=callback.from_user.id,
            page=page,
            per_page=page_size,
        )

        total_pages = max(1, (total + page_size - 1) // page_size)

        if not campaigns:
            text = (
                "📋 <b>У вас пока нет кампаний</b>\n\nСоздайте первую кампанию через главное меню!"
            )
            builder = InlineKeyboardBuilder()
            builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
            builder.adjust(1)
            # Используем edit_message_caption для совместимости с фото
            try:
                await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())
            except Exception:
                await callback.message.edit_message_caption(caption=text, reply_markup=builder.as_markup())
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
                text="◀ Пред", callback_data=PaginationCB(prefix="campaigns", page=page - 1)
            )

        builder.button(
            text=f"{page}/{total_pages}", callback_data=PaginationCB(prefix="campaigns", page=page)
        )

        if page < total_pages:
            builder.button(
                text="След ▶", callback_data=PaginationCB(prefix="campaigns", page=page + 1)
            )

        builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
        builder.adjust(2, 1, 1)

        await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())


@router.callback_query(PaginationCB.filter(F.prefix == "campaigns"))
async def campaigns_pagination_callback(
    callback: CallbackQuery, callback_data: PaginationCB
) -> None:
    """
    Callback handler для пагинации кампаний.

    Args:
        callback: Callback query.
        callback_data: Данные пагинации.
    """
    await show_campaigns_list(callback, page=callback_data.page)
