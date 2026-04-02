"""AuditLog model — append-only audit trail for sensitive data access."""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class AuditLog(Base):
    """
    Append-only audit log for sensitive resource access.
    IMPORTANT: No UPDATE or DELETE on this table in production.
    Postgres: REVOKE UPDATE, DELETE ON audit_logs FROM <app_user>;
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # NULL = system
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # READ, WRITE, DELETE, ADMIN_READ
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'legal_profile', 'contract', 'payout'
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_target_user_id", "target_user_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action={self.action!r}, "
            f"resource_type={self.resource_type!r}, user_id={self.user_id})>"
        )
