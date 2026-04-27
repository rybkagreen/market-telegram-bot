"""PlacementStatusHistory ORM model.

Implements Phase 2 § 2.B.0 Decision 10 (autoincrement PK, NOT UNIQUE on
(placement_id, status) — ping-pong negotiation legitimately produces
duplicate entries per placement).

This model is the historical audit trail for placement state transitions.
Writes happen exclusively through PlacementTransitionService (§ 2.B.0
Decision 7 lint enforcement, deferred to § 2.B.X).
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base
from src.db.models.placement_request import PlacementStatus

if TYPE_CHECKING:
    from src.db.models.placement_request import PlacementRequest
    from src.db.models.user import User


class PlacementStatusHistory(Base):
    """Append-only audit trail of placement status transitions."""

    __tablename__ = "placement_status_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    placement_id: Mapped[int] = mapped_column(
        ForeignKey("placement_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_status: Mapped[PlacementStatus | None] = mapped_column(
        ENUM(PlacementStatus, name="placementstatus", create_type=False),
        nullable=True,
    )
    to_status: Mapped[PlacementStatus] = mapped_column(
        ENUM(PlacementStatus, name="placementstatus", create_type=False),
        nullable=False,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    placement: Mapped["PlacementRequest"] = relationship(back_populates="status_history")
    actor: Mapped["User | None"] = relationship()

    __table_args__ = (
        Index(
            "ix_psh_placement_changed",
            "placement_id",
            "changed_at",
            postgresql_using="btree",
        ),
    )
