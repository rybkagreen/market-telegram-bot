"""TelegramChat model for Telegram channels/chats."""

import itertools
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

_fake_telegram_id_counter = itertools.count(start=-(2**32))

from src.db.base import Base, TimestampMixin  # noqa: E402

CASCADE_ALL = "all, delete-orphan"

if TYPE_CHECKING:
    from src.db.models.channel_mediakit import ChannelMediakit
    from src.db.models.channel_settings import ChannelSettings
    from src.db.models.mailing_log import MailingLog
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
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        default=lambda: next(_fake_telegram_id_counter),
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    member_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_er: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    avg_views: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rating: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    category: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_test: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )
    last_parsed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Aliases for compatibility
    owner_user_id = synonym("owner_id")
    topic = synonym("category")

    # Relationships
    owner: Mapped[User] = relationship("User", back_populates="telegram_chats")
    channel_settings: Mapped[ChannelSettings | None] = relationship(
        "ChannelSettings", back_populates="channel", uselist=False, cascade=CASCADE_ALL
    )
    channel_mediakit: Mapped[ChannelMediakit | None] = relationship(
        "ChannelMediakit", back_populates="channel", uselist=False, cascade=CASCADE_ALL
    )
    placement_requests: Mapped[list[PlacementRequest]] = relationship(
        "PlacementRequest", back_populates="channel", cascade=CASCADE_ALL
    )
    mailing_logs: Mapped[list[MailingLog]] = relationship("MailingLog", back_populates="chat")

    def __repr__(self) -> str:
        return f"<TelegramChat(id={self.id}, telegram_id={self.telegram_id}, username={self.username!r})>"
