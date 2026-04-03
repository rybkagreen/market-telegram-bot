"""PlatformAccount model - singleton for platform financial tracking."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.security.field_encryption import EncryptedString, HashableEncryptedString
from src.db.base import Base


class PlatformAccount(Base):
    """Singleton модель для учёта финансов платформы. Всегда одна запись с id=1."""

    __tablename__ = "platform_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    escrow_reserved: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), server_default="0"
    )
    payout_reserved: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), server_default="0"
    )
    profit_accumulated: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), server_default="0"
    )
    total_topups: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), server_default="0"
    )
    total_payouts: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), server_default="0"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    # Legal / requisites fields (used in contract templates)
    legal_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    inn: Mapped[str | None] = mapped_column(HashableEncryptedString(300), nullable=True)
    kpp: Mapped[str | None] = mapped_column(String(9), nullable=True)
    ogrn: Mapped[str | None] = mapped_column(String(15), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    bank_account: Mapped[str | None] = mapped_column(EncryptedString(300), nullable=True)
    bank_bik: Mapped[str | None] = mapped_column(String(9), nullable=True)
    bank_corr_account: Mapped[str | None] = mapped_column(EncryptedString(300), nullable=True)

    def __repr__(self) -> str:
        return f"<PlatformAccount(id={self.id}, escrow_reserved={self.escrow_reserved})>"
