"""Transaction model for financial transactions."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.act import Act
    from src.db.models.invoice import Invoice
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
    # Sprint B.2: NDFL withholding
    ndfl_withholding = "ndfl_withholding"
    # Sprint D.2: storno/reversal
    storno = "storno"
    # Admin credits and gamification
    admin_credit = "admin_credit"
    gamification_bonus = "gamification_bonus"


class Transaction(Base, TimestampMixin):
    """Модель финансовой транзакции."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    type: Mapped[TransactionType] = mapped_column(nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    placement_request_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("placement_requests.id"), nullable=True, index=True
    )
    payout_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("payout_requests.id"), nullable=True
    )
    yookassa_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payment_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    balance_before: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    balance_after: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now()
    )

    # Sprint A.3: бухгалтерские связи
    contract_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contracts.id"), nullable=True
    )
    counterparty_legal_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    currency: Mapped[str] = mapped_column(
        String(3), nullable=False, default="RUB", server_default="RUB"
    )

    # Sprint C.1: VAT tracking
    vat_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"), server_default="0"
    )

    # Sprint D.1: ООО УСН 15% expense tracking
    expense_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_tax_deductible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Sprint E.1: links to primary documents
    act_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("acts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    invoice_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Sprint D.2: storno/reversal support
    reverses_transaction_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    is_reversed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Sprint S-48 (A.2): business-level idempotency guard.
    # UNIQUE + nullable lets legacy rows keep NULL while new financial events
    # (escrow_freeze / escrow_release / refund / commission) carry a stable
    # human-readable key like `escrow_release:placement=1:owner`.
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True, index=True
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="transactions")
    placement_request: Mapped[PlacementRequest | None] = relationship(
        "PlacementRequest", back_populates="transactions", foreign_keys=[placement_request_id]
    )
    payout_request: Mapped[PayoutRequest | None] = relationship(
        "PayoutRequest", back_populates="transactions"
    )
    act: Mapped[Act | None] = relationship("Act")
    invoice: Mapped[Invoice | None] = relationship("Invoice")
    # Self-referencing: transactions that reverse THIS transaction
    reversed_transactions: Mapped[list[Transaction]] = relationship(
        "Transaction",
        foreign_keys=[reverses_transaction_id],
        back_populates="reverses_transaction",
        lazy="selectin",
    )
    # Self-referencing: THIS transaction reverses another
    reverses_transaction: Mapped[Transaction | None] = relationship(
        "Transaction",
        foreign_keys=[reverses_transaction_id],
        remote_side=[id],
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, user_id={self.user_id}, type={self.type.value}, amount={self.amount})>"
