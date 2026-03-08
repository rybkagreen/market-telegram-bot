"""
Модель категории и подкатегории TopicCategory.
Хранит тематики каналов в БД вместо хардкода в Python.
"""

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint

from src.db.base import Base, TimestampMixin


class TopicCategory(Base, TimestampMixin):
    """
    Категория и подкатегория Telegram канала.

    Attributes:
        id: Уникальный идентификатор.
        topic: Основной топик (бизнес, маркетинг, it, и т.д.).
        subcategory: Подкатегория (startup, smm, programming, и т.д.).
        display_name_ru: Отображаемое название на русском.
        is_active: Активна ли категория.
        sort_order: Порядок сортировки.
    """

    __tablename__ = "topic_categories"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Topic и subcategory
    topic: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Основной топик",
    )

    subcategory: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Подкатегория",
    )

    # Отображаемое название
    display_name_ru: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Отображаемое название на русском",
    )

    # Активность и сортировка
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Активна ли категория",
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Порядок сортировки",
    )

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint("topic", "subcategory", name="uq_topic_subcategory"),
        {"comment": "Категории и подкатегории Telegram каналов"},
    )

    def __repr__(self) -> str:
        return (
            f"<TopicCategory(id={self.id}, topic={self.topic}, "
            f"subcategory={self.subcategory}, name={self.display_name_ru})>"
        )
