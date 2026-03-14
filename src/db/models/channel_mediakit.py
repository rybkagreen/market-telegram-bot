"""
ChannelMediakit model for channel media kits.
"""


from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin


class ChannelMediakit(Base, TimestampMixin):
    """
    Модель медиакита канала.
    one-to-one с TelegramChat.
    """

    __tablename__ = "channel_mediakits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("telegram_chats.id"),
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    avg_post_reach: Mapped[int] = mapped_column(Integer, default=0)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    downloads_count: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Relationships
    channel: Mapped["TelegramChat"] = relationship("TelegramChat", back_populates="channel_mediakit")

    def __repr__(self) -> str:
        return f"<ChannelMediakit(id={self.id}, channel_id={self.channel_id}, is_published={self.is_published})>"
