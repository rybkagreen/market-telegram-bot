"""
Модели для хранения аналитики Telegram каналов и групп.
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.mailing_log import MailingLog
    from src.db.models.payout import Payout
    from src.db.models.review import Review
    from src.db.models.user import User


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
    subcategory: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    language: Mapped[str] = mapped_column(String(10), default="ru", nullable=False)
    # Язык контента канала (ru, en, mixed, etc.)
    russian_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    # Оценка русскоязычности (0.0-1.0), 1.0 = полностью русский

    # Флаги доступности
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    can_post: Mapped[bool] = mapped_column(Boolean, default=False)
    # True = открытая группа куда можно писать без вступления

    # Поля для совместимости с mailing-системой (из таблицы chats)
    member_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Синоним last_subscribers для mailing-фильтров

    rating: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    # Рейтинг 0-10 для сортировки в mailing

    is_scam: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_fake: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Флаги безопасности — исключают чат из рассылок

    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Синоним parse_error_count для совместимости

    # Поля жалоб и чёрного списка
    complaint_count: Mapped[int] = mapped_column(Integer, default=0)
    last_complaint_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    blacklisted_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    blacklisted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    deactivate_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Причина деактивации для отладки

    # Последние известные данные (денормализация для быстрых запросов)
    last_subscribers: Mapped[int] = mapped_column(Integer, default=0)
    last_avg_views: Mapped[int] = mapped_column(Integer, default=0)
    last_er: Mapped[float] = mapped_column(Float, default=0.0)
    last_post_frequency: Mapped[float] = mapped_column(Float, default=0.0)
    # постов в день за последние 30 дней

    last_parsed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_error_count: Mapped[int] = mapped_column(Integer, default=0)

    # Поля для LLM-классификации
    last_classified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Когда последний раз была LLM-классификация"
    )
    llm_confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Уверенность LLM при последней классификации (0.0–1.0)"
    )
    recent_posts: Mapped[list[dict] | None] = mapped_column(
        sa.JSON,
        nullable=True,
        comment="Последние 5 постов для LLM-классификации [{'text': '...', 'date': '...'}]",
    )

    # === Поля opt-in (Спринт 0) ===
    bot_is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false",
        comment="Бот добавлен администратором в канале"
    )
    admin_added_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Когда бот был добавлен администратором"
    )
    owner_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        comment="Владелец канала (FK на users.id)"
    )
    price_per_post: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True,
        comment="Цена за один рекламный пост в рублях"
    )
    is_accepting_ads: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, server_default="false",
        comment="Канал принимает рекламные размещения"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Индексы для mailing-фильтров
    __table_args__ = (
        sa.Index("ix_telegram_chats_member_count", "member_count"),
        sa.Index("ix_telegram_chats_rating", "rating"),
        sa.Index("ix_telegram_chats_topic_active", "topic", "is_active"),
        sa.Index("ix_telegram_chats_is_active", "is_active"),
    )

    # Связи
    snapshots: Mapped[list[ChatSnapshot]] = relationship(
        "ChatSnapshot", back_populates="chat", lazy="select"
    )
    mailing_logs: Mapped[list[MailingLog]] = relationship(
        "MailingLog",
        back_populates="chat",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    owner: Mapped[User | None] = relationship(
        "User",
        back_populates="channels",
        lazy="select",
        foreign_keys=[owner_user_id],
    )

    payouts: Mapped[list[Payout]] = relationship(
        "Payout",
        back_populates="channel",
        lazy="select",
    )

    reviews: Mapped[list[Review]] = relationship(
        "Review",
        back_populates="channel",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<TelegramChat(id={self.id}, username={self.username!r}, title={self.title!r})>"

    @property
    def is_eligible_for_mailing(self) -> bool:
        """Можно ли использовать чат для рассылки."""
        return (
            self.is_active
            and not self.is_scam
            and not self.is_fake
            and (self.error_count or 0) < 5
            and self.member_count > 0
        )

    def increment_error(self, reason: str | None = None) -> None:
        """Увеличить счётчик ошибок, деактивировать после 5."""
        self.error_count = (self.error_count or 0) + 1
        self.parse_error_count = self.error_count  # синхронизировать
        if reason:
            self.deactivate_reason = reason[:500]
        if self.error_count >= 5:
            self.is_active = False

    def mark_checked(self) -> None:
        """Отметить чат как проверенный."""
        self.last_parsed_at = datetime.utcnow()


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
