"""ChannelMediakit model for channel media kits."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.telegram_chat import TelegramChat


class ChannelMediakit(Base, TimestampMixin):
    """Модель медиакита канала. one-to-one с TelegramChat."""

    __tablename__ = "channel_mediakits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_chats.id"), unique=True, nullable=False
    )
    owner_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    theme_color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    avg_post_reach: Mapped[int] = mapped_column(Integer, default=0)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    downloads_count: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Aliases for compatibility
    custom_description = synonym("description")
    is_public = synonym("is_published")

    # Relationships
    channel: Mapped["TelegramChat"] = relationship(
        "TelegramChat", back_populates="channel_mediakit"
    )

    def __repr__(self) -> str:
        return f"<ChannelMediakit(id={self.id}, channel_id={self.channel_id}, is_published={self.is_published})>"
