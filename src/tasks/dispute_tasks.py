"""
Celery задачи для разрешения споров (Dispute Resolution).
S-32: асинхронные финансовые операции при решении споров.
"""

import asyncio
import logging
from typing import Any

from src.core.services.billing_service import billing_service
from src.db.models.dispute import DisputeResolution, DisputeStatus
from src.db.models.placement_request import PlacementStatus
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=BaseTask, name="dispute:resolve_financial")
def resolve_dispute_financial(
    self: Any,
    dispute_id: int,
    resolution: str,
    placement_request_id: int,
    final_price: float,
    advertiser_id: int,
    owner_id: int,
) -> None:
    """
    Выполнить финансовые операции при разрешении спора.

    Args:
        dispute_id: ID спора.
        resolution: Тип резолюции (owner_fault, advertiser_fault, technical, partial).
        placement_request_id: ID заявки.
        final_price: Финальная цена размещения.
        advertiser_id: ID рекламодателя.
        owner_id: ID владельца.

    Retry:
        При ошибке — retry через 5 минут (max 3 попытки).
    """
    from decimal import Decimal

    from src.db.session import celery_async_session_factory

    async def _resolve_async() -> None:
        async with celery_async_session_factory() as session:
            # Update dispute status
            from src.db.models.dispute import PlacementDispute

            dispute_result = await session.get(PlacementDispute, dispute_id)
            if not dispute_result:
                logger.error(f"Dispute {dispute_id} not found for financial resolution")
                return

            price = Decimal(str(final_price))
            new_status = PlacementStatus.refunded

            try:
                if resolution in ("owner_fault", "technical"):
                    # 100% refund to advertiser
                    await billing_service.refund_escrow(
                        session=session,
                        placement_id=placement_request_id,
                        final_price=price,
                        advertiser_id=advertiser_id,
                        owner_id=owner_id,
                        scenario="before_escrow",
                    )
                    new_status = PlacementStatus.refunded

                elif resolution == "advertiser_fault":
                    # 85% to owner
                    await billing_service.release_escrow(
                        session=session,
                        placement_id=placement_request_id,
                        final_price=price,
                        advertiser_id=advertiser_id,
                        owner_id=owner_id,
                    )
                    new_status = PlacementStatus.published

                elif resolution == "partial":
                    # ~50/50 split
                    await billing_service.refund_escrow(
                        session=session,
                        placement_id=placement_request_id,
                        final_price=price,
                        advertiser_id=advertiser_id,
                        owner_id=owner_id,
                        scenario="after_confirmation",
                    )
                    new_status = PlacementStatus.refunded

            except Exception as exc:
                logger.error(f"Financial resolution failed for dispute {dispute_id}: {exc}")
                raise

            # Update dispute and placement
            dispute_result.status = DisputeStatus.resolved
            dispute_result.resolution = DisputeResolution(resolution)
            dispute_result.resolved_at = dispute_result.resolved_at or dispute_result.created_at

            from src.db.models.placement_request import PlacementRequest

            placement = await session.get(PlacementRequest, placement_request_id)
            if placement:
                placement.status = new_status

            await session.commit()
            logger.info(
                f"Dispute {dispute_id} financially resolved: "
                f"resolution={resolution}, placement_status={new_status.value}"
            )

    try:
        asyncio.run(_resolve_async())
    except Exception as e:
        logger.error(f"Failed to financially resolve dispute {dispute_id}: {e}")
        raise self.retry(exc=e, countdown=300, max_retries=3) from e
