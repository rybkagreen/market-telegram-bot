"""Contract model for platform contracts."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.placement_request import PlacementRequest
    from src.db.models.user import User


class Contract(Base, TimestampMixin):
    """Договор между пользователем и платформой."""

    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(30), nullable=False)
    contract_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )
    placement_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("placement_requests.id"), nullable=True
    )
    parent_contract_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    legal_status_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    template_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="1.0", server_default="1.0"
    )
    pdf_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_telegram_file_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    signature_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    signature_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    kep_requested: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    kep_request_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    role: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'owner' | 'advertiser'

    # Relationships
    user: Mapped[User] = relationship("User", foreign_keys=[user_id])
    placement: Mapped[PlacementRequest | None] = relationship(
        "PlacementRequest", foreign_keys=[placement_id]
    )
    parent_contract: Mapped[Contract | None] = relationship(
        "Contract", remote_side=[id], foreign_keys=[parent_contract_id]
    )

    __table_args__ = (
        Index("ix_contracts_user_id", "user_id"),
        Index("ix_contracts_placement_id", "placement_id"),
        Index("ix_contracts_type_status", "contract_type", "contract_status"),
        Index("ix_contract_placement_type", "placement_id", "contract_type"),
        Index(
            "uq_contracts_supplementary_placement_role",
            "placement_id",
            "contract_type",
            "role",
            unique=True,
            postgresql_where=text("contract_type = 'supplementary_agreement'"),
        ),
    )

    def __repr__(self) -> str:
        return f"<Contract(id={self.id}, user_id={self.user_id}, type={self.contract_type!r}, status={self.contract_status!r})>"
