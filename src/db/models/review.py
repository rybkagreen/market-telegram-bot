"""
Модель отзывов — двусторонняя система оценки.
Рекламодатель оценивает канал, владелец оценивает рекламодателя.

Антифрод: отзыв только по завершённому размещению, один отзыв на пару
(reviewer_id + placement_id), дубликаты автоскрываются.
"""

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.analytics import TelegramChat
    from src.db.models.mailing_log import MailingLog
    from src.db.models.user import User


class ReviewerRole(str, Enum):
    """Роль рецензента."""

    ADVERTISER = "advertiser"  # рекламодатель оценивает канал
    OWNER = "owner"  # владелец оценивает рекламодателя


class Review(Base, TimestampMixin):
    """
    Модель отзыва о размещении.

    Attributes:
        id: Уникальный идентификатор отзыва.
        reviewer_id: ID оставившего отзыв (FK на users.id).
        reviewee_id: ID того кого оценили (FK на users.id).
        channel_id: ID канала (FK на telegram_chats.id, nullable).
        placement_id: ID размещения (FK на mailing_logs.id, NOT NULL).
        reviewer_role: Роль рецензента (advertiser/owner).

        # Оценки рекламодателя → каналу (если reviewer_role=ADVERTISER)
        score_compliance: Соответствие договорённостям (1-5, nullable).
        score_audience: Качество аудитории (1-5, nullable).
        score_speed: Скорость взаимодействия (1-5, nullable).

        # Оценки владельца → рекламодателю (если reviewer_role=OWNER)
        score_material: Качество материала (1-5, nullable).
        score_requirements: Адекватность требований (1-5, nullable).
        score_payment: Скорость оплаты (1-5, nullable).

        comment: Текст отзыва (nullable).
        is_hidden: Скрыт ли отзыв (антифрод).
    """

    __tablename__ = "reviews"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    reviewer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID оставившего отзыв",
    )

    reviewee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID того кого оценили",
    )

    channel_id: Mapped[int | None] = mapped_column(
        ForeignKey("telegram_chats.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID канала",
    )

    placement_id: Mapped[int] = mapped_column(
        ForeignKey("mailing_logs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="ID размещения (один отзыв на размещение)",
    )

    # Роль рецензента
    reviewer_role: Mapped[ReviewerRole] = mapped_column(
        String(20),
        nullable=False,
        doc="Роль рецензента (advertiser/owner)",
    )

    # Оценки рекламодателя → каналу
    score_compliance: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Соответствие договорённостям (1-5)",
    )

    score_audience: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Качество аудитории (1-5)",
    )

    score_speed: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Скорость взаимодействия (1-5)",
    )

    # Оценки владельца → рекламодателю
    score_material: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Качество материала (1-5)",
    )

    score_requirements: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Адекватность требований (1-5)",
    )

    score_payment: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Скорость оплаты (1-5)",
    )

    # Комментарий
    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Текст отзыва",
    )

    # Антифрод
    is_hidden: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        index=True,
        doc="Скрыт ли отзыв (антифрод)",
    )

    # Отношения
    reviewer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[reviewer_id],
        back_populates="reviews_given",
        lazy="select",
    )

    reviewee: Mapped["User"] = relationship(
        "User",
        foreign_keys=[reviewee_id],
        back_populates="reviews_received",
        lazy="select",
    )

    channel: Mapped["TelegramChat | None"] = relationship(
        "TelegramChat",
        back_populates="reviews",
        lazy="select",
    )

    placement: Mapped["MailingLog"] = relationship(
        "MailingLog",
        back_populates="review",
        lazy="select",
    )

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint("reviewer_id", "placement_id", name="uq_reviewer_placement"),
        {
            "comment": "Отзывы о размещениях (двусторонняя оценка)",
        },
    )

    def __repr__(self) -> str:
        return (
            f"<Review(id={self.id}, reviewer_id={self.reviewer_id}, "
            f"placement_id={self.placement_id}, role={self.reviewer_role.value})>"
        )

    @property
    def average_score(self) -> float | None:
        """Средний балл по всем заполненным оценкам."""
        scores = []
        if self.score_compliance is not None:
            scores.append(self.score_compliance)
        if self.score_audience is not None:
            scores.append(self.score_audience)
        if self.score_speed is not None:
            scores.append(self.score_speed)
        if self.score_material is not None:
            scores.append(self.score_material)
        if self.score_requirements is not None:
            scores.append(self.score_requirements)
        if self.score_payment is not None:
            scores.append(self.score_payment)

        if not scores:
            return None
        return sum(scores) / len(scores)

    @property
    def is_advertiser_review(self) -> bool:
        """Проверяет что отзыв от рекламодателя."""
        return self.reviewer_role == ReviewerRole.ADVERTISER

    @property
    def is_owner_review(self) -> bool:
        """Проверяет что отзыв от владельца."""
        return self.reviewer_role == ReviewerRole.OWNER
