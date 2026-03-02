"""
Mailing Celery tasks.

Использует asyncio.run() для запуска async кода в синхронных Celery задачах.
asyncio.run() создаёт новый event loop для каждого вызова и закрывает его,
что гарантирует корректную работу в Celery worker контексте без конфликтов.
"""

import asyncio
import logging
from datetime import UTC
from decimal import Decimal
from typing import Any

from src.config.settings import settings
from src.db.models.notification import NotificationType
from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.notification_repo import NotificationRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask, name="mailing:send_campaign")
def send_campaign(self, campaign_id: int) -> dict[str, Any]:
    """
    Отправить кампанию по чатам.

    Args:
        campaign_id: ID кампании.

    Returns:
        Статистика отправки.
    """
    logger.info(f"Starting campaign {campaign_id}")

    async def _send_async() -> dict[str, Any]:
        from aiogram import Bot

        from src.db.models.campaign import CampaignStatus
        from src.utils.telegram.sender import CampaignSender

        async with async_session_factory() as session:
            campaign_repo = CampaignRepository(session)
            bot = Bot(token=settings.bot_token)
            sender = CampaignSender(bot=bot)

            # Получаем кампанию
            campaign = await campaign_repo.get_by_id(campaign_id)

            if not campaign:
                logger.error(f"Campaign {campaign_id} not found")
                return {"error": "Campaign not found"}

            if campaign.status not in [CampaignStatus.RUNNING, CampaignStatus.QUEUED]:
                logger.warning(f"Campaign {campaign_id} is not in running/queued state")
                return {"skipped": "Campaign not in running/queued state"}

            # Получаем чаты для рассылки
            chats = await sender.get_chats_for_campaign(campaign)

            if not chats:
                logger.warning(f"No chats found for campaign {campaign_id}")
                return {"no_chats": True}

            stats = {
                "total": len(chats),
                "sent": 0,
                "failed": 0,
                "skipped": 0,
            }

            for chat in chats:
                try:
                    # Отправляем сообщение
                    success = await sender.send_to_chat(
                        chat=chat,
                        text=campaign.text,
                        image_file_id=campaign.image_file_id,
                    )

                    if success:
                        stats["sent"] += 1
                    else:
                        stats["failed"] += 1

                except Exception as e:
                    logger.error(f"Error sending to chat {chat.telegram_id}: {e}")
                    stats["failed"] += 1

            # Обновляем статистику кампании
            await campaign_repo.update_statistics(
                campaign_id=campaign.id,
                sent_count=stats["sent"],
                failed_count=stats["failed"],
                total_chats=stats["total"],
            )

            # Завершаем кампанию
            await campaign_repo.update_status(campaign.id, CampaignStatus.DONE)

            logger.info(
                f"Campaign {campaign_id} completed: "
                f"sent={stats['sent']}, failed={stats['failed']}, total={stats['total']}"
            )

            return stats

    try:
        # asyncio.run() создаёт новый event loop и закрывает его после выполнения
        # Это правильный способ запуска async кода в синхронном контексте
        return asyncio.run(_send_async())

    except Exception as e:
        logger.error(f"Error in send_campaign: {e}")
        return {"error": str(e)}


@celery_app.task(bind=True, base=BaseTask, name="mailing:check_scheduled_campaigns")
def check_scheduled_campaigns(self) -> dict[str, Any]:
    """
    Проверить и запустить запланированные кампании.

    Returns:
        Статистика.
    """
    logger.info("Checking scheduled campaigns")

    async def _check_async() -> dict[str, Any]:
        from datetime import datetime

        from src.db.models.campaign import CampaignStatus

        async with async_session_factory() as session:
            campaign_repo = CampaignRepository(session)

            # Получаем кампании, готовые к запуску
            now = datetime.now(UTC)
            campaigns = await campaign_repo.get_scheduled_due(now)

            stats = {
                "total_checked": len(campaigns),
                "launched": 0,
                "errors": 0,
            }

            for campaign in campaigns:
                try:
                    # Обновляем статус на running
                    await campaign_repo.update_status(campaign.id, CampaignStatus.RUNNING)

                    # Запускаем рассылку
                    send_campaign.delay(campaign.id)
                    stats["launched"] += 1

                    logger.info(f"Launched scheduled campaign {campaign.id}")

                except Exception as e:
                    logger.error(f"Error launching scheduled campaign {campaign.id}: {e}")
                    stats["errors"] += 1

                    # Обновляем статус на error
                    await campaign_repo.update_status(campaign.id, CampaignStatus.ERROR, str(e))

            return stats

    try:
        # Используем asyncio.run() с обработкой ситуации когда event loop уже существует
        # Это происходит в Celery worker при использовании prefork pool
        try:
            loop = asyncio.get_running_loop()
            # Loop уже существует — создаём новый и запускаем в нём
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, _check_async())
                result = future.result(timeout=300)
        except RuntimeError:
            # Нет активного loop — используем обычный asyncio.run()
            result = asyncio.run(_check_async())
        
        logger.info(f"Scheduled campaigns check completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Error checking scheduled campaigns: {e}")
        return {"error": str(e)}


