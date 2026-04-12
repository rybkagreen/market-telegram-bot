"""Invoice model for B2B billing."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.contract import Contract
    from src.db.models.placement_request import PlacementRequest
    from src.db.models.user import User


class Invoice(Base, TimestampMixin):
    """Модель счёта на оплату (B2B)."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    invoice_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    amount_rub: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vat_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"), server_default="0"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )
    pdf_path: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # Sprint E.1: links to placement and contract
    placement_request_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("placement_requests.id"), nullable=True, index=True
    )
    contract_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contracts.id"), nullable=True, index=True
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="invoices")
    placement_request: Mapped[PlacementRequest | None] = relationship(
        "PlacementRequest", foreign_keys=[placement_request_id]
    )
    contract: Mapped[Contract | None] = relationship("Contract")

    def __repr__(self) -> str:
        return f"<Invoice(id={self.id}, number={self.invoice_number!r}, amount={self.amount_rub})>"
