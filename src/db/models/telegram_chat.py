"""TelegramChat model for Telegram channels/chats."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.channel_mediakit import ChannelMediakit
    from src.db.models.channel_settings import ChannelSettings
    from src.db.models.placement_request import PlacementRequest
    from src.db.models.user import User


class ChatType(str, Enum):
    """Типы чатов."""

    CHANNEL = "channel"
    SUPERGROUP = "supergroup"
    GROUP = "group"
    PRIVATE = "private"


class TelegramChat(Base, TimestampMixin):
    """Модель Telegram канала или чата."""

    __tablename__ = "telegram_chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    member_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_er: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    avg_views: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rating: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    category: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_parsed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="telegram_chats")
    channel_settings: Mapped[Optional["ChannelSettings"]] = relationship("ChannelSettings", back_populates="channel", uselist=False, cascade="all, delete-orphan")
    channel_mediakit: Mapped[Optional["ChannelMediakit"]] = relationship("ChannelMediakit", back_populates="channel", uselist=False, cascade="all, delete-orphan")
    placement_requests: Mapped[list["PlacementRequest"]] = relationship("PlacementRequest", back_populates="channel", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<TelegramChat(id={self.id}, telegram_id={self.telegram_id}, username={self.username!r})>"
