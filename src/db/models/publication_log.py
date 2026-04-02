"""
PublicationLog — append-only evidentiary record of publication events.
S9: records every publication lifecycle event for dispute evidence.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.db.base import Base

# Valid event types
PUBLICATION_EVENT_TYPES = frozenset(
    {
        "published",
        "monitoring_ok",
        "monitoring_missing",
        "deleted_by_bot",
        "deleted_early",
        "erid_missing",
        "erid_ok",
        "bot_removed",
        "publish_failed",
    }
)


class PublicationLog(Base):
    """
    Append-only log of publication lifecycle events.

    IMPORTANT: No UPDATE, no DELETE — this is the evidentiary record for disputes.
    """

    __tablename__ = "publication_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    placement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("placement_requests.id", ondelete="RESTRICT"),
        nullable=False,
    )
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    post_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    erid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_publication_logs_placement_id", "placement_id"),
        Index("ix_publication_logs_channel_id", "channel_id"),
        Index("ix_publication_logs_event_type", "event_type"),
        Index("ix_publication_logs_detected_at", "detected_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<PublicationLog id={self.id} placement_id={self.placement_id} "
            f"event_type={self.event_type}>"
        )
