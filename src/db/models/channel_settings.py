"""
Модель настроек канала ChannelSettings.
Спринт 6 — настраиваемые правила монетизации для владельцев каналов.

One-to-one с TelegramChat (channel_id — PRIMARY KEY).
"""

from datetime import time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.analytics import TelegramChat
    from src.db.models.user import User


# Системные константы
MIN_PRICE_PER_POST = Decimal("100.00")
MAX_PACKAGE_DISCOUNT = 50
MIN_SUBSCRIPTION_DAYS = 7
MAX_SUBSCRIPTION_DAYS = 365
MAX_POSTS_PER_DAY = 5
MAX_POSTS_PER_WEEK = 35
MIN_HOURS_BETWEEN_POSTS = 4
# PLATFORM_COMMISSION импортируется из src.constants.payments


class ChannelSettings(Base, TimestampMixin):
    """
    Настройки монетизации канала.

    Атрибуты:
        channel_id: ID канала (PRIMARY KEY, FK на telegram_chats.id).
        owner_id: ID владельца канала (FK на users.id).
        price_per_post: Цена за один пост (мин. 100 кр).
        daily_package_enabled: Включен ли пакет в день.
        daily_package_max: Макс. постов в день (1-5).
        daily_package_discount: Скидка на пакет в день (0-50%).
        weekly_package_enabled: Включен ли пакет в неделю.
        weekly_package_max: Макс. постов в неделю (1-35).
        weekly_package_discount: Скидка на пакет в неделю (0-50%).
        subscription_enabled: Включена ли подписка.
        subscription_min_days: Мин. срок подписки (7-365).
        subscription_max_days: Макс. срок подписки (7-365).
        subscription_max_per_day: Макс. постов в день при подписке.
        publish_start_time: Начало времени публикаций.
        publish_end_time: Окончание времени публикаций.
        break_start_time: Начало перерыва.
        break_end_time: Окончание перерыва.
        auto_accept_enabled: Включено ли авто-принятие.
        auto_accept_min_price: Мин. цена для авто-принятия.
    """

    __tablename__ = "channel_settings"

    # Primary key (one-to-one с telegram_chats)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_chats.id", ondelete="CASCADE"),
        primary_key=True,
        doc="ID канала (PRIMARY KEY)",
    )

    # Foreign keys
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID владельца канала",
    )

    # Базовая цена
    price_per_post: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("500.00"),
        nullable=False,
        doc="Цена за один пост (мин. 100 кр)",
    )

    # Пакет в день
    daily_package_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Включен ли пакет в день",
    )

    daily_package_max: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
        doc="Макс. постов в день (1-5)",
    )

    daily_package_discount: Mapped[int] = mapped_column(
        Integer,
        default=20,
        nullable=False,
        doc="Скидка на пакет в день (0-50%)",
    )

    # Пакет в неделю
    weekly_package_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Включен ли пакет в неделю",
    )

    weekly_package_max: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
        doc="Макс. постов в неделю (1-35)",
    )

    weekly_package_discount: Mapped[int] = mapped_column(
        Integer,
        default=30,
        nullable=False,
        doc="Скидка на пакет в неделю (0-50%)",
    )

    # Подписка
    subscription_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Включена ли подписка",
    )

    subscription_min_days: Mapped[int] = mapped_column(
        Integer,
        default=7,
        nullable=False,
        doc="Мин. срок подписки (7-365)",
    )

    subscription_max_days: Mapped[int] = mapped_column(
        Integer,
        default=365,
        nullable=False,
        doc="Макс. срок подписки (7-365)",
    )

    subscription_max_per_day: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Макс. постов в день при подписке (1-5)",
    )

    # Время публикаций
    publish_start_time: Mapped[time] = mapped_column(
        Time,
        default=time(9, 0),
        nullable=False,
        doc="Начало времени публикаций",
    )

    publish_end_time: Mapped[time] = mapped_column(
        Time,
        default=time(21, 0),
        nullable=False,
        doc="Окончание времени публикаций",
    )

    break_start_time: Mapped[time | None] = mapped_column(
        Time,
        default=time(14, 0),
        nullable=True,
        doc="Начало перерыва",
    )

    break_end_time: Mapped[time | None] = mapped_column(
        Time,
        default=time(15, 0),
        nullable=True,
        doc="Окончание перерыва",
    )

    # Авто-принятие
    auto_accept_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Включено ли авто-принятие",
    )

    auto_accept_min_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        doc="Мин. цена для авто-принятия",
    )

    # Форматы публикаций (v4.2)
    allow_format_post_24h: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        doc="Разрешён формат: обычный пост 24 часа",
    )

    allow_format_post_48h: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
        doc="Разрешён формат: обычный пост 48 часов",
    )

    allow_format_post_7d: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        doc="Разрешён формат: обычный пост 7 дней",
    )

    allow_format_pin_24h: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        doc="Разрешён формат: закреплённый пост 24 часа",
    )

    allow_format_pin_48h: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        doc="Разрешён формат: закреплённый пост 48 часов",
    )

    # Отношения
    channel: Mapped["TelegramChat"] = relationship(
        "TelegramChat",
        back_populates="settings",
        lazy="selectin",
    )

    owner: Mapped["User"] = relationship(
        "User",
        back_populates="channel_settings",
        lazy="selectin",
    )

    # Индексы
    __table_args__ = (
        {
            "comment": "Настройки монетизации каналов (one-to-one с telegram_chats)",
        },
    )

    def __repr__(self) -> str:
        return (
            f"<ChannelSettings(channel_id={self.channel_id}, owner_id={self.owner_id}, "
            f"price_per_post={self.price_per_post})>"
        )
