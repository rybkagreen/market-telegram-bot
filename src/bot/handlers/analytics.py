"""
Handlers для аналитики и статистики.
Задача 6.1: Развилка по роли в main:analytics
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.main_menu import MainMenuCB
from src.bot.utils.message_utils import safe_edit_message
from src.core.services.analytics_service import analytics_service
from src.core.services.user_role_service import UserRoleService
from src.db.repositories.chat_analytics import ChatAnalyticsRepository
from src.db.session import async_session_factory
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()


def make_progress_bar(percent: float, length: int = 10) -> str:
    """
    Создать Unicode прогресс-бар.

    Args:
        percent: Процент выполнения (0-100).
        length: Длина бара в символах.

    Returns:
        Строка с прогресс-баром.
    """
    percent = max(0, min(100, percent))  # Ограничиваем 0-100
    filled = int(percent / 100 * length)
    return "█" * filled + "░" * (length - filled) + f" {percent:.0f}%"


@router.callback_query(MainMenuCB.filter(F.action == "analytics"))
async def show_analytics_menu(callback: CallbackQuery) -> None:
    """
    Показать меню аналитики.
    Задача 6.1: Развилка по роли.

    Args:
        callback: Callback query.
    """
    # Задача 6.1: Определяем роль пользователя
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        user_role_service = UserRoleService()
        user_context = await user_role_service.get_user_context(user.id)
        role = user_context.role

    # Задача 6.1: Развилка по роли
    if role in ("owner",):
        await show_owner_analytics(callback, user.id)
    elif role == "both":
        # Показать выбор: как рекламодатель или как владелец
        await show_analytics_role_choice(callback, user.id)
    else:
        # advertiser или new — показываем аналитику рекламодателя
        await show_advertiser_analytics(callback, user.id)


async def show_analytics_role_choice(callback: CallbackQuery, user_id: int) -> None:
    """
    Задача 6.1: Выбор роли для аналитики (для пользователей с обеими ролями).
    """
    text = (
        "📊 <b>Аналитика</b>\n\n"
        "Выберите раздел:\n\n"
        "📺 Как владелец канала\n"
        "📣 Как рекламодатель"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📺 Как владелец канала", callback_data="owner_analytics:role")
    builder.button(text="📣 Как рекламодатель", callback_data=MainMenuCB(action="advertiser_analytics"))
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1, 1)

    await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())


async def show_advertiser_analytics(callback: CallbackQuery, user_id: int) -> None:
    """
    Задача 6.1: Аналитика рекламодателя (существующее меню).
    """
    text = (
        "📊 <b>Аналитика рекламодателя</b>\n\n"
        "Выберите раздел:\n\n"
        "📈 Общая статистика — ваша сводка за 30 дней\n"
        "📋 Кампании — статистика по кампаниям\n"
        "🏆 Топ чатов — лучшие чаты по эффективности\n"
        "📊 Тематики кампаний — распределение по темам\n"
        "✨ AI-анализ — анализ кампании через ИИ"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📈 Общая статистика", callback_data=MainMenuCB(action="user_summary"))
    builder.button(text="📋 Кампании", callback_data=MainMenuCB(action="campaigns_stats"))
    builder.button(text="🏆 Топ чатов", callback_data=MainMenuCB(action="top_chats"))
    builder.button(text="📊 Тематики", callback_data=MainMenuCB(action="topics_distribution"))
    builder.button(text="✨ AI-анализ", callback_data=MainMenuCB(action="ai_campaign_analytics"))
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(2, 2, 1)

    await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())


async def show_owner_analytics(callback: CallbackQuery, user_id: int) -> None:
    """
    Задача 6.2: Аналитика владельца канала — список каналов.
    """
    async with async_session_factory() as session:
        from sqlalchemy import select

        from src.db.models.analytics import TelegramChat

        # Получаем каналы пользователя
        stmt = select(TelegramChat).where(
            TelegramChat.owner_user_id == user_id,
            TelegramChat.is_active ,
        )
        result = await session.execute(stmt)
        channels = list(result.scalars().all())

    if not channels:
        text = (
            "📺 <b>Аналитика владельца</b>\n\n"
            "У вас пока нет каналов.\n\n"
            "Добавьте первый канал для отслеживания статистики."
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="➕ Добавить канал", callback_data=MainMenuCB(action="add_channel"))
        builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
        builder.adjust(1)

        await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())
        return

    # Если канал один — сразу показываем статистику
    if len(channels) == 1:
        await show_owner_channel_analytics(callback, channels[0].id, "all")
        return

    # Если каналов несколько — показываем выбор
    text = "📺 <b>Статистика каналов</b>\n\nВыберите канал:\n\n"

    builder = InlineKeyboardBuilder()
    for channel in channels:
        channel_name = f"@{channel.username}" if channel.username else channel.title
        text += f"• {channel_name}\n"
        builder.button(
            text=f"📺 {channel_name}",
            callback_data=f"owner_analytics:channel:{channel.id}",
        )

    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1)

    await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())


@router.callback_query(F.data.startswith("owner_analytics:channel:"))
async def handle_owner_channel_analytics(callback: CallbackQuery) -> None:
    """
    Задача 6.3: Экран статистики одного канала владельца.
    """
    # Парсим callback: owner_analytics:channel:{channel_id}:period:{period}
    parts = (callback.data or "").split(":")
    channel_id = int(parts[2]) if len(parts) > 2 else 0
    period = parts[4] if len(parts) > 4 else "all"

    await show_owner_channel_analytics(callback, channel_id, period)


async def show_owner_channel_analytics(
    callback: CallbackQuery,
    channel_id: int,
    period: str = "all",
) -> None:
    """
    Задача 6.3: Показать статистику одного канала.

    Args:
        callback: Callback query.
        channel_id: ID канала.
        period: Период (7, 30, all).
    """
    async with async_session_factory() as session:
        from sqlalchemy import func, select

        from src.db.models.analytics import TelegramChat
        from src.db.models.mailing_log import MailingLog, MailingStatus

        # Получаем канал
        channel = await session.get(TelegramChat, channel_id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return

        # Задача 6.3: Блок ДОХОД — из mailing_log за период
        from datetime import datetime, timedelta

        if period == "7":
            days_label = "7 дней"
            start_date = datetime.now() - timedelta(days=7)
        elif period == "30":
            days_label = "30 дней"
            start_date = datetime.now() - timedelta(days=30)
        else:
            days_label = "Всё время"
            start_date = None

        # Подсчитываем размещения и заработок
        stmt = select(
            func.count(MailingLog.id),
            func.sum(MailingLog.cost),
        ).where(
            MailingLog.chat_id == channel_id,
            MailingLog.status == MailingStatus.SENT,
        )
        if start_date:
            stmt = stmt.where(MailingLog.sent_at >= start_date)

        result = await session.execute(stmt)
        row = result.one()
        placements_count = row[0] or 0
        earned_credits = float(row[1] or 0) * 0.8  # 80% владельцу

        # Задача 6.3: Блок КАНАЛ — из chat
        member_count = channel.member_count or 0

        # Задача 6.3: Блок РЕЙТИНГ — только если поля существуют
        rating = getattr(channel, 'rating', None)

        # Формируем текст
        text = f"📺 @{channel.username or channel.title}  •  {days_label}\n\n"

        text += "━━━━ ДОХОД ━━━━\n"
        text += f"Размещений: {placements_count}\n"
        text += f"Заработано: {earned_credits:.0f} кр\n"
        if placements_count > 0:
            avg_check = earned_credits / placements_count
            text += f"Средний чек: {avg_check:.0f} кр/пост\n"

        text += "\n━━━━ КАНАЛ ━━━━\n"
        text += f"Подписчиков: {member_count:,}\n"

        if rating:
            text += "\n━━━━ РЕЙТИНГ ━━━━\n"
            text += f"Надёжность: {rating:.1f}★\n"

        # Клавиатура с переключателями периода
        builder = InlineKeyboardBuilder()

        builder.button(
            text="→ 7 дней" if period == "7" else "7 дней",
            callback_data=f"owner_analytics:channel:{channel_id}:period:7",
        )
        builder.button(
            text="→ 30 дней" if period == "30" else "30 дней",
            callback_data=f"owner_analytics:channel:{channel_id}:period:30",
        )
        builder.button(
            text="→ Всё время" if period == "all" else "Всё время",
            callback_data=f"owner_analytics:channel:{channel_id}:period:all",
        )

        builder.button(
            text="💰 История выплат",
            callback_data=f"ch_payouts:{channel_id}",
        )
        builder.button(
            text="📋 Все размещения",
            callback_data=f"ch_requests:{channel_id}",
        )
        builder.button(text="🔙 Назад", callback_data="owner_analytics:role")

        builder.adjust(3, 2, 1)

        await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())


@router.callback_query(MainMenuCB.filter(F.action == "user_summary"))
async def handle_user_summary(callback: CallbackQuery) -> None:
    """
    Показать сводную аналитику пользователя за 30 дней.

    Args:
        callback: Callback query.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем аналитику
        user_analytics = await analytics_service.get_user_summary(user.id, days=30)

        if not user_analytics:
            await callback.answer("❌ Не удалось загрузить аналитику", show_alert=True)
            return

        # Получаем топ тематику из БД
        analytics_repo = ChatAnalyticsRepository(svc._session)
        top_topic = await analytics_repo.get_top_topic(user.id) or "Нет данных"

        # Форматируем успешность с прогресс-баром
        success_rate_bar = make_progress_bar(user_analytics.avg_success_rate)

        text = (
            f"📊 <b>Ваша аналитика за 30 дней</b>\n\n"
            f"📤 Всего кампаний: <b>{user_analytics.total_campaigns}</b>\n"
            f"🔄 Активных: <b>{user_analytics.active_campaigns}</b>\n"
            f"✅ Завершённых: <b>{user_analytics.completed_campaigns}</b>\n"
            f"💰 Потрачено: <b>{user_analytics.total_spent}₽</b>\n\n"
            f"📊 Успешность: {success_rate_bar}\n"
            f"👥 Чатов достигнуто: <b>{user_analytics.total_chats_reached}</b>\n\n"
            f"🏆 Топ тематика: <b>{top_topic}</b>"
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 В меню аналитики", callback_data=MainMenuCB(action="analytics"))
        builder.adjust(1)

        await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())


