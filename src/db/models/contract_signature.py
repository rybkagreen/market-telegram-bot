"""ContractSignature — append-only audit trail for every signature event."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class ContractSignature(Base):
    """Запись о подписании договора. Append-only — не изменяется и не удаляется."""

    __tablename__ = "contract_signatures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("contracts.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'owner' | 'advertiser'
    legal_status: Mapped[str] = mapped_column(String(30), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    signature_method: Mapped[str] = mapped_column(String(20), nullable=False)  # 'button_accept' | 'sms_code' | 'kep_diadoc'
    document_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256 hex
    template_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0", server_default="1.0")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_contract_signatures_contract_id", "contract_id"),
        Index("ix_contract_signatures_user_id", "user_id"),
        Index("ix_contract_signatures_signed_at", "signed_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ContractSignature(id={self.id}, contract_id={self.contract_id}, "
            f"user_id={self.user_id}, method={self.signature_method!r})>"
        )