@celery_app.task(bind=True, base=BaseTask, name="mailing:check_low_balance")
def check_low_balance(self, threshold: float = 50.0) -> dict[str, Any]:
    """
    Проверить баланс пользователей и отправить уведомления.

    Args:
        threshold: Порог низкого баланса.

    Returns:
        Статистика.
    """
    logger.info(f"Checking low balance (threshold: {threshold})")

    async def _check_balance_async() -> dict[str, Any]:
        async with async_session_factory() as session:
            user_repo = UserRepository(session)

            # Получаем пользователей с низким балансом
            users = await user_repo.get_users_with_low_balance(Decimal(str(threshold)))

            stats = {
                "total_checked": len(users),
                "notified": 0,
                "errors": 0,
            }

            # NOTE: Уведомления создаются через бота, не через БД
            for user in users:
                try:
                    # Отправляем уведомление через бота
                    notify_user.delay(
                        user.id,
                        f"⚠️ Низкий баланс!\n\nВаш баланс меньше {threshold}₽.\nПополните баланс для продолжения работы.",
                    )
                    stats["notified"] += 1
                    logger.info(f"Low balance notification sent to user {user.id}")

                except Exception as e:
                    logger.error(f"Error notifying user {user.id}: {e}")
                    stats["errors"] += 1

            return stats

    try:
        # asyncio.run() создаёт новый event loop и закрывает его после выполнения
        result = asyncio.run(_check_balance_async())
        logger.info(f"Low balance check completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Error checking low balance: {e}")
        return {"error": str(e)}


@celery_app.task(bind=True, base=BaseTask, name="mailing:notify_user")
def notify_user(
    self,
    user_id: int,
    message: str,
    notification_type: str = "system",
    title: str | None = None,
    campaign_id: int | None = None,
) -> bool:
    """
    Отправить уведомление пользователю.

    Args:
        user_id: ID пользователя в БД.
        message: Текст сообщения.
        notification_type: Тип уведомления (campaign_started, campaign_done, и т.д.).
        title: Заголовок уведомления (опционально).
        campaign_id: ID кампании (опционально).

    Returns:
        True если успешно.
    """
    logger.info(f"Sending notification to user {user_id}")

    async def _notify_async() -> bool:
        from telegram import Bot

        async with async_session_factory() as session:
            user_repo = UserRepository(session)
            notification_repo = NotificationRepository(session)

            user = await user_repo.get_by_id(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return False

            bot = Bot(token=self.app.conf.broker_url.split("://")[1].split("/")[0])

            try:
                # Отправляем уведомление через Telegram
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message,
                )

                # Логируем уведомление в БД
                await notification_repo.create_notification(
                    user_id=user_id,
                    message=message,
                    notification_type=NotificationType(notification_type),
                    title=title,
                    campaign_id=campaign_id,
                )

                logger.info(f"Notification sent to user {user_id}")
                return True

            except Exception as e:
                logger.error(f"Error sending notification to user {user_id}: {e}")
                return False

            finally:
                await bot.session.close()

    try:
        # asyncio.run() создаёт новый event loop и закрывает его после выполнения
        return asyncio.run(_notify_async())

    except Exception as e:
        logger.error(f"Error notifying user: {e}")
        return False
