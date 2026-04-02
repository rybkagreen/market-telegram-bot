"""
PublicationLogRepo — append-only repository for publication lifecycle events.
S9: evidentiary record for disputes, never updates or deletes.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.publication_log import PublicationLog

logger = logging.getLogger(__name__)


class PublicationLogRepo:
    """Append-only repository for publication events."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_event(
        self,
        placement_id: int,
        channel_id: int,
        event_type: str,
        message_id: int | None = None,
        post_url: str | None = None,
        erid: str | None = None,
        extra: dict | None = None,
    ) -> None:
        """
        INSERT a publication event record.

        Logging must NEVER block the publication flow — all errors are swallowed.
        """
        try:
            entry = PublicationLog(
                placement_id=placement_id,
                channel_id=channel_id,
                event_type=event_type,
                message_id=message_id,
                post_url=post_url,
                erid=erid,
                extra=extra,
            )
            self.session.add(entry)
            await self.session.flush()
        except Exception:
            logger.exception(
                "Failed to log publication event "
                "(placement_id=%s, event_type=%s) — swallowing to not block flow",
                placement_id,
                event_type,
            )

    async def get_evidence(self, placement_id: int) -> list[PublicationLog]:
        """Return all log entries for a placement, ordered chronologically."""
        result = await self.session.execute(
            select(PublicationLog)
            .where(PublicationLog.placement_id == placement_id)
            .order_by(PublicationLog.detected_at.asc())
        )
        return list(result.scalars().all())

    async def get_last_known_state(self, placement_id: int) -> PublicationLog | None:
        """Return the most recent log entry for a placement."""
        result = await self.session.execute(
            select(PublicationLog)
            .where(PublicationLog.placement_id == placement_id)
            .order_by(PublicationLog.detected_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
