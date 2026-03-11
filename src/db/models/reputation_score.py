"""
Модель репутации ReputationScore.
Спринт 6 — система доверия и модерации (НЕ геймификация!).

Важно: XP ≠ Репутация
- XP (User.advertiser_xp, User.owner_xp) — геймификация, уровни, достижения
- ReputationScore — доверие, штрафы, блокировки

One-to-one с User (user_id — PRIMARY KEY).
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.user import User


class ReputationScore(Base, TimestampMixin):
    """
    Репутация пользователя (разделена по ролям).

    Атрибуты:
        user_id: ID пользователя (PRIMARY KEY, FK на users.id).
        advertiser_score: Репутация рекламодателя (0.0-10.0, старт 5.0).
        owner_score: Репутация владельца (0.0-10.0, старт 5.0).
        advertiser_violations: Счётчик нарушений рекламодателя.
        owner_violations: Счётчик нарушений владельца.
        is_advertiser_blocked: Заблокирован ли как рекламодатель.
        is_owner_blocked: Заблокирован ли как владелец.
        advertiser_blocked_until: До какой даты заблокирован как рекламодатель.
        owner_blocked_until: До какой даты заблокирован как владелец.
        block_reason: Причина блокировки.
    """

    __tablename__ = "reputation_scores"

    # Primary key (one-to-one с users)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        doc="ID пользователя (PRIMARY KEY)",
    )

    # Репутация по ролям (старт 5.0, диапазон 0.0-10.0)
    advertiser_score: Mapped[float] = mapped_column(
        default=5.0,
        nullable=False,
        doc="Репутация рекламодателя (0.0-10.0)",
    )

    owner_score: Mapped[float] = mapped_column(
        default=5.0,
        nullable=False,
        doc="Репутация владельца (0.0-10.0)",
    )

    # Счётчики нарушений
    advertiser_violations: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Счётчик нарушений рекламодателя",
    )

    owner_violations: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Счётчик нарушений владельца",
    )

    # Блокировки
    is_advertiser_blocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Заблокирован ли как рекламодатель",
    )

    is_owner_blocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Заблокирован ли как владелец",
    )

    advertiser_blocked_until: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="До какой даты заблокирован как рекламодатель",
    )

    owner_blocked_until: Mapped[datetime | None] = mapped_column(
        nullable=True,
        doc="До какой даты заблокирован как владелец",
    )

    block_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Причина блокировки",
    )

    # Отношения
    user: Mapped["User"] = relationship(
        "User",
        back_populates="reputation_score",
        lazy="selectin",
    )

    # Индексы
    __table_args__ = (
        {
            "comment": "Репутация пользователей (one-to-one с users)",
        },
    )

    def __repr__(self) -> str:
        return (
            f"<ReputationScore(user_id={self.user_id}, "
            f"advertiser_score={self.advertiser_score}, owner_score={self.owner_score})>"
        )

    @property
    def is_advertiser_active(self) -> bool:
        """Проверяет, активен ли пользователь как рекламодатель."""
        if self.is_advertiser_blocked:
            return False
        return not (self.advertiser_blocked_until and self.advertiser_blocked_until > datetime.now())

    @property
    def is_owner_active(self) -> bool:
        """Проверяет, активен ли пользователь как владелец."""
        if self.is_owner_blocked:
            return False
        return not (self.owner_blocked_until and self.owner_blocked_until > datetime.now())
