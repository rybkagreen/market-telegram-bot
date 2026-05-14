"""Audit log of contract lifecycle events.

Separate from ContractSignature (signing-specific evidence): captures
sub-stage progression for BL-037 (visible in admin timeline).

Created in Phase 4 (Q-A.2 / Q-M.5) to track ДС lifecycle without touching
Contract model with a JSONB event column.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.contract import Contract
    from src.db.models.user import User


class ContractEvent(Base):
    """Per-contract lifecycle event row (append-only).

    `event_type` is a closed discriminator. Phase 4 values:
        - ds_generated_advertiser
        - ds_generated_owner
        - ds_notified_both
        - ds_signed_advertiser
        - ds_signed_owner
        - ds_marked_active

    Future event_type values (KEP, revocation, expiry roll) extend the
    Pydantic discriminator schema in src/core/schemas/contract_event.py
    (added in PROMPT 27 Step 4).
    """

    __tablename__ = "contract_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

    contract: Mapped[Contract] = relationship("Contract", foreign_keys=[contract_id])
    actor: Mapped[User | None] = relationship("User", foreign_keys=[actor_user_id])

    __table_args__ = (
        Index("ix_contract_events_contract_id_created", "contract_id", "created_at"),
        Index("ix_contract_events_event_type", "event_type"),
        Index("ix_contract_events_actor_user_id", "actor_user_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ContractEvent(id={self.id}, contract_id={self.contract_id}, "
            f"event_type={self.event_type!r})>"
        )
