"""
Celery tasks for ORD (advertising registry) operations.
Queue: background (concurrency 4).
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from src.db.session import celery_async_session_factory as async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


async def _register_creative_async(placement_request_id: int) -> None:
    async with async_session_factory() as session:
        from src.core.services.ord_service import OrdService
        from src.db.models.placement_request import PlacementRequest

        placement = await session.get(PlacementRequest, placement_request_id)
        if not placement:
            logger.warning("ord:register_creative — placement %s not found", placement_request_id)
            return
        if placement.erid:
            logger.info("ord:register_creative — erid already set for placement %s", placement_request_id)
            return
        ord_service = OrdService(session)
        await ord_service.register_creative(
            placement_request_id=placement_request_id,
            ad_text=placement.ad_text or "",
            media_type=placement.media_type or "none",
        )
        await session.commit()


async def _report_publication_async(placement_request_id: int) -> None:
    async with async_session_factory() as session:
        from src.core.services.ord_service import OrdService
        from src.db.models.placement_request import PlacementRequest

        placement = await session.get(PlacementRequest, placement_request_id)
        if not placement:
            logger.warning("ord:report_publication — placement %s not found", placement_request_id)
            return
        if not placement.erid:
            logger.warning("ord:report_publication — no erid for placement %s, skipping", placement_request_id)
            return
        published_at = placement.published_at or datetime.now(UTC)
        ord_service = OrdService(session)
        await ord_service.report_publication(
            placement_request_id=placement_request_id,
            channel_id=0,
            published_at=published_at,
            post_url="",
        )
        await session.commit()


@celery_app.task(bind=True, base=BaseTask, name="ord:register_creative", queue="background")
def register_creative_task(self: Any, placement_request_id: int) -> None:
    """Register an ad creative in ORD asynchronously."""
    try:
        asyncio.run(_register_creative_async(placement_request_id))
    except Exception as e:
        logger.error("ord:register_creative failed for placement %s: %s", placement_request_id, e)
        raise self.retry(exc=e, countdown=300, max_retries=3) from e


@celery_app.task(bind=True, base=BaseTask, name="ord:report_publication", queue="background")
def report_publication_task(self: Any, placement_request_id: int) -> None:
    """Report publication fact to ORD asynchronously."""
    try:
        asyncio.run(_report_publication_async(placement_request_id))
    except Exception as e:
        logger.error("ord:report_publication failed for placement %s: %s", placement_request_id, e)
        raise self.retry(exc=e, countdown=300, max_retries=3) from e
