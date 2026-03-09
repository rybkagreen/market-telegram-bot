"""
Модель медиакита канала.
Спринт 9 — медиакиты для привлечения рекламодателей.
"""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.analytics import TelegramChat
    from src.db.models.user import User


class ChannelMediakit(Base, TimestampMixin):
    """
    Медиакит канала — настраиваемая презентация для рекламодателей.

    Attributes:
        id: Уникальный идентификатор медиакита.
        channel_id: ID канала (FK на telegram_chats.id).
        owner_user_id: ID владельца канала (FK на users.id).

        # Контент
        custom_description: Кастомное описание (если отличается от description канала).
        logo_file_id: Telegram file ID логотипа.
        banner_file_id: Telegram file ID баннера.

        # Настройки отображения
        show_metrics: JSONB с флагами какие метрики показывать.
        theme_color: HEX цвет темы (например, "#1a73e8").
        is_public: Публичный ли медиакит (доступен по ссылке).

        # Статистика
        views_count: Количество просмотров медиакита.
        downloads_count: Количество скачиваний PDF.
    """

    __tablename__ = "channel_mediakits"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_chats.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="ID канала",
    )

    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID владельца канала",
    )

    # Контент
    custom_description: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
        doc="Кастомное описание канала",
    )

    logo_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Telegram file ID логотипа",
    )

    banner_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Telegram file ID баннера",
    )

    # Настройки отображения
    show_metrics: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=lambda: {
            "subscribers": True,
            "avg_views": True,
            "er": True,
            "post_frequency": True,
            "price": True,
            "topics": True,
        },
        doc="Какие метрики показывать",
    )

    theme_color: Mapped[str] = mapped_column(
        String(7),
        default="#1a73e8",
        nullable=False,
        doc="HEX цвет темы (например, #1a73e8)",
    )

    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Публичный ли медиакит",
    )

    # Статистика
    views_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Количество просмотров",
    )

    downloads_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Количество скачиваний PDF",
    )

    # Отношения
    channel: Mapped["TelegramChat"] = relationship(
        "TelegramChat",
        back_populates="mediakit",
        lazy="select",
    )

    owner: Mapped["User"] = relationship(
        "User",
        back_populates="mediakits",
        lazy="select",
    )

    # Индексы и ограничения
    __table_args__ = (
        {
            "comment": "Медиакиты каналов для привлечения рекламодателей",
        },
    )

    def __repr__(self) -> str:
        return f"<ChannelMediakit(id={self.id}, channel_id={self.channel_id}, owner_id={self.owner_user_id})>"

    @property
    def is_customized(self) -> bool:
        """Проверяет есть ли кастомизация (логотип или описание)."""
        return bool(self.logo_file_id or self.custom_description)
