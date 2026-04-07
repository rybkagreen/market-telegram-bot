"""MailingLog model for tracking mailing status."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.placement_request import PlacementRequest
    from src.db.models.telegram_chat import TelegramChat


class MailingStatus(str, Enum):
    """Статусы рассылки."""

    pending_approval = "pending_approval"
    queued = "queued"
    pending = "pending"
    sent = "sent"
    failed = "failed"
    skipped = "skipped"
    rejected = "rejected"
    changes_requested = "changes_requested"
    paid = "paid"


class MailingLog(Base, TimestampMixin):
    """Лог рассылки — результат размещения в канале."""

    __tablename__ = "mailing_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    placement_request_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("placement_requests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    campaign_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    chat_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("telegram_chats.id", ondelete="SET NULL"), nullable=True
    )
    chat_telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    status: Mapped[MailingStatus] = mapped_column(
        String(32), default=MailingStatus.pending, server_default="pending", index=True
    )
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    meta_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    placement_request: Mapped["PlacementRequest | None"] = relationship(
        "PlacementRequest", back_populates="mailing_logs"
    )
    chat: Mapped["TelegramChat | None"] = relationship(
        "TelegramChat", back_populates="mailing_logs"
    )

    __table_args__ = (
        UniqueConstraint("placement_request_id", "chat_id", name="uq_mailing_placement_chat"),
        Index("ix_mailing_logs_chat_id", "chat_id"),
        Index("ix_mailing_status_chat", "status", "chat_id"),
        Index("ix_mailing_sent_at", "sent_at"),
    )

    @property
    def is_success(self) -> bool:
        """Check if mailing was successful."""
        return self.status == MailingStatus.sent

    @property
    def is_failed(self) -> bool:
        """Check if mailing failed."""
        return self.status == MailingStatus.failed

    @property
    def is_skipped(self) -> bool:
        """Check if mailing was skipped."""
        return self.status == MailingStatus.skipped

    def __repr__(self) -> str:
        return f"<MailingLog(id={self.id}, chat_telegram_id={self.chat_telegram_id}, status={self.status.value})>"
