"""Transaction model for financial transactions."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.payout import PayoutRequest
    from src.db.models.placement_request import PlacementRequest
    from src.db.models.user import User


class TransactionType(str, Enum):
    """Типы транзакций."""

    topup = "topup"
    escrow_freeze = "escrow_freeze"
    escrow_release = "escrow_release"
    platform_fee = "platform_fee"
    refund_full = "refund_full"
    refund_partial = "refund_partial"
    cancel_penalty = "cancel_penalty"
    owner_cancel_compensation = "owner_cancel_compensation"
    payout = "payout"
    payout_fee = "payout_fee"
    credits_buy = "credits_buy"
    failed_permissions_refund = "failed_permissions_refund"
    spend = "spend"
    bonus = "bonus"
    commission = "commission"
    refund = "refund"


class Transaction(Base, TimestampMixin):
    """Модель финансовой транзакции."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[TransactionType] = mapped_column(nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    placement_request_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("placement_requests.id"), nullable=True, index=True)
    payout_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("payout_requests.id"), nullable=True)
    yookassa_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    balance_before: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    balance_after: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    placement_request: Mapped[Optional["PlacementRequest"]] = relationship("PlacementRequest", back_populates="transactions", foreign_keys=[placement_request_id])
    payout_request: Mapped[Optional["PayoutRequest"]] = relationship("PayoutRequest", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, user_id={self.user_id}, type={self.type.value}, amount={self.amount})>"
