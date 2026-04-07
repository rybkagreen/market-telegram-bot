"""LegalProfile model for user legal/tax data."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.security.field_encryption import EncryptedString, HashableEncryptedString
from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.user import User


class LegalProfile(Base, TimestampMixin):
    """Юридический профиль пользователя."""

    __tablename__ = "legal_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, unique=True
    )
    legal_status: Mapped[str] = mapped_column(String(30), nullable=False)
    # INN — encrypted at rest; inn_hash for indexed search (HMAC-SHA256)
    inn: Mapped[str | None] = mapped_column(HashableEncryptedString(300), nullable=True)
    inn_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    kpp: Mapped[str | None] = mapped_column(String(9), nullable=True)
    ogrn: Mapped[str | None] = mapped_column(String(15), nullable=True)
    ogrnip: Mapped[str | None] = mapped_column(String(15), nullable=True)
    legal_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_regime: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # Sensitive banking/payment fields — encrypted at rest
    bank_account: Mapped[str | None] = mapped_column(EncryptedString(300), nullable=True)
    bank_bik: Mapped[str | None] = mapped_column(String(9), nullable=True)
    bank_corr_account: Mapped[str | None] = mapped_column(EncryptedString(300), nullable=True)
    yoomoney_wallet: Mapped[str | None] = mapped_column(EncryptedString(300), nullable=True)
    # Passport fields — encrypted at rest
    passport_series: Mapped[str | None] = mapped_column(EncryptedString(300), nullable=True)
    passport_number: Mapped[str | None] = mapped_column(EncryptedString(300), nullable=True)
    passport_issued_by: Mapped[str | None] = mapped_column(EncryptedString(1000), nullable=True)
    passport_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Document file IDs — encrypted at rest (Telegram file_ids are sensitive)
    inn_scan_file_id: Mapped[str | None] = mapped_column(EncryptedString(500), nullable=True)
    passport_scan_file_id: Mapped[str | None] = mapped_column(EncryptedString(500), nullable=True)
    self_employed_cert_file_id: Mapped[str | None] = mapped_column(
        EncryptedString(500), nullable=True
    )
    company_doc_file_id: Mapped[str | None] = mapped_column(EncryptedString(500), nullable=True)
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="legal_profile")

    __table_args__ = (
        Index("ix_legal_profiles_user_id", "user_id", unique=True),
        Index("ix_legal_profiles_inn_hash", "inn_hash"),
    )

    def __repr__(self) -> str:
        return f"<LegalProfile(id={self.id}, user_id={self.user_id}, legal_status={self.legal_status!r})>"
