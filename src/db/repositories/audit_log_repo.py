"""AuditLogRepo — fire-and-forget audit trail writes."""

import logging
from typing import Any

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


class AuditLogRepo:
    """Repository for the append-only audit_logs table."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        action: str,
        resource_type: str,
        user_id: int | None = None,
        resource_id: int | None = None,
        target_user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """
        Insert an audit log entry.
        Fire-and-forget: audit failure NEVER blocks the main operation.
        Caller is responsible for committing the session.
        """
        try:
            await self.session.execute(
                insert(AuditLog).values(
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    target_user_id=target_user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    extra=extra,
                )
            )
            await self.session.flush()
        except Exception:
            logger.warning(
                "Audit log write failed — ignoring to not block main operation", exc_info=True
            )

    async def query_logs(
        self,
        user_id: int | None = None,
        target_user_id: int | None = None,
        resource_type: str | None = None,
        action: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Query audit logs with optional filters, ordered by created_at DESC."""
        from sqlalchemy import select

        q = select(AuditLog).order_by(AuditLog.created_at.desc())
        if user_id is not None:
            q = q.where(AuditLog.user_id == user_id)
        if target_user_id is not None:
            q = q.where(AuditLog.target_user_id == target_user_id)
        if resource_type is not None:
            q = q.where(AuditLog.resource_type == resource_type)
        if action is not None:
            q = q.where(AuditLog.action == action)
        q = q.limit(limit).offset(offset)
        result = await self.session.execute(q)
        return list(result.scalars().all())
