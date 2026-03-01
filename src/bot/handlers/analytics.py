"""
Handlers для аналитики и статистики.
"""

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.main_menu import MainMenuCB
from src.core.services.analytics_service import analytics_service
from src.db.repositories.chat_analytics import ChatAnalyticsRepository
from src.services import get_user_service

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

    Args:
        callback: Callback query.
    """
    text = (
        "📊 <b>Аналитика</b>\n\n"
        "Выберите раздел:\n\n"
        "📈 Общая статистика — ваша сводка за 30 дней\n"
        "📋 Кампании — статистика по кампаниям\n"
        "🏆 Топ чатов — лучшие чаты по эффективности"
    )

    builder = InlineKeyboardBuilder()
    builder.button(text="📈 Общая статистика", callback_data=MainMenuCB(action="user_summary"))
    builder.button(text="📋 Кампании", callback_data=MainMenuCB(action="campaigns_stats"))
    builder.button(text="🏆 Топ чатов", callback_data=MainMenuCB(action="top_chats"))
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(2, 2)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(MainMenuCB.filter(F.action == "user_summary"))
async def handle_user_summary(callback: CallbackQuery) -> None:
    """
    Показать сводную аналитику пользователя за 30 дней.

    Args:
        callback: Callback query.
    """
    async with get_user_service() as svc:
        user = await svc._user_repo.get_by_telegram_id(callback.from_user.id)

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

        text = (
            f"📊 <b>Ваша аналитика за 30 дней</b>\n\n"
            f"📤 Всего кампаний: <b>{user_analytics.total_campaigns}</b>\n"
            f"🔄 Активных: <b>{user_analytics.active_campaigns}</b>\n"
            f"✅ Завершённых: <b>{user_analytics.completed_campaigns}</b>\n"
            f"💰 Потрачено: <b>{user_analytics.total_spent}₽</b>\n\n"
            f"📊 Средняя успешность: <b>{user_analytics.avg_success_rate:.1f}%</b>\n"
            f"👥 Чатов достигнуто: <b>{user_analytics.total_chats_reached}</b>\n\n"
            f"🏆 Топ тематика: <b>{top_topic}</b>"
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(MainMenuCB.filter(F.action == "campaigns_stats"))
async def handle_campaigns_stats(callback: CallbackQuery) -> None:
    """
    Показать статистику по кампаниям.

    Args:
        callback: Callback query.
    """
    async with get_user_service() as svc:
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
            builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
            builder.adjust(2)

            await callback.message.edit_text(text, reply_markup=builder.as_markup())
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
        builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())


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
    async with get_user_service() as svc:
        user = await svc._user_repo.get_by_telegram_id(callback.from_user.id)

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
            builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
            builder.adjust(2)

            await callback.message.edit_text(text, reply_markup=builder.as_markup())
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
        builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
        builder.adjust(1)

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
