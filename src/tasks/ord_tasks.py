"""
Celery tasks for ORD (advertising registry) operations.
Queue: background (concurrency 4).

S-28 Phase 2: Added poll_erid_status for async Yandex ORD ERIR polling.
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from src.core.exceptions import OrdPermanentError, OrdProviderRejectedError
from src.core.services.ord_retry import compute_backoff
from src.core.services.stub_ord_provider import StubOrdProvider
from src.db.models.ord_audit_log import OrdAuditEventType
from src.db.models.ord_registration import OrdRegistrationStatus
from src.db.session import celery_async_session_factory as async_session_factory
from src.tasks.celery_app import BaseTask, celery_app

logger = logging.getLogger(__name__)


async def _register_creative_async(placement_request_id: int) -> None:
    """Run a single register_creative attempt.

    Permanent failures (OrdProviderRejected → ord_blocked, OrdPermanentError →
    erir_failed) are caught here, the OrdRegistration is moved к the terminal
    status, an audit log entry is written, and the task returns normally so
    Celery does NOT retry. Transient failures bubble out for the task wrapper
    to retry с exponential backoff.
    """
    async with async_session_factory() as session:
        from src.core.services.ord_service import get_ord_service
        from src.db.models.placement_request import PlacementRequest
        from src.db.repositories.ord_audit_log_repo import OrdAuditLogRepo
        from src.db.repositories.ord_registration_repo import OrdRegistrationRepo

        placement = await session.get(PlacementRequest, placement_request_id)
        if not placement:
            logger.warning("ord:register_creative — placement %s not found", placement_request_id)
            return
        if placement.erid:
            logger.info(
                "ord:register_creative — erid already set for placement %s", placement_request_id
            )
            return
        ord_service = get_ord_service(session)
        try:
            await ord_service.register_creative(
                placement_request_id=placement_request_id,
                ad_text=placement.ad_text or "",
                media_type=placement.media_type or "none",
            )
        except OrdProviderRejectedError as exc:
            await _record_terminal_failure(
                session,
                placement_request_id,
                OrdRegistrationStatus.ord_blocked,
                exc,
                ord_audit_repo=OrdAuditLogRepo(session),
                ord_reg_repo=OrdRegistrationRepo(session),
            )
            await session.commit()
            return
        except OrdPermanentError as exc:
            await _record_terminal_failure(
                session,
                placement_request_id,
                OrdRegistrationStatus.erir_failed,
                exc,
                ord_audit_repo=OrdAuditLogRepo(session),
                ord_reg_repo=OrdRegistrationRepo(session),
            )
            await session.commit()
            return
        await session.commit()


async def _record_terminal_failure(
    session: Any,
    placement_request_id: int,
    target_status: OrdRegistrationStatus,
    exc: Exception,
    *,
    ord_audit_repo: Any,
    ord_reg_repo: Any,
) -> None:
    """Persist a terminal failure on the pending OrdRegistration row + audit it.

    Called by _register_creative_async on permanent provider errors. The row
    must exist in `pending` state (created by register_creative's pre-create
    step); if not, log a warning and skip (defensive — could happen if the
    error occurs before pre-create).
    """
    registration = await ord_reg_repo.get_by_placement(placement_request_id)
    if registration is None:
        logger.warning(
            "ord:register_creative permanent failure but no registration row; "
            "placement_request_id=%s, exc=%s",
            placement_request_id,
            exc,
        )
        return
    status_from = registration.status
    await ord_reg_repo.update_status(registration.id, target_status, error_message=str(exc)[:500])
    correlation_id = registration.correlation_id
    if correlation_id is not None:
        await ord_audit_repo.log(
            correlation_id=correlation_id,
            placement_id=placement_request_id,
            event_type=OrdAuditEventType.ERROR,
            ord_registration_id=registration.id,
            status_from=status_from,
            status_to=target_status,
            error_message=str(exc)[:500],
            payload={"exception_type": type(exc).__name__},
        )


async def _report_publication_async(placement_request_id: int) -> None:
    async with async_session_factory() as session:
        from src.core.services.ord_service import get_ord_service
        from src.db.models.placement_request import PlacementRequest

        placement = await session.get(PlacementRequest, placement_request_id)
        if not placement:
            logger.warning("ord:report_publication — placement %s not found", placement_request_id)
            return
        if not placement.erid:
            logger.warning(
                "ord:report_publication — no erid for placement %s, skipping", placement_request_id
            )
            return
        published_at = placement.published_at or datetime.now(UTC)
        ord_service = get_ord_service(session)
        await ord_service.report_publication(
            placement_request_id=placement_request_id,
            published_at=published_at,
        )
        await session.commit()


async def _poll_erid_status_async(registration_id: int) -> str:
    """Poll ERIR status for a registration. Returns status string.

    Called by poll_erid_status Celery task.
    """
    from src.core.services.ord_service import get_ord_service
    from src.db.repositories.ord_registration_repo import OrdRegistrationRepo

    async with async_session_factory() as session:
        repo = OrdRegistrationRepo(session)
        registration = await repo.get_by_id(registration_id)
        if not registration:
            logger.warning("ord:poll_erid_status — registration %s not found", registration_id)
            return "not_found"

        # Terminal states — no need to poll
        terminal_statuses = {
            OrdRegistrationStatus.erir_confirmed,
            OrdRegistrationStatus.erir_failed,
            OrdRegistrationStatus.erir_timeout,
            OrdRegistrationStatus.reported,
        }
        if registration.status in terminal_statuses:
            return registration.status.value

        if not registration.yandex_request_id:
            logger.warning(
                "ord:poll_erid_status — no yandex_request_id for registration %s",
                registration_id,
            )
            await repo.update_status(
                registration.id,
                OrdRegistrationStatus.erir_failed,
                error_message="No yandex_request_id",
            )
            return "no_request_id"

        ord_service = get_ord_service(session)

        # Skip if stub provider
        if isinstance(ord_service._provider, StubOrdProvider):
            return "stub"

        try:
            status_response = await ord_service.poll_erid_status_by_request_id(
                registration.yandex_request_id
            )
        except Exception as e:
            logger.error(
                "ord:poll_erid_status — error polling status for registration %s: %s",
                registration_id,
                e,
                exc_info=True,
            )
            raise  # Let Celery handle retry

        from src.core.services.yandex_ord_provider import ERROR_STATUSES, SUCCESS_STATUSES

        if status_response in SUCCESS_STATUSES:
            await repo.update_status(registration.id, OrdRegistrationStatus.erir_confirmed)
            logger.info(
                "ord:poll_erid_status — ERIR confirmed for registration %s",
                registration_id,
            )
            return "erir_confirmed"
        elif status_response in ERROR_STATUSES:
            await repo.update_status(
                registration.id,
                OrdRegistrationStatus.erir_failed,
                error_message=f"ERIR error: {status_response}",
            )
            logger.warning(
                "ord:poll_erid_status — ERIR failed for registration %s: %s",
                registration_id,
                status_response,
            )
            return "erir_failed"
        else:
            # Pending — retry
            logger.debug(
                "ord:poll_erid_status — pending for registration %s: %s",
                registration_id,
                status_response,
            )
            raise RuntimeError(f"ERIR status pending: {status_response}")


@celery_app.task(bind=True, base=BaseTask, name="ord:register_creative", queue="background")
def register_creative_task(self: Any, placement_request_id: int) -> None:
    """Register an ad creative in ORD asynchronously.

    Retries с exponential backoff + jitter (BL-080 8c Q3=(b)). Base 5s,
    max 5min, max 5 attempts. Replaces the previous linear 300s/3-retries
    pattern that risked thundering-herd hits on Yandex during outages.
    """
    try:
        asyncio.run(_register_creative_async(placement_request_id))
    except Exception as e:
        logger.error("ord:register_creative failed for placement %s: %s", placement_request_id, e)
        countdown = compute_backoff(self.request.retries)
        raise self.retry(exc=e, countdown=countdown, max_retries=5) from e


@celery_app.task(bind=True, base=BaseTask, name="ord:report_publication", queue="background")
def report_publication_task(self: Any, placement_request_id: int) -> None:
    """Report publication fact to ORD asynchronously.

    Retries: exponential backoff + jitter (BL-080 8c). Same envelope as
    register_creative_task.
    """
    try:
        asyncio.run(_report_publication_async(placement_request_id))
    except Exception as e:
        logger.error("ord:report_publication failed for placement %s: %s", placement_request_id, e)
        countdown = compute_backoff(self.request.retries)
        raise self.retry(exc=e, countdown=countdown, max_retries=5) from e


@celery_app.task(
    bind=True,
    base=BaseTask,
    name="ord:poll_erid_status",
    queue="background",
    max_retries=12,
)
def poll_erid_status(self: Any, registration_id: int) -> None:
    """Poll ERIR status for an ORD registration.

    Retries up to 12 times с exponential backoff + jitter (BL-080 8c
    Q3=(b)). Base 30s, max 10min — широкий poll window survives Yandex
    ERIR async-processing latency без drumming the API.

    On success: status = 'erir_confirmed'.
    On error: status = 'erir_failed'.
    On timeout: status = 'erir_timeout'.
    """
    try:
        result = asyncio.run(_poll_erid_status_async(registration_id))
        if result == "stub":
            logger.info("ord:poll_erid_status — stub provider, skipping")
            return
    except RuntimeError as e:
        if "pending" in str(e).lower():
            # Pending — retry
            if self.request.retries >= self.max_retries:

                async def _mark_timeout() -> None:
                    async with async_session_factory() as session:
                        from src.db.repositories.ord_registration_repo import OrdRegistrationRepo

                        repo = OrdRegistrationRepo(session)
                        registration = await repo.get_by_id(registration_id)
                        if registration:
                            await repo.update_status(
                                registration.id,
                                OrdRegistrationStatus.erir_timeout,
                                error_message=f"ERIR polling timeout after {self.max_retries} retries",
                            )

                asyncio.run(_mark_timeout())
                logger.warning(
                    "ord:poll_erid_status — timeout for registration %s after %d retries",
                    registration_id,
                    self.max_retries,
                )
                return
            countdown = compute_backoff(self.request.retries, base_seconds=30.0, max_seconds=600.0)
            raise self.retry(exc=e, countdown=countdown) from e
        raise
    except Exception as e:
        logger.error(
            "ord:poll_erid_status failed for registration %s: %s",
            registration_id,
            e,
            exc_info=True,
        )
        countdown = compute_backoff(self.request.retries, base_seconds=30.0, max_seconds=600.0)
        raise self.retry(exc=e, countdown=countdown) from e
