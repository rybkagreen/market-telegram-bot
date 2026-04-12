"""OrdRegistration model for ORD (advertising registry) tracking."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.contract import Contract
    from src.db.models.placement_request import PlacementRequest


class OrdRegistration(Base, TimestampMixin):
    """Регистрация размещения в Операторе Рекламных Данных (ОРД)."""

    __tablename__ = "ord_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    placement_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("placement_requests.id"), nullable=False, unique=True
    )
    contract_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contracts.id"), nullable=True
    )
    advertiser_ord_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    creative_ord_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    erid: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ord_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="default", server_default="default"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Yandex ORD specific fields (S-28 Phase 2)
    yandex_request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    platform_ord_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    contract_ord_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Relationships
    placement_request: Mapped[PlacementRequest] = relationship(
        "PlacementRequest", foreign_keys=[placement_request_id]
    )
    contract: Mapped[Contract | None] = relationship("Contract", foreign_keys=[contract_id])

    __table_args__ = (
        Index("ix_ord_registrations_placement_request_id", "placement_request_id", unique=True),
        Index("ix_ord_registrations_erid", "erid"),
    )

    def __repr__(self) -> str:
        return f"<OrdRegistration(id={self.id}, placement_request_id={self.placement_request_id}, status={self.status!r})>"
