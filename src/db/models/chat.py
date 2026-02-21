"""
Модель чата Chat.
Хранит информацию о Telegram-чатах для рассылки.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin


class Chat(Base, TimestampMixin):
    """
    Модель Telegram-чата для рассылки.

    Attributes:
        id: Уникальный идентификатор в БД (автоинкремент).
        telegram_id: Telegram ID чата (BigInt, уникальный).
        title: Заголовок чата/канала.
        username: Username чата (@channel_name).
        description: Описание чата (опционально).
        member_count: Количество участников.
        topic: Тематика чата (классифицированная).
        is_active: Активен ли чат для рассылки.
        is_verified: Проверенный ли чат (синяя галочка).
        is_scam: Помечен ли чат как scam.
        is_fake: Помечен ли чат как fake.
        rating: Рейтинг чата (0.0 - 10.0).
        last_checked: Время последней проверки чата.
        last_message_date: Дата последнего сообщения в чате.
        avg_post_reach: Средний охват поста.
        posts_per_day: Количество постов в день.
        error_count: Количество ошибок при отправке.
        deactivate_reason: Причина деактивации чата.
    """

    __tablename__ = "chats"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Telegram данные
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        doc="Telegram ID чата",
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Заголовок чата/канала",
    )

    username: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        doc="Username чата (@channel_name)",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Описание чата",
    )

    # Статистика
    member_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
        doc="Количество участников",
    )

    topic: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Тематика чата",
    )

    # Статусы
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Активен ли чат для рассылки",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Проверенный ли чат",
    )

    is_scam: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Помечен ли как scam",
    )

    is_fake: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Помечен ли как fake",
    )

    is_broadcast: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Является ли каналом (вещание)",
    )

    # Рейтинг и метрики
    rating: Mapped[float] = mapped_column(
        Float,
        default=5.0,
        nullable=False,
        doc="Рейтинг чата (0.0 - 10.0)",
    )

    last_checked: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="Время последней проверки чата",
    )

    last_message_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Дата последнего сообщения",
    )

    avg_post_reach: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Средний охват поста",
    )

    posts_per_day: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
        doc="Количество постов в день",
    )

    # Ошибки
    error_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Количество ошибок при отправке",
    )

    deactivate_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        doc="Причина деактивации чата",
    )

    # Индексы
    __table_args__ = (
        UniqueConstraint("telegram_id", name="uq_chats_telegram_id"),
        Index("ix_chats_topic_active", "topic", "is_active"),
        Index("ix_chats_rating_active", "rating", "is_active"),
        Index("ix_chats_members_active", "member_count", "is_active"),
        {
            "comment": "Telegram чаты для рассылки",
        },
    )

    def __repr__(self) -> str:
        return f"<Chat(id={self.id}, telegram_id={self.telegram_id}, title={self.title!r})>"

    @property
    def mention(self) -> str:
        """Возвращает упоминание чата."""
        if self.username:
            return f"@{self.username}"
        return self.title

    @property
    def is_eligible_for_mailing(self) -> bool:
        """Проверяет, подходит ли чат для рассылки."""
        return (
            self.is_active
            and not self.is_scam
            and not self.is_fake
            and self.error_count < 5
        )

    def increment_error(self) -> None:
        """Увеличивает счетчик ошибок."""
        self.error_count += 1
        if self.error_count >= 5:
            self.is_active = False
            self.deactivate_reason = "Слишком много ошибок при отправке"

    def update_rating(self, new_rating: float) -> None:
        """Обновляет рейтинг чата."""
        self.rating = max(0.0, min(10.0, new_rating))
        if self.rating < 2.0:
            self.is_active = False
            self.deactivate_reason = "Низкий рейтинг"

    def mark_checked(self) -> None:
        """Отмечает чат как проверенный."""
        self.last_checked = datetime.now(tz=self.last_checked.tzinfo) if self.last_checked else datetime.now(tz=None)
