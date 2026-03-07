"""
Рейтинг каналов — верифицированная система оценки.
Формула из PRD §7.1: 6 компонентов с весами.
Ежедневный пересчёт через Celery Beat.
"""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.analytics import TelegramChat


class ChannelRating(Base, TimestampMixin):
    """
    Модель ежедневного рейтинга канала.

    Attributes:
        id: Уникальный идентификатор записи.
        channel_id: ID канала (FK на telegram_chats.id).
        date: Дата рейтинга.
        subscribers: Количество подписчиков.
        avg_views: Среднее количество просмотров.
        er: Engagement Rate (%).

        # Компоненты рейтинга (PRD §7.1)
        reach_score: Reach score (0-100, вес 30%).
        er_score: ER score (0-100, вес 25%).
        growth_score: Growth score (0-100, вес 15%).
        frequency_score: Frequency score (0-100, вес 10%).
        reliability_score: Reliability score (0-100, вес 15%).
        age_score: Age score (0-100, вес 5%).

        total_score: Итоговый балл (0-100).
        rank_in_topic: Позиция в тематике.
        fraud_flag: Флаг подозрительной активности.
    """

    __tablename__ = "channel_ratings"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID канала",
    )

    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        doc="Дата рейтинга",
    )

    # Основные метрики
    subscribers: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Количество подписчиков",
    )

    avg_views: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Среднее количество просмотров",
    )

    er: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Engagement Rate (%)",
    )

    # Компоненты рейтинга (PRD §7.1)
    reach_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Reach score (0-100, вес 30%)",
    )

    er_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="ER score (0-100, вес 25%)",
    )

    growth_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Growth score (0-100, вес 15%)",
    )

    frequency_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Frequency score (0-100, вес 10%)",
    )

    reliability_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Reliability score (0-100, вес 15%)",
    )

    age_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Age score (0-100, вес 5%)",
    )

    total_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        index=True,
        doc="Итоговый балл (0-100)",
    )

    rank_in_topic: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Позиция в тематике",
    )

    # Детектор накрутки
    fraud_flag: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Флаг подозрительной активности",
    )

    # Отношения
    channel: Mapped["TelegramChat"] = relationship(
        "TelegramChat",
        back_populates="ratings",
        lazy="select",
    )

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint("channel_id", "date", name="uq_channel_rating_date"),
        {
            "comment": "Ежедневные рейтинги каналов",
        },
    )

    def __repr__(self) -> str:
        return (
            f"<ChannelRating(channel_id={self.channel_id}, date={self.date}, "
            f"total_score={self.total_score})>"
        )

    @property
    def reliability_stars(self) -> float:
        """
        Конвертирует reliability_score в звёзды (1-5).
        PRD §7.2: 1★ = 0-20, 2★ = 20-40, 3★ = 40-60, 4★ = 60-80, 5★ = 80-100.
        """
        if self.reliability_score >= 80:
            return 5.0
        elif self.reliability_score >= 60:
            return 4.0
        elif self.reliability_score >= 40:
            return 3.0
        elif self.reliability_score >= 20:
            return 2.0
        else:
            return 1.0
