"""PayoutRequest model for owner payout requests."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.security.field_encryption import EncryptedString
from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.transaction import Transaction
    from src.db.models.user import User


# 5b.7b CL-2: constraint name for the UNIQUE index on idempotency_key column.
# Mirrors src/db/migrations/versions/0001_initial_schema.py:816 literal.
# Production code (routers/payouts.py error handling) and tests import this
# constant — single source of truth for runtime constraint introspection.
IDEMPOTENCY_KEY_CONSTRAINT_NAME = "ix_payout_requests_idempotency_key"


class PayoutStatus(str, Enum):
    """Статусы заявок на выплату."""

    pending = "pending"
    processing = "processing"
    paid = "paid"
    rejected = "rejected"
    cancelled = "cancelled"


class PayoutMethodType(str, Enum):
    """Типы методов выплаты (Phase 3b minimal subset; Phase 5 may extend)."""

    bank_card = "bank_card"
    yoomoney = "yoomoney"
    sbp = "sbp"
    bank_transfer = "bank_transfer"


class PayoutRequest(Base, TimestampMixin):
    """Модель заявки на выплату владельцу канала."""

    __tablename__ = "payout_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[PayoutStatus] = mapped_column(default=PayoutStatus.pending, index=True)
    requisites: Mapped[str] = mapped_column(EncryptedString(2048), nullable=False)
    admin_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sprint B.2: NDFL withholding & NPD receipt tracking
    ndfl_withheld: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True, default=Decimal("0"), server_default="0"
    )
    npd_receipt_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    npd_receipt_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    npd_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )

    # Phase 3: G06 typed payout method (D2 — enum tag, per-method validators in 3b).
    # Phase 3b 5b.1.4 (M3=a): String(16) → enum (mirrors PayoutStatus pattern —
    # Mapped[Enum] shortcut auto-creates the postgres type via create_all()).
    payout_method_type: Mapped[PayoutMethodType | None] = mapped_column(nullable=True)

    # Phase 3b 5b.1.3: business-level idempotency guard for payout events.
    # UNIQUE + nullable mirrors transactions.idempotency_key pattern; service-level
    # keying convention landed in 5b.7b (POST /api/payouts/ — X-Idempotency-Key).
    # IDEMPOTENCY_KEY_CONSTRAINT_NAME below mirrors the migration literal —
    # production code AND tests import it for runtime constraint introspection.
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True, index=True
    )

    # Relationships
    owner: Mapped[User] = relationship(
        "User", foreign_keys=[owner_id], back_populates="payout_requests"
    )
    transactions: Mapped[list[Transaction]] = relationship(
        "Transaction", back_populates="payout_request"
    )
    admin: Mapped[User | None] = relationship("User", foreign_keys=[admin_id])

    def __repr__(self) -> str:
        return f"<PayoutRequest(id={self.id}, owner_id={self.owner_id}, gross_amount={self.gross_amount}, status={self.status.value})>"
