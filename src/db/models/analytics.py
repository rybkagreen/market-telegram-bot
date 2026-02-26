"""
Модели для хранения аналитики Telegram каналов и групп.
"""
from __future__ import annotations

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.mailing_log import MailingLog


class ChatType(str, enum.Enum):
    """Тип Telegram чата."""

    channel = "channel"  # Telegram канал (только чтение)
    group = "group"  # Публичная группа (можно постить)
    supergroup = "supergroup"


class TelegramChat(Base):
    """
    Telegram канал или публичная группа.
    Добавляется пользователем вручную или автоматически по тематике.
    """

    __tablename__ = "telegram_chats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    chat_type: Mapped[ChatType] = mapped_column(
        Enum(ChatType), default=ChatType.channel, nullable=False
    )
    topic: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Флаги доступности
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    can_post: Mapped[bool] = mapped_column(Boolean, default=False)
    # True = открытая группа куда можно писать без вступления

    # Последние известные данные (денормализация для быстрых запросов)
    last_subscribers: Mapped[int] = mapped_column(Integer, default=0)
    last_avg_views: Mapped[int] = mapped_column(Integer, default=0)
    last_er: Mapped[float] = mapped_column(Float, default=0.0)
    last_post_frequency: Mapped[float] = mapped_column(Float, default=0.0)
    # постов в день за последние 30 дней

    last_parsed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_error_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )

    # Связи
    snapshots: Mapped[list[ChatSnapshot]] = relationship(
        "ChatSnapshot", back_populates="chat", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<TelegramChat(id={self.id}, username={self.username!r}, title={self.title!r})>"


class ChatSnapshot(Base):
    """
    Снимок метрик канала/группы за конкретный день.
    Один снимок = один день = одна строка.
    Позволяет строить графики динамики.
    """

    __tablename__ = "chat_snapshots"
    __table_args__ = (
        UniqueConstraint("chat_id", "snapshot_date", name="uq_chat_snapshot_date"),
        {"comment": "Ежедневные снимки метрик Telegram чатов"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("telegram_chats.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Основные метрики
    subscribers: Mapped[int] = mapped_column(Integer, default=0)
    # Динамика — вычисляется относительно предыдущего снимка
    subscribers_delta: Mapped[int] = mapped_column(Integer, default=0)
    subscribers_delta_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Охват постов
    avg_views: Mapped[int] = mapped_column(Integer, default=0)
    max_views: Mapped[int] = mapped_column(Integer, default=0)
    min_views: Mapped[int] = mapped_column(Integer, default=0)
    posts_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    # сколько постов взяли для расчёта avg_views

    # ER = avg_views / subscribers * 100
    er: Mapped[float] = mapped_column(Float, default=0.0)

    # Частота публикаций
    post_frequency: Mapped[float] = mapped_column(Float, default=0.0)
    # постов в день за последние 30 дней
    posts_last_30d: Mapped[int] = mapped_column(Integer, default=0)

    # Доступность для постинга
    can_post: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Связи
    chat: Mapped[TelegramChat] = relationship("TelegramChat", back_populates="snapshots")

    def __repr__(self) -> str:
        return (
            f"<ChatSnapshot(chat_id={self.chat_id}, date={self.snapshot_date}, "
            f"subscribers={self.subscribers})>"
        )
