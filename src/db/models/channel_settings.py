"""ChannelSettings model for channel configuration."""

from datetime import datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.telegram_chat import TelegramChat


class ChannelSettings(Base):
    """Модель настроек канала. one-to-one с TelegramChat."""

    __tablename__ = "channel_settings"

    channel_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_chats.id"), primary_key=True
    )
    price_per_post: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("1000"), server_default="1000"
    )
    allow_format_post_24h: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    allow_format_post_48h: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    allow_format_post_7d: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    allow_format_pin_24h: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    allow_format_pin_48h: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    max_posts_per_day: Mapped[int] = mapped_column(Integer, default=2, server_default="2")
    max_posts_per_week: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    publish_start_time: Mapped[time] = mapped_column(Time, default=time(9, 0))
    publish_end_time: Mapped[time] = mapped_column(Time, default=time(21, 0))
    break_start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    break_end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    auto_accept_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    # Relationships
    channel: Mapped["TelegramChat"] = relationship(
        "TelegramChat", back_populates="channel_settings"
    )

    def __repr__(self) -> str:
        return (
            f"<ChannelSettings(channel_id={self.channel_id}, price_per_post={self.price_per_post})>"
        )
