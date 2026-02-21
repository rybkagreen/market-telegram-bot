"""
Mailing Celery tasks для отправки кампаний.
"""

import asyncio
import logging
from typing import Any

from src.db.repositories.campaign_repo import CampaignRepository
from src.db.repositories.log_repo import MailingLogRepository
from src.db.session import async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask, name="mailing:send_campaign")
def send_campaign(self, campaign_id: int) -> dict[str, Any]:
    """
    Отправить рекламную кампанию.

    Args:
        campaign_id: ID кампании.

    Returns:
        Статистика рассылки.
    """
    logger.info(f"Starting campaign {campaign_id}")

    try:
        # Импортируем mailing_service здесь чтобы избежать circular imports
        from src.core.services.mailing_service import MailingService

        stats = asyncio.run(_run_campaign_async(campaign_id))

        logger.info(f"Campaign {campaign_id} completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Campaign {campaign_id} failed: {e}")
        raise self.retry(exc=e, countdown=60)


async def _run_campaign_async(campaign_id: int) -> dict[str, Any]:
    """
    Асинхронная функция для запуска кампании.

    Args:
        campaign_id: ID кампании.

    Returns:
        Статистика рассылки.
    """
    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)
        log_repo = MailingLogRepository(session)

        # Получаем кампанию
        campaign = await campaign_repo.get_by_id(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Запускаем рассылку через сервис
        from src.core.services.mailing_service import MailingService

        mailing_service = MailingService(campaign_repo, log_repo)
        stats = await mailing_service.run_campaign(campaign_id)

        return stats


@celery_app.task(bind=True, base=BaseTask, name="mailing:check_scheduled_campaigns")
def check_scheduled_campaigns(self) -> dict[str, Any]:
    """
    Проверить запланированные кампании и запустить готовые.

    Returns:
        Статистика проверенных кампаний.
    """
    logger.info("Checking scheduled campaigns")

    try:
        stats = asyncio.run(_check_scheduled_async())
        logger.info(f"Scheduled campaigns check completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error checking scheduled campaigns: {e}")
        return {"error": str(e)}


async def _check_scheduled_async() -> dict[str, Any]:
    """
    Асинхронная проверка запланированных кампаний.

    Returns:
        Статистика.
    """
    from datetime import datetime, timezone

    from src.db.models.campaign import CampaignStatus

    async with async_session_factory() as session:
        campaign_repo = CampaignRepository(session)

        # Получаем кампании, готовые к запуску
        now = datetime.now(tz=timezone.utc)
        campaigns = await campaign_repo.get_scheduled_due(now)

        stats = {
            "total_checked": len(campaigns),
            "launched": 0,
            "errors": 0,
        }

        for campaign in campaigns:
            try:
                # Обновляем статус на running
                await campaign_repo.update_status(
                    campaign.id, CampaignStatus.RUNNING
                )

                # Запускаем рассылку
                send_campaign.delay(campaign.id)
                stats["launched"] += 1

                logger.info(f"Launched scheduled campaign {campaign.id}")

            except Exception as e:
                logger.error(
                    f"Error launching scheduled campaign {campaign.id}: {e}"
                )
                stats["errors"] += 1

                # Обновляем статус на error
                await campaign_repo.update_status(
                    campaign.id, CampaignStatus.ERROR, str(e)
                )

        return stats
