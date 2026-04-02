"""
Cleanup tasks для очистки и архивации данных.
"""

import asyncio
import logging
from datetime import UTC
from typing import Any

from src.db.session import celery_async_session_factory as async_session_factory
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
    Очистить старые записи из БД по новым моделям.

    Args:
        days: Базовый порог в днях (PlacementRequest и Transaction).

    Returns:
        Статистика удалённых записей.
    """
    from datetime import datetime, timedelta

    from sqlalchemy import delete

    from src.db.models.placement_request import PlacementRequest, PlacementStatus
    from src.db.models.reputation_history import ReputationHistory
    from src.db.models.yookassa_payment import YookassaPayment

    now = datetime.now(tz=UTC)
    cutoff_placements = now - timedelta(days=days)
    cutoff_reputation = now - timedelta(days=180)
    cutoff_payments = now - timedelta(days=30)

    async with async_session_factory() as session:
        # Удалить старые завершённые/отменённые заявки
        r1 = await session.execute(
            delete(PlacementRequest).where(
                PlacementRequest.status.in_([
                    PlacementStatus.cancelled,
                    PlacementStatus.refunded,
                    PlacementStatus.failed,
                    PlacementStatus.failed_permissions,
                ]),
                PlacementRequest.created_at < cutoff_placements,
            )
        )

        # Удалить старую историю репутации
        r2 = await session.execute(
            delete(ReputationHistory).where(
                ReputationHistory.created_at < cutoff_reputation,
            )
        )

        # Удалить отменённые платежи ЮKassa
        r3 = await session.execute(
            delete(YookassaPayment).where(
                YookassaPayment.status == "cancelled",
                YookassaPayment.created_at < cutoff_payments,
            )
        )

        await session.commit()

    return {
        "placements_deleted": r1.rowcount,  # type: ignore[attr-defined]
        "reputation_history_deleted": r2.rowcount,  # type: ignore[attr-defined]
        "payments_deleted": r3.rowcount,  # type: ignore[attr-defined]
        "cutoff_date": cutoff_placements.isoformat(),
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

    from src.db.models.placement_request import PlacementRequest, PlacementStatus

    async with async_session_factory() as session:
        cutoff_date = datetime.now(tz=UTC) - timedelta(days=months * 30)

        # Archive old cancelled/failed placements
        stmt = (
            update(PlacementRequest)
            .where(
                PlacementRequest.created_at < cutoff_date,
                PlacementRequest.status.in_(
                    [PlacementStatus.failed, PlacementStatus.cancelled, PlacementStatus.refunded]
                ),
            )
            .values(status=PlacementStatus.failed)
        )
        result = await session.execute(stmt)
        await session.commit()

        archived_count = result.rowcount  # type: ignore

        return {
            "archived_count": archived_count,
            "cutoff_date": cutoff_date.isoformat(),
        }


@celery_app.task(bind=True, base=BaseTask, name="cleanup:cleanup_useless_channels")
def cleanup_useless_channels(self) -> dict[str, Any]:
    """
    Удалить бесполезные каналы (без названия, тестовые).

    Returns:
        Статистика: удалено, пропущено.
    """
    return asyncio.run(_cleanup_useless_channels_async())


async def _cleanup_useless_channels_async() -> dict[str, Any]:
    """Асинхронная реализация очистки бесполезных каналов."""
    from sqlalchemy import delete, or_

    from src.db.models.telegram_chat import TelegramChat

    stats = {"deleted": 0, "skipped": 0}

    async with async_session_factory() as session:
        # Находим каналы для удаления:
        # - без названия (title IS NULL OR title = '')
        # - тестовые (username LIKE 'test%' OR 'temp%' OR title LIKE 'Test Channel%')
        # - без подписчиков (member_count = 0)
        stmt = delete(TelegramChat).where(
            or_(
                TelegramChat.title.is_(None),
                TelegramChat.title == "",
                TelegramChat.username.like("test%"),
                TelegramChat.username.like("temp%"),
                TelegramChat.title.like("Test Channel%"),
                TelegramChat.member_count == 0,
            )
        )

        result = await session.execute(stmt)
        stats["deleted"] = result.rowcount if result.rowcount is not None else 0  # type: ignore[attr-defined]
        await session.commit()

    logger.info(f"Cleanup useless channels complete: {stats}")
    return stats


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
