"""
PlacementRequest model for advertising placement requests.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin


class PlacementStatus(str, Enum):
    """Статусы заявки на размещение."""

    pending_owner = "pending_owner"
    counter_offer = "counter_offer"
    pending_payment = "pending_payment"
    escrow = "escrow"
    published = "published"
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
    """
    Модель заявки на размещение рекламы.
    """

    __tablename__ = "placement_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    advertiser_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    channel_id: Mapped[int] = mapped_column(Integer, ForeignKey("telegram_chats.id"), nullable=False, index=True)
    status: Mapped[PlacementStatus] = mapped_column(
        default=PlacementStatus.pending_owner,
        index=True,
    )
    publication_format: Mapped[PublicationFormat] = mapped_column(
        default=PublicationFormat.post_24h,
    )
    ad_text: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    final_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    proposed_schedule: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_schedule: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    counter_offer_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    counter_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    counter_schedule: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    counter_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    scheduled_delete_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_reach: Mapped[int | None] = mapped_column(nullable=True)
    clicks_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tracking_short_code: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True)

    # Relationships
    advertiser: Mapped["User"] = relationship("User", foreign_keys=[advertiser_id], back_populates="placement_requests_advertiser")
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id], back_populates="placement_requests_owner")
    channel: Mapped["TelegramChat"] = relationship("TelegramChat", back_populates="placement_requests")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="placement_request")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="placement_request", cascade="all, delete-orphan")
    disputes: Mapped[list["PlacementDispute"]] = relationship("PlacementDispute", back_populates="placement_request", cascade="all, delete-orphan")
    reputation_history: Mapped[list["ReputationHistory"]] = relationship("ReputationHistory", back_populates="placement_request")

    __table_args__ = (
        Index("ix_placement_requests_status_expires", "status", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<PlacementRequest(id={self.id}, advertiser_id={self.advertiser_id}, status={self.status.value})>"