@router.callback_query(MainMenuCB.filter(F.action == "campaigns_stats"))
async def handle_campaigns_stats(callback: CallbackQuery) -> None:
    """
    Показать статистику по кампаниям.

    Args:
        callback: Callback query.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        campaigns, total = await svc.get_campaigns_page(
            telegram_id=callback.from_user.id,
            page=1,
            per_page=10,
        )

        if not campaigns:
            text = "📋 <b>У вас пока нет кампаний</b>\n\nСоздайте первую кампанию!"

            builder = InlineKeyboardBuilder()
            builder.button(
                text="🚀 Создать кампанию", callback_data=MainMenuCB(action="create_campaign")
            )
            builder.button(text="🔙 В меню аналитики", callback_data=MainMenuCB(action="analytics"))
            builder.adjust(2)

            await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())
            return

        # Формируем список кампаний с прогресс-барами
        text = f"📋 <b>Статистика кампаний</b> ({total} всего)\n\n"

        for campaign in campaigns:
            progress_bar = make_progress_bar(campaign.progress)
            success_rate = campaign.success_rate

            status_emoji = {
                "draft": "📝",
                "queued": "⏳",
                "running": "🔄",
                "done": "✅",
                "error": "❌",
                "paused": "⏸️",
                "cancelled": "🚫",
            }.get(campaign.status.value, "📝")

            text += (
                f"{status_emoji} <b>{campaign.title}</b>\n"
                f"   Прогресс: {progress_bar}\n"
                f"   Успешность: {success_rate:.1f}%\n"
                f"   Отправлено: {campaign.sent_count}/{campaign.total_chats}\n\n"
            )

        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 В меню аналитики", callback_data=MainMenuCB(action="analytics"))
        builder.adjust(1)

        await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())


@router.callback_query(MainMenuCB.filter(F.action == "campaign_stats"))
async def handle_single_campaign_stats(callback: CallbackQuery) -> None:
    """
    Показать детальную статистику одной кампании.

    Args:
        callback: Callback query.
    """
    # В production campaign_id передаётся через callback_data
    # Для now заглушка
    await callback.answer("🚧 Функция в разработке", show_alert=True)


@router.callback_query(MainMenuCB.filter(F.action == "top_chats"))
async def handle_top_chats(callback: CallbackQuery) -> None:
    """
    Показать топ-5 чатов по эффективности.

    Args:
        callback: Callback query.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Получаем топ чатов
        top_chats = await analytics_service.get_top_performing_chats(user.id, limit=5)

        if not top_chats:
            text = (
                "🏆 <b>Топ чатов</b>\n\n"
                "Пока нет данных о чатах.\n"
                "Запустите кампанию для сбора статистики."
            )

            builder = InlineKeyboardBuilder()
            builder.button(
                text="🚀 Создать кампанию", callback_data=MainMenuCB(action="create_campaign")
            )
            builder.button(text="🔙 В меню аналитики", callback_data=MainMenuCB(action="analytics"))
            builder.adjust(2)

            await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())
            return

        # Формируем список топ чатов
        text = "🏆 <b>Топ чатов по эффективности</b>\n\n"

        for i, chat in enumerate(top_chats, 1):
            # Прогресс-бар для success rate
            progress_bar = make_progress_bar(chat.success_rate, length=8)

            text += (
                f"<b>{i}. {chat.chat_title}</b>\n"
                f"   Успешность: {progress_bar}\n"
                f"   Отправлено: {chat.total_sent}\n"
                f"   Рейтинг: {chat.avg_rating:.1f}\n\n"
            )

        text += (
            "💡 <b>Совет:</b>\n"
            "Запускайте кампании в чатах с высоким рейтингом\n"
            "для лучшей конверсии."
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 В меню аналитики", callback_data=MainMenuCB(action="analytics"))
        builder.adjust(1)

        await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())


