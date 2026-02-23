"""
Handlers и утилиты для уведомлений пользователей.

Этот модуль содержит:
- Форматировщики уведомлений (вызываются из Celery tasks)
- Handler скачивания PDF-отчёта
"""

import logging
from io import BytesIO

from aiogram import Router
from aiogram.types import BufferedInputFile, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.keyboards.main_menu import MainMenuCB
from src.core.services.analytics_service import analytics_service
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory

logger = logging.getLogger(__name__)

router = Router()


# ==================== ФОРМАТЧИКИ УВЕДОМЛЕНИЙ ====================
# Вызываются из Celery tasks через bot.send_message


def format_campaign_started(title: str, chat_count: int, estimate_min: int) -> str:
    """
    Сформировать уведомление о запуске кампании.

    Args:
        title: Название кампании.
        chat_count: Количество целевых чатов.
        estimate_min: Ожидаемое время выполнения в минутах.

    Returns:
        Отформатированное сообщение в HTML.
    """
    return (
        f"🚀 <b>Кампания запущена!</b>\n\n"
        f"📋 {title}\n"
        f"👥 Целевых чатов: <b>{chat_count}</b>\n"
        f"⏱ Ожидаемое время: ~<b>{estimate_min} мин</b>\n\n"
        f"Вы получите уведомление о завершении."
    )


def format_campaign_done(sent: int, total: int, rate: float) -> str:
    """
    Сформировать уведомление о завершении кампании.

    Args:
        sent: Количество отправленных сообщений.
        total: Общее количество чатов.
        rate: Процент успешности.

    Returns:
        Отформатированное сообщение в HTML.
    """
    return (
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: <b>{sent}</b> из <b>{total}</b>\n"
        f"📊 Успешность: <b>{rate:.1f}%</b>\n\n"
        f"📄 Вы можете скачать подробный отчёт в формате PDF."
    )


def format_campaign_error(error_msg: str) -> str:
    """
    Сформировать уведомление об ошибке кампании.

    Args:
        error_msg: Сообщение об ошибке.

    Returns:
        Отформатированное сообщение в HTML.
    """
    return (
        f"❌ <b>Ошибка рассылки</b>\n\n"
        f"Причина: {error_msg}\n\n"
        f"Проверьте настройки кампании или обратитесь в поддержку."
    )


def format_low_balance(balance: float, threshold: float = 50.0) -> str:
    """
    Сформировать уведомление о низком балансе.

    Args:
        balance: Текущий баланс пользователя.
        threshold: Порог уведомления.

    Returns:
        Отформатированное сообщение в HTML.
    """
    return (
        f"⚠️ <b>Низкий баланс!</b>\n\n"
        f"Ваш баланс: <b>{balance}₽</b>\n"
        f"Рекомендуемый минимум: <b>{threshold}₽</b>\n\n"
        f"Пополните баланс, чтобы продолжить запуск кампаний."
    )


def format_referral_bonus(bonus_amount: float, referred_user_id: int) -> str:
    """
    Сформировать уведомление о реферальном бонусе.

    Args:
        bonus_amount: Сумма бонуса.
        referred_user_id: ID приглашённого пользователя.

    Returns:
        Отформатированное сообщение в HTML.
    """
    return (
        f"🎁 <b>Реферальный бонус!</b>\n\n"
        f"Ваш друг присоединился к Market Bot!\n"
        f"💰 Вам начислено: <b>{bonus_amount}₽</b>\n\n"
        f"Продолжайте приглашать друзей и получайте бонусы!"
    )


# ==================== СКАЧИВАНИЕ PDF ОТЧЁТА ====================


@router.callback_query(MainMenuCB.filter(lambda cb: cb.action == "download_report"))
async def handle_report_request(callback: CallbackQuery) -> None:
    """
    Обработать запрос на скачивание PDF-отчёта кампании.

    Args:
        callback: Callback query.
    """
    # Извлекаем campaign_id из callback_data
    # В production нужно передавать campaign_id через callback_data
    await callback.answer("🚧 Функция в разработке", show_alert=True)


async def send_campaign_report(
    user_id: int,
    campaign_id: int,
    bot,
) -> None:
    """
    Отправить PDF-отчёт кампании пользователю.

    Args:
        user_id: ID пользователя.
        campaign_id: ID кампании.
        bot: Экземпляр бота для отправки.
    """
    try:
        # Генерируем PDF через analytics_service
        # В production analytics_service.generate_campaign_report должен возвращать bytes
        pdf_bytes = await analytics_service.generate_campaign_report(campaign_id)

        if not pdf_bytes:
            logger.error(f"Failed to generate PDF report for campaign {campaign_id}")
            return

        # Создаём BufferedInputFile
        pdf_file = BufferedInputFile(
            pdf_bytes,
            filename=f"report_campaign_{campaign_id}.pdf",
        )

        # Отправляем пользователю
        await bot.send_document(
            chat_id=user_id,
            document=pdf_file,
            caption=(
                f"📊 <b>Отчёт по кампании #{campaign_id}</b>\n\n"
                f"Файл сгенерирован автоматически."
            ),
        )

        logger.info(f"Sent PDF report for campaign {campaign_id} to user {user_id}")

    except Exception as e:
        logger.error(f"Error sending PDF report: {e}")


