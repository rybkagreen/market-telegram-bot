"""
PayoutRequest model for owner payout requests.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin


class PayoutStatus(str, Enum):
    """Статусы заявок на выплату."""

    pending = "pending"
    processing = "processing"
    paid = "paid"
    rejected = "rejected"
    cancelled = "cancelled"


class PayoutRequest(Base, TimestampMixin):
    """
    Модель заявки на выплату владельцу канала.
    """

    __tablename__ = "payout_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[PayoutStatus] = mapped_column(
        default=PayoutStatus.pending,
        index=True,
    )
    requisites: Mapped[str] = mapped_column(String(512), nullable=False)
    admin_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", foreign_keys=[owner_id], back_populates="payout_requests")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="payout_request")
    admin: Mapped[Optional["User"]] = relationship("User", foreign_keys=[admin_id])

    def __repr__(self) -> str:
        return f"<PayoutRequest(id={self.id}, owner_id={self.owner_id}, gross_amount={self.gross_amount}, status={self.status.value})>"
