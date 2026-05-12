"""OrdAuditLogRepo — fire-and-forget event log writes for ORD registration.

Mirrors AuditLogRepo (L48): SAVEPOINT-wrapped INSERT so audit log failures
never block the registration flow. Caller owns transaction lifecycle (S-48
Pattern 1).
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.ord_audit_log import OrdAuditLog
from src.db.models.ord_registration import OrdRegistrationStatus

logger = logging.getLogger(__name__)


class OrdAuditLogRepo:
    """Append-only event log writer for ORD registration lifecycle (BL-080 8c)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        *,
        correlation_id: UUID,
        placement_id: int,
        event_type: str,
        ord_registration_id: int | None = None,
        payload: dict[str, Any] | None = None,
        status_from: OrdRegistrationStatus | None = None,
        status_to: OrdRegistrationStatus | None = None,
        error_message: str | None = None,
        attempt_number: int | None = None,
    ) -> None:
        """Insert an event log entry.

        SAVEPOINT-wrapped: if the INSERT fails (constraint violation, transient
        error), the savepoint rolls back and the outer transaction is
        untouched. The audit log write is fire-and-forget — observers могут
        see a gap, but the registration flow itself continues.

        S-48 compliant: never calls commit/rollback on the session.
        """
        try:
            async with self.session.begin_nested():
                await self.session.execute(
                    insert(OrdAuditLog).values(
                        correlation_id=correlation_id,
                        placement_id=placement_id,
                        event_type=event_type,
                        ord_registration_id=ord_registration_id,
                        payload=payload,
                        status_from=status_from,
                        status_to=status_to,
                        error_message=error_message,
                        attempt_number=attempt_number,
                    )
                )
        except Exception:
            logger.warning(
                "OrdAuditLog write failed — continuing к not block registration flow",
                exc_info=True,
            )
