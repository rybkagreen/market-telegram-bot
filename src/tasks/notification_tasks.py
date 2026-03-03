"""
Notification tasks для уведомлений пользователей.
"""

import asyncio
import logging
from decimal import Decimal
from typing import Any

from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask, name="mailing:check_low_balance")
def check_low_balance(self) -> dict[str, Any]:
    """
    Проверить баланс пользователей и отправить уведомления о низком балансе.

    Returns:
        Статистика проверенных пользователей.
    """
    logger.info("Checking low balance users")

    try:
        stats = asyncio.run(_check_low_balance_async())
        logger.info(f"Low balance check completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error checking low balance: {e}")
        return {"error": str(e)}


async def _check_low_balance_async() -> dict[str, Any]:
    """
    Асинхронная проверка низкого баланса.

    Returns:
        Статистика.
    """

    async with async_session_factory() as session:
        user_repo = UserRepository(session)

        # Получаем пользователей с балансом < 50 RUB
        users = await user_repo.get_users_for_notification(
            min_balance=Decimal("0.00"),
            max_balance=Decimal("50.00"),
        )

        stats = {
            "total_checked": len(users),
            "notified": 0,
            "errors": 0,
        }

        for user in users:
            try:
                # Проверяем настройку уведомлений
                if not user.notifications_enabled:
                    logger.debug(f"Notifications disabled for user {user.telegram_id}, skipping")
                    continue

                # Отправляем уведомление
                await _notify_low_balance(user.telegram_id, user.credits)
                stats["notified"] += 1

            except Exception as e:
                logger.error(f"Error notifying user {user.telegram_id}: {e}")
                stats["errors"] += 1

        return stats


async def _notify_low_balance(telegram_id: int, credits: int) -> None:
    """
    Отправить уведомление о низком балансе.

    Args:
        telegram_id: Telegram ID пользователя.
        credits: Текущий баланс в кредитах.
    """
    # Импортируем aiogram Bot
    from aiogram import Bot

    from src.config.settings import settings

    bot = Bot(token=settings.bot_token)

    message = (
        f"⚠️ <b>Низкий баланс</b>\n\n"
        f"Ваш баланс: {credits} кр\n"
        f"Пополните баланс для продолжения использования бота.\n\n"
        f"Используйте команду /billing для пополнения."
    )

    try:
        await bot.send_message(telegram_id, message, parse_mode="HTML")
    finally:
        await bot.session.close()


@celery_app.task(name="notifications:notify_campaign_status", bind=True, max_retries=3)
def notify_campaign_status(
    self,
    user_id: int,
    campaign_id: int,
    status: str,
    error_message: str = "",
) -> None:
    """
    Уведомить пользователя об изменении статуса кампании.

    Args:
        user_id: Telegram ID пользователя.
        campaign_id: ID кампании.
        status: Статус кампании (paused, banned, completed, error).
        error_message: Сообщение об ошибке (опционально).
    """
    async def _send():
        # НОВОЕ: проверяем настройку перед отправкой
        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            user = await user_repo.get_by_telegram_id(user_id)

            if not user or not user.notifications_enabled:
                logger.debug(f"Notifications disabled for user {user_id}, skipping")
                return

        text = _get_campaign_message(campaign_id, status, error_message)
        try:
            asyncio.run(_notify_user_async(user_id, text, "HTML"))
        except Exception as exc:
            logger.warning(f"Failed to notify user {user_id} about campaign {campaign_id}: {exc}")
            raise self.retry(countdown=60, exc=exc) from exc

    asyncio.run(_send())


def _get_campaign_message(campaign_id: int, status: str, error_message: str = "") -> str:
    """Получить текст уведомления о кампании."""
    messages = {
        "paused": (
            f"⏸ <b>Кампания #{campaign_id} приостановлена</b>\n\n"
            f"Telegram ограничил отправку. Кампания продолжится автоматически."
        ),
        "banned": (
            f"🚫 <b>Кампания #{campaign_id} остановлена</b>\n\n"
            f"Telegram-аккаунт рассылки заблокирован. Обратитесь в поддержку."
        ),
        "completed": f"✅ <b>Кампания #{campaign_id} завершена!</b>",
        "error": (
            f"❌ <b>Ошибка в кампании #{campaign_id}</b>\n\n"
            f"{error_message}"
        ),
    }
    return messages.get(status, f"Статус кампании #{campaign_id}: {status}")


@celery_app.task(bind=True, base=BaseTask, name="mailing:notify_user")
def notify_user(
    self,
    telegram_id: int,
    message: str,
    parse_mode: str = "HTML",
) -> bool:
    """
    Отправить уведомление пользователю.

    Args:
        telegram_id: Telegram ID пользователя.
        message: Текст сообщения.
        parse_mode: Режим парсинга (HTML/Markdown).

    Returns:
        True если отправлено успешно.
    """
    try:
        asyncio.run(_notify_user_async(telegram_id, message, parse_mode))
        return True
    except Exception as e:
        logger.error(f"Error notifying user {telegram_id}: {e}")
        return False


async def _notify_user_async(
    telegram_id: int,
    message: str,
    parse_mode: str = "HTML",
) -> None:
    """
    Асинхронная отправка уведомления.

    Args:
        telegram_id: Telegram ID пользователя.
        message: Текст сообщения.
        parse_mode: Режим парсинга.
    """
    from aiogram import Bot

    from src.config.settings import settings

    bot = Bot(token=settings.bot_token)

    try:
        await bot.send_message(telegram_id, message, parse_mode=parse_mode)
    finally:
        await bot.session.close()
