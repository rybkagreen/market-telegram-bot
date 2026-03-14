"""
Transaction model for financial transactions.
"""

from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin


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


class Transaction(Base, TimestampMixin):
    """
    Модель финансовой транзакции.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[TransactionType] = mapped_column(nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    placement_request_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("placement_requests.id"),
        nullable=True,
        index=True,
    )
    payout_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("payout_requests.id"),
        nullable=True,
    )
    yookassa_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    placement_request: Mapped[Optional["PlacementRequest"]] = relationship("PlacementRequest", back_populates="transactions")
    payout_request: Mapped[Optional["PayoutRequest"]] = relationship("PayoutRequest", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, user_id={self.user_id}, type={self.type.value}, amount={self.amount})>"
