"""
Cleanup tasks для очистки и архивации данных.
"""

import asyncio
import logging
from datetime import UTC
from typing import Any

from src.db.session import async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask, name="cleanup:delete_old_logs")
def delete_old_logs(self, days: int = 90) -> dict[str, Any]:
    """
    Удалить старые логи рассылок.

    Args:
        days: Удалять логи старше этого количества дней.

    Returns:
        Статистика удаления.
    """
    logger.info(f"Deleting logs older than {days} days")

    try:
        stats = asyncio.run(_delete_old_logs_async(days))
        logger.info(f"Cleanup completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error deleting old logs: {e}")
        return {"error": str(e)}


async def _delete_old_logs_async(days: int = 90) -> dict[str, Any]:
    """
    Асинхронное удаление старых логов.

    Args:
        days: Количество дней.

    Returns:
        Статистика.
    """
    from datetime import datetime, timedelta

    from sqlalchemy import delete

    from src.db.models.mailing_log import MailingLog

    async with async_session_factory() as session:
        cutoff_date = datetime.now(tz=UTC) - timedelta(days=days)

        stmt = delete(MailingLog).where(MailingLog.created_at < cutoff_date)
        result = await session.execute(stmt)
        await session.commit()

        deleted_count = result.rowcount or 0

        return {
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }


@celery_app.task(bind=True, base=BaseTask, name="cleanup:archive_old_campaigns")
def archive_old_campaigns(self, months: int = 12) -> dict[str, Any]:
    """
    Архивировать старые кампании.

    Args:
        months: Архивировать кампании старше этого количества месяцев.

    Returns:
        Статистика архивации.
    """
    logger.info(f"Archiving campaigns older than {months} months")

    try:
        stats = asyncio.run(_archive_old_campaigns_async(months))
        logger.info(f"Archive completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error archiving old campaigns: {e}")
        return {"error": str(e)}


async def _archive_old_campaigns_async(months: int = 12) -> dict[str, Any]:
    """
    Асинхронная архивация старых кампаний.

    Args:
        months: Количество месяцев.

    Returns:
        Статистика.
    """
    from datetime import datetime, timedelta

    from sqlalchemy import update

    from src.db.models.campaign import Campaign, CampaignStatus

    async with async_session_factory() as session:
        cutoff_date = datetime.now(tz=UTC) - timedelta(days=months * 30)

        # Находим завершенные кампании старше cutoff_date
        stmt = (
            update(Campaign)
            .where(
                Campaign.completed_at < cutoff_date,
                Campaign.status.in_(
                    [CampaignStatus.DONE, CampaignStatus.ERROR, CampaignStatus.CANCELLED]
                ),
            )
            .values(status=CampaignStatus.DONE)  # Можно добавить статус "archived"
        )
        result = await session.execute(stmt)
        await session.commit()

        archived_count = result.rowcount or 0

        return {
            "archived_count": archived_count,
            "cutoff_date": cutoff_date.isoformat(),
        }


@celery_app.task(bind=True, base=BaseTask, name="cleanup:cleanup_expired_sessions")
def cleanup_expired_sessions(self) -> dict[str, Any]:
    """
    Очистить истекшие сессии пользователей.

    Returns:
        Статистика очистки.
    """
    logger.info("Cleaning up expired sessions")

    try:
        stats = asyncio.run(_cleanup_expired_sessions_async())
        logger.info(f"Session cleanup completed: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")
        return {"error": str(e)}


async def _cleanup_expired_sessions_async() -> dict[str, Any]:
    """
    Асинхронная очистка истекших сессий.

    Returns:
        Статистика.
    """
    from datetime import datetime

    # Здесь можно добавить модель UserSession если нужна
    # Пока заглушка для будущей реализации

    return {
        "deleted_count": 0,
        "cleaned_at": datetime.now(tz=UTC).isoformat(),
    }
