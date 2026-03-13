"""
Celery задачи для публикации и удаления размещений.
S-07: публикация постов, удаление по расписанию, периодическая проверка.
"""

import asyncio
import logging
from typing import Any

from aiogram import Bot

from src.core.services.publication_service import PublicationService
from src.db.repositories.placement_request_repo import PlacementRequestRepo
from src.db.session import async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


def _get_bot() -> Bot:
    """Создать бота для Celery задачи."""
    from src.config.settings import settings

    return Bot(token=settings.bot_token)


@celery_app.task(bind=True, base=BaseTask, name="publication:publish_placement")
def publish_placement(self: Any, placement_id: int) -> None:
    """
    Опубликовать размещение.

    Args:
        self: Celery task.
        placement_id: ID заявки.

    Retry:
        При ошибке — retry через 1 час (max 3 попытки).
    """
    bot = _get_bot()

    async def _publish_async() -> None:
        async with async_session_factory() as session:
            pub_service = PublicationService()
            await pub_service.publish_placement(session, bot, placement_id)

    try:
        asyncio.run(_publish_async())
    except Exception as e:
        logger.error(f"Failed to publish placement {placement_id}: {e}")
        # Retry через 1 час
        raise self.retry(exc=e, countdown=3600, max_retries=3) from e
    finally:
        asyncio.run(bot.session.close())


@celery_app.task(bind=True, base=BaseTask, name="publication:delete_published_post")
def delete_published_post(self: Any, placement_id: int) -> None:
    """
    Удалить опубликованный пост.

    Args:
        self: Celery task.
        placement_id: ID заявки.
    """
    bot = _get_bot()

    async def _delete_async() -> None:
        async with async_session_factory() as session:
            pub_service = PublicationService()
            await pub_service.delete_published_post(bot, session, placement_id)

    try:
        asyncio.run(_delete_async())
    except Exception as e:
        logger.error(f"Failed to delete placement {placement_id}: {e}")
        raise self.retry(exc=e, countdown=300, max_retries=3) from e
    finally:
        asyncio.run(bot.session.close())


@celery_app.task(bind=True, base=BaseTask, name="publication:unpin_and_delete_post")
def unpin_and_delete_post(self: Any, placement_id: int) -> None:
    """
    Открепить и удалить пост (для pin форматов).

    Args:
        self: Celery task.
        placement_id: ID заявки.
    """
    bot = _get_bot()

    async def _unpin_delete_async() -> None:
        async with async_session_factory() as session:
            pub_service = PublicationService()
            # delete_published_post уже вызывает unpin внутри для pin форматов
            await pub_service.delete_published_post(bot, session, placement_id)

    try:
        asyncio.run(_unpin_delete_async())
    except Exception as e:
        logger.error(f"Failed to unpin/delete placement {placement_id}: {e}")
        raise self.retry(exc=e, countdown=300, max_retries=3) from e
    finally:
        asyncio.run(bot.session.close())


@celery_app.task(base=BaseTask, name="publication:check_scheduled_deletions")
def check_scheduled_deletions() -> dict[str, Any]:
    """
    Периодическая задача — найти посты с истёкшим scheduled_delete_at.

    Запускается каждые 5 минут через Celery Beat.

    Returns:
        Статистика удалений.
    """
    stats = {
        "total_found": 0,
        "deleted": 0,
        "failed": 0,
    }

    async def _check_async() -> dict[str, Any]:
        async with async_session_factory() as session:
            placement_repo = PlacementRequestRepo(session)
            placements = await placement_repo.get_scheduled_for_deletion(session)

            stats["total_found"] = len(placements)

            for placement in placements:
                try:
                    # Запускаем задачу удаления
                    delete_published_post.delay(placement.id)
                    stats["deleted"] += 1
                except Exception as e:
                    logger.error(f"Failed to schedule deletion for placement {placement.id}: {e}")
                    stats["failed"] += 1

            return stats

    try:
        return asyncio.run(_check_async())
    except Exception as e:
        logger.error(f"Failed to check scheduled deletions: {e}")
        return stats
