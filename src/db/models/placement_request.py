"""PlacementRequest model for advertising placement requests."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

_CASCADE_ALL_DELETE = "all, delete-orphan"

if TYPE_CHECKING:
    from src.db.models.act import Act
    from src.db.models.dispute import PlacementDispute
    from src.db.models.mailing_log import MailingLog
    from src.db.models.reputation_history import ReputationHistory
    from src.db.models.review import Review
    from src.db.models.telegram_chat import TelegramChat
    from src.db.models.transaction import Transaction
    from src.db.models.user import User


class PlacementStatus(str, Enum):
    """Статусы заявки на размещение."""

    pending_owner = "pending_owner"
    counter_offer = "counter_offer"
    pending_payment = "pending_payment"
    escrow = "escrow"
    published = "published"
    completed = "completed"
    failed = "failed"
    failed_permissions = "failed_permissions"
    refunded = "refunded"
    cancelled = "cancelled"


class PublicationFormat(str, Enum):
    """Форматы публикации."""

    post_24h = "post_24h"
    post_48h = "post_48h"
    post_7d = "post_7d"
    pin_24h = "pin_24h"
    pin_48h = "pin_48h"


class PlacementRequest(Base, TimestampMixin):
    """Модель заявки на размещение рекламы."""

    __tablename__ = "placement_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    advertiser_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    channel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_chats.id"), nullable=False, index=True
    )
    status: Mapped[PlacementStatus] = mapped_column(
        default=PlacementStatus.pending_owner, index=True
    )
    publication_format: Mapped[PublicationFormat] = mapped_column(
        default=PublicationFormat.post_24h
    )
    ad_text: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    final_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    proposed_schedule: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    final_schedule: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    counter_offer_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    counter_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    counter_schedule: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    counter_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    # FIX #4: Separate field for advertiser's counter-offer (prevents data collision)
    advertiser_counter_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    advertiser_counter_schedule: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    advertiser_counter_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    scheduled_delete_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_reach: Mapped[int | None] = mapped_column(nullable=True)
    clicks_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tracking_short_code: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True)
    is_test: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )
    test_label: Mapped[str | None] = mapped_column(String(64), nullable=True, default=None)

    # Aggregated counters (Variant B — MailingLog replacement)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    click_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Media
    media_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="none",
        server_default="none",
        comment="MediaType: none/photo/video",
    )
    video_file_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    video_thumbnail_file_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    video_duration: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="seconds")

    # Escrow
    escrow_transaction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("transactions.id"), nullable=True, index=True
    )

    # ORD
    erid: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="ad marking token from ORD"
    )

    # Meta
    meta_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)

    # Relationships
    advertiser: Mapped[User] = relationship(
        "User", foreign_keys=[advertiser_id], back_populates="placement_requests_advertiser"
    )
    owner: Mapped[User] = relationship(
        "User", foreign_keys=[owner_id], back_populates="placement_requests_owner"
    )
    channel: Mapped[TelegramChat] = relationship(
        "TelegramChat", back_populates="placement_requests"
    )
    acts: Mapped[list[Act]] = relationship(
        "Act", back_populates="placement", cascade=_CASCADE_ALL_DELETE
    )
    transactions: Mapped[list[Transaction]] = relationship(
        "Transaction",
        back_populates="placement_request",
        foreign_keys="[Transaction.placement_request_id]",
    )
    reviews: Mapped[list[Review]] = relationship(
        "Review", back_populates="placement_request", cascade=_CASCADE_ALL_DELETE
    )
    disputes: Mapped[list[PlacementDispute]] = relationship(
        "PlacementDispute", back_populates="placement_request", cascade=_CASCADE_ALL_DELETE
    )
    reputation_history: Mapped[list[ReputationHistory]] = relationship(
        "ReputationHistory", back_populates="placement_request"
    )
    mailing_logs: Mapped[list[MailingLog]] = relationship(
        "MailingLog", back_populates="placement_request"
    )

    __table_args__ = (
        Index("ix_placement_requests_status_expires", "status", "expires_at"),
        # INV-1 (see /root/.claude/plans/optimized-brewing-music.md):
        # status='escrow' ⇒ escrow_transaction_id IS NOT NULL AND final_price IS NOT NULL.
        CheckConstraint(
            "status != 'escrow' OR "
            "(escrow_transaction_id IS NOT NULL AND final_price IS NOT NULL)",
            name="placement_escrow_integrity",
        ),
    )

    @property
    def has_dispute(self) -> bool:
        """True if any disputes are loaded and present (requires eager load)."""
        disputes = self.__dict__.get("disputes")
        return bool(disputes)

    @property
    def dispute_status(self) -> str | None:
        """Status string of first loaded dispute, or None."""
        disputes = self.__dict__.get("disputes")
        if not disputes:
            return None
        first = disputes[0]
        return first.status.value if hasattr(first.status, "value") else str(first.status)

    def __repr__(self) -> str:
        return f"<PlacementRequest(id={self.id}, advertiser_id={self.advertiser_id}, status={self.status.value})>"
