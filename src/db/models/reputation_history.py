"""
Модель истории репутации ReputationHistory.
Спринт 6 — история изменений репутации для аудита.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.placement_request import PlacementRequest
    from src.db.models.user import User


class ReputationAction(str, Enum):
    """Типы событий изменения репутации."""

    PUBLICATION = "publication"  # +1 за успешную публикацию
    REVIEW_5STAR = "review_5star"  # +2
    REVIEW_4STAR = "review_4star"  # +1
    REVIEW_3STAR = "review_3star"  # 0
    REVIEW_2STAR = "review_2star"  # -1
    REVIEW_1STAR = "review_1star"  # -2
    CANCEL_BEFORE = "cancel_before"  # -5 отмена до подтверждения
    CANCEL_AFTER = "cancel_after"  # -20 отмена после подтверждения
    CANCEL_SYSTEMATIC = "cancel_systematic"  # -20 + предупреждение (3 за 30 дней)
    REJECT_INVALID_1 = "reject_invalid_1"  # -10 первый невалидный отказ
    REJECT_INVALID_2 = "reject_invalid_2"  # -15 второй
    REJECT_INVALID_3 = "reject_invalid_3"  # -20 + бан 7 дней
    REJECT_FREQUENT = "reject_frequent"  # -5 частые отказы >50%
    RECOVERY_30DAYS = "recovery_30days"  # +5 за 30 дней без нарушений
    BAN_RESET = "ban_reset"  # сброс до 2.0 после бана
    INITIAL_MIGRATION = "initial_migration"  # служебная запись


class ReputationHistory(Base):
    """
    История изменений репутации.

    Атрибуты:
        id: Уникальный идентификатор записи.
        user_id: ID пользователя (FK на users.id).
        placement_request_id: ID заявки (FK на placement_requests.id, опционально).
        action: Тип события.
        delta: Изменение score (+1, +2, -5, -10, -20 и т.д.).
        new_score: Score после изменения.
        role: Роль ("advertiser" или "owner").
        comment: Дополнительный контекст.
    """

    __tablename__ = "reputation_history"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID пользователя",
    )

    placement_request_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("placement_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID заявки (опционально)",
    )

    # Событие
    action: Mapped[ReputationAction] = mapped_column(
        String(50),
        nullable=False,
        doc="Тип события",
    )

    delta: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Изменение score",
    )

    new_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Score после изменения",
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Роль (advertiser или owner)",
    )

    comment: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Дополнительный контекст",
    )

    # Временная метка
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.now,
        server_default="NOW()",
        nullable=False,
        doc="Время события",
    )

    # Отношения
    user: Mapped["User"] = relationship(
        "User",
        back_populates="reputation_history",
        lazy="selectin",
    )

    placement_request: Mapped[Optional["PlacementRequest"]] = relationship(
        "PlacementRequest",
        back_populates="reputation_history",
        lazy="select",
    )

    # Индексы
    __table_args__ = (
        Index("ix_reputation_history_user_id", "user_id"),
        Index("ix_reputation_history_placement_request_id", "placement_request_id"),
        Index("ix_reputation_history_created_at", "created_at"),
        Index("ix_reputation_history_role", "role"),
        {
            "comment": "История изменений репутации",
        },
    )

    def __repr__(self) -> str:
        return (
            f"<ReputationHistory(id={self.id}, user_id={self.user_id}, "
            f"action={self.action.value}, delta={self.delta})>"
        )
