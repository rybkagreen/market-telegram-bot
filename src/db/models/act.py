"""Act model for акты выполненных работ (acts of services rendered)."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.placement_request import PlacementRequest


class Act(Base, TimestampMixin):
    """Акт выполненных работ — первичный документ для признания выручки.

    Генерируется автоматически после удаления опубликованного поста
    (когда placement_request.deleted_at IS NOT NULL).

    Номер акта формируется через DocumentNumberService: АКТ-{YEAR}-{SEQ:04d}.

    Sprint F.1: добавлены поля для подписания (act_type, sign_status, signed_at, ...).
    """

    __tablename__ = "acts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    placement_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("placement_requests.id"), nullable=False, index=True
    )
    act_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    act_type: Mapped[str] = mapped_column(
        String(10), nullable=False, default="income", server_default="income"
    )
    act_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    pdf_path: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    meta_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Sprint E.1: link to contract
    contract_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contracts.id"), nullable=True, index=True
    )

    # Sprint F.1: signing fields
    sign_status: Mapped[str] = mapped_column(
        String(15), nullable=False, default="draft", server_default="draft"
    )
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sign_method: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationships
    placement: Mapped[PlacementRequest] = relationship("PlacementRequest", back_populates="acts")

    __table_args__ = (
        Index("ix_acts_placement_request_id", "placement_request_id"),
        Index("ix_acts_act_number", "act_number", unique=True),
        Index("ix_acts_sign_status", "sign_status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Act(id={self.id}, act_number={self.act_number!r}, "
            f"type={self.act_type}, status={self.sign_status})>"
        )