# ==================== УВЕДОМЛЕНИЯ ИЗ CELERY ====================


async def notify_user(
    bot,
    user_id: int,
    text: str,
    reply_markup=None,
) -> bool:
    """
    Отправить уведомление пользователю.

    Args:
        bot: Экземпляр бота.
        user_id: Telegram ID пользователя.
        text: Текст сообщения.
        reply_markup: Клавиатура (опционально).

    Returns:
        True если уведомление отправлено успешно.
    """
    try:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")
        return False


async def notify_campaign_started(
    bot,
    user_id: int,
    campaign_id: int,
    title: str,
    chat_count: int,
    estimate_min: int,
) -> bool:
    """
    Уведомить о запуске кампании.

    Args:
        bot: Экземпляр бота.
        user_id: Telegram ID пользователя.
        campaign_id: ID кампании.
        title: Название кампании.
        chat_count: Количество чатов.
        estimate_min: Ожидаемое время.

    Returns:
        True если уведомление отправлено успешно.
    """
    text = format_campaign_started(title, chat_count, estimate_min)

    builder = InlineKeyboardBuilder()
    builder.button(
        text="📊 Статистика",
        callback_data=f"campaign_stats:{campaign_id}"
    )
    builder.button(
        text="🔙 В меню",
        callback_data=MainMenuCB(action="main_menu")
    )
    builder.adjust(2)

    return await notify_user(bot, user_id, text, builder.as_markup())


async def notify_campaign_done(
    bot,
    user_id: int,
    campaign_id: int,
    sent: int,
    total: int,
    rate: float,
) -> bool:
    """
    Уведомить о завершении кампании.

    Args:
        bot: Экземпляр бота.
        user_id: Telegram ID пользователя.
        campaign_id: ID кампании.
        sent: Количество отправленных.
        total: Общее количество.
        rate: Процент успешности.

    Returns:
        True если уведомление отправлено успешно.
    """
    text = format_campaign_done(sent, total, rate)

    builder = InlineKeyboardBuilder()
    builder.button(
        text="📄 Скачать PDF",
        callback_data=f"download_report:{campaign_id}"
    )
    builder.button(
        text="📊 Статистика",
        callback_data=f"campaign_stats:{campaign_id}"
    )
    builder.button(
        text="🔙 В меню",
        callback_data=MainMenuCB(action="main_menu")
    )
    builder.adjust(2, 1)

    return await notify_user(bot, user_id, text, builder.as_markup())


async def notify_campaign_error(
    bot,
    user_id: int,
    campaign_id: int,
    error_msg: str,
) -> bool:
    """
    Уведомить об ошибке кампании.

    Args:
        bot: Экземпляр бота.
        user_id: Telegram ID пользователя.
        campaign_id: ID кампании.
        error_msg: Сообщение об ошибке.

    Returns:
        True если уведомление отправлено успешно.
    """
    text = format_campaign_error(error_msg)

    builder = InlineKeyboardBuilder()
    builder.button(
        text="🔙 В меню",
        callback_data=MainMenuCB(action="main_menu")
    )
    builder.adjust(1)

    return await notify_user(bot, user_id, text, builder.as_markup())


async def notify_low_balance(
    bot,
    user_id: int,
    balance: float,
    threshold: float = 50.0,
) -> bool:
    """
    Уведомить о низком балансе.

    Args:
        bot: Экземпляр бота.
        user_id: Telegram ID пользователя.
        balance: Текущий баланс.
        threshold: Порог уведомления.

    Returns:
        True если уведомление отправлено успешно.
    """
    text = format_low_balance(balance, threshold)

    builder = InlineKeyboardBuilder()
    builder.button(
        text="💳 Пополнить",
        callback_data="billing:topup:0"
    )
    builder.button(
        text="🔙 В меню",
        callback_data=MainMenuCB(action="main_menu")
    )
    builder.adjust(2)

    return await notify_user(bot, user_id, text, builder.as_markup())


async def notify_referral_bonus(
    bot,
    user_id: int,
    bonus_amount: float,
    referred_user_id: int,
) -> bool:
    """
    Уведомить о реферальном бонусе.

    Args:
        bot: Экземпляр бота.
        user_id: Telegram ID пользователя.
        bonus_amount: Сумма бонуса.
        referred_user_id: ID приглашённого.

    Returns:
        True если уведомление отправлено успешно.
    """
    text = format_referral_bonus(bonus_amount, referred_user_id)

    builder = InlineKeyboardBuilder()
    builder.button(
        text="👥 Рефералы",
        callback_data="billing:referral:0"
    )
    builder.button(
        text="🔙 В меню",
        callback_data=MainMenuCB(action="main_menu")
    )
    builder.adjust(2)

    return await notify_user(bot, user_id, text, builder.as_markup())
