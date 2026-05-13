"""OrdAuditLog model — append-only event log for ORD registration lifecycle.

BL-080 8c (Q6=(a)). Every meaningful event during ORD registration —
provider request, provider response, state transition, error — is mirrored
here. Writes are SAVEPOINT-wrapped в OrdAuditLogRepo so that audit failures
never block the main registration flow (mirror of L48 AuditLogRepo precedent).

IMPORTANT: append-only. No UPDATE or DELETE in production.
Postgres: REVOKE UPDATE, DELETE ON ord_audit_log FROM <app_user>;
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.models.ord_registration import OrdRegistrationStatus

if TYPE_CHECKING:
    pass


class OrdAuditEventType(str):
    """Canonical event_type vocabulary. Plain str (not Enum) so the column stays
    String(64) — vocabulary may grow without DB migration churn."""

    PROVIDER_REQUEST = "provider_request"
    PROVIDER_RESPONSE = "provider_response"
    STATE_TRANSITION = "state_transition"
    ERROR = "error"
    ADMIN_OVERRIDE = "admin_override"
    RETRY_ATTEMPT = "retry_attempt"


class OrdAuditLog(Base):
    """Append-only event log entry for an ORD registration."""

    __tablename__ = "ord_audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    correlation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    ord_registration_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ord_registrations.id"), nullable=True
    )
    placement_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("placement_requests.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status_from: Mapped[OrdRegistrationStatus | None] = mapped_column(nullable=True)
    status_to: Mapped[OrdRegistrationStatus | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_ord_audit_log_correlation_id", "correlation_id"),
        Index("ix_ord_audit_log_placement_id", "placement_id"),
        Index("ix_ord_audit_log_ord_registration_id", "ord_registration_id"),
        Index("ix_ord_audit_log_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<OrdAuditLog(id={self.id}, event_type={self.event_type!r}, "
            f"correlation_id={self.correlation_id})>"
        )
