"""PlacementDispute model for arbitration disputes."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

_USERS_FK = "users.id"

if TYPE_CHECKING:
    from src.db.models.placement_request import PlacementRequest
    from src.db.models.user import User


class DisputeReason(str, Enum):
    """Причины споров.

    Объединены значения из Telegram-бота (legacy) и фронтенда (mini_app/web_portal).
    """

    # Legacy (Telegram bot)
    post_removed_early = "post_removed_early"
    bot_kicked = "bot_kicked"
    advertiser_complaint = "advertiser_complaint"

    # Frontend (mini_app / web_portal)
    not_published = "not_published"
    wrong_time = "wrong_time"
    wrong_text = "wrong_text"
    early_deletion = "early_deletion"
    other = "other"


class DisputeStatus(str, Enum):
    """Статусы споров."""

    open = "open"
    owner_explained = "owner_explained"
    resolved = "resolved"
    closed = "closed"


class DisputeResolution(str, Enum):
    """Резолюции споров.

    Объединены значения из Telegram-бота (financial) и фронтенда (display).
    """

    # Telegram bot — финансовые резолюции
    owner_fault = "owner_fault"
    advertiser_fault = "advertiser_fault"
    technical = "technical"
    partial = "partial"

    # Frontend — отображаемые резолюции
    full_refund = "full_refund"
    partial_refund = "partial_refund"
    no_refund = "no_refund"
    warning = "warning"


class PlacementDispute(Base, TimestampMixin):
    """Модель спора по размещению."""

    __tablename__ = "placement_disputes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    placement_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("placement_requests.id"), nullable=False, index=True
    )
    advertiser_id: Mapped[int] = mapped_column(Integer, ForeignKey(_USERS_FK), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey(_USERS_FK), nullable=False)
    reason: Mapped[DisputeReason] = mapped_column(nullable=False)
    status: Mapped[DisputeStatus] = mapped_column(default=DisputeStatus.open, index=True)
    owner_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    advertiser_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[DisputeResolution | None] = mapped_column(nullable=True)
    resolution_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    admin_id: Mapped[int | None] = mapped_column(Integer, ForeignKey(_USERS_FK), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    advertiser_refund_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    owner_payout_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    placement_request: Mapped[PlacementRequest] = relationship(
        "PlacementRequest", back_populates="disputes"
    )
    advertiser: Mapped[User] = relationship(
        "User", foreign_keys=[advertiser_id], back_populates="disputes_advertiser"
    )
    owner: Mapped[User] = relationship(
        "User", foreign_keys=[owner_id], back_populates="disputes_owner"
    )
    admin: Mapped[User | None] = relationship("User", foreign_keys=[admin_id])

    def __repr__(self) -> str:
        return f"<PlacementDispute(id={self.id}, placement_request_id={self.placement_request_id}, status={self.status.value})>"