@router.callback_query(MainMenuCB.filter(F.action == "topics_distribution"))
async def handle_topics_distribution(callback: CallbackQuery) -> None:
    """
    Показать распределение кампаний по тематикам.

    Args:
        callback: Callback query.
    """
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_by_telegram_id(callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Проверяем тариф
        plan_str = user.plan.value if hasattr(user.plan, "value") else str(user.plan)
        if plan_str not in ("pro", "business"):
            text = (
                "📊 <b>Тематики кампаний</b>\n\n"
                "❌ Доступно только для тарифов PRO и BUSINESS\n\n"
                "Upgrade откроет:\n"
                "• Аналитику по тематикам\n"
                "• Топ чатов по эффективности\n"
                "• AI-аналитику кампаний"
            )

            builder = InlineKeyboardBuilder()
            builder.button(
                text="💳 Изменить тариф",
                callback_data=MainMenuCB(action="balance"),
            )
            builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
            builder.adjust(1)

            await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())
            return

        # Получаем тематики из БД
        from sqlalchemy import select

        from src.db.models.campaign import Campaign
        from src.db.session import async_session_factory

        async with async_session_factory() as session:
            result = await session.execute(
                select(Campaign.filters_json).where(
                    Campaign.user_id == user.id,
                    Campaign.status == "done",
                )
            )
            rows = result.scalars().all()

        # Подсчитываем тематики
        from collections import Counter

        topic_counter: Counter = Counter()

        for filters_json in rows:
            if not filters_json:
                continue
            topics = filters_json.get("topics", [])
            if isinstance(topics, list):
                for t in topics:
                    if t:
                        topic_counter[t] += 1

        if not topic_counter:
            text = (
                "📊 <b>Тематики кампаний</b>\n\n"
                "Пока нет данных.\n"
                "Запустите несколько кампаний с разными тематиками."
            )

            builder = InlineKeyboardBuilder()
            builder.button(text="🔙 В меню аналитики", callback_data=MainMenuCB(action="analytics"))
            builder.adjust(1)

            await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())
            return

        # Формируем текст с распределением
        total = sum(topic_counter.values())
        text = "📊 <b>Тематики ваших кампаний</b>\n\n"

        for topic, count in topic_counter.most_common(8):
            percentage = round(count / total * 100, 1)
            progress_bar = make_progress_bar(percentage, length=10)
            text += f"<b>{topic}</b>: {count} ({progress_bar})\n"

        text += f"\n💡 <b>Всего:</b> {total} кампаний"

        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 В меню аналитики", callback_data=MainMenuCB(action="analytics"))
        builder.adjust(1)

        await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())
