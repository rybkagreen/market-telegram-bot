"""
Модель лога рассылки MailingLog.
Хранит историю отправок сообщений по кампаниям.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.analytics import TelegramChat
    from src.db.models.campaign import Campaign


class MailingStatus(str, Enum):
    """Статусы отправки сообщения."""

    SENT = "sent"  # Успешно отправлено
    FAILED = "failed"  # Ошибка при отправке
    SKIPPED = "skipped"  # Пропущено (rate limit, blacklist, и т.д.)
    PENDING = "pending"  # В очереди на отправку


class MailingLog(Base, TimestampMixin):
    """
    Модель лога рассылки.

    Attributes:
        id: Уникальный идентификатор лога.
        campaign_id: ID кампании (FK на Campaign).
        chat_id: ID чата (FK на Chat).
        chat_telegram_id: Telegram ID чата (для истории, если чат удален).
        status: Статус отправки.
        error_msg: Сообщение об ошибке.
        message_id: ID отправленного сообщения в Telegram.
        retry_count: Количество попыток отправки.
        sent_at: Время отправки.
        cost: Стоимость отправки в этом чате.
    """

    __tablename__ = "mailing_logs"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID кампании",
    )

    chat_id: Mapped[int | None] = mapped_column(
        ForeignKey("telegram_chats.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID чата",
    )

    # Telegram ID чата (дублируется для истории)
    chat_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        doc="Telegram ID чата (копия для истории)",
    )

    # Статус
    status: Mapped[MailingStatus] = mapped_column(
        String(50),
        default=MailingStatus.PENDING,
        nullable=False,
        index=True,
        doc="Статус отправки",
    )

    # Ошибки
    error_msg: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Сообщение об ошибке",
    )

    # Telegram message
    message_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="ID отправленного сообщения в Telegram",
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Количество попыток отправки",
    )

    # Время отправки
    sent_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
        doc="Время отправки сообщения",
    )

    cost: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
        doc="Стоимость отправки в этом чате",
    )

    # Отношения
    campaign: Mapped["Campaign"] = relationship(
        back_populates="mailing_logs",
        lazy="selectin",
    )

    chat: Mapped["TelegramChat | None"] = relationship(
        "TelegramChat",
        back_populates="mailing_logs",
        lazy="selectin",
    )

    # Индексы
    __table_args__ = (
        UniqueConstraint("campaign_id", "chat_telegram_id", name="uq_mailing_logs_campaign_chat"),
        Index("ix_mailing_logs_status_campaign", "status", "campaign_id"),
        Index("ix_mailing_logs_chat_telegram", "chat_telegram_id"),
        {
            "comment": "Логи рассылок по кампаниям",
        },
    )

    def __repr__(self) -> str:
        return f"<MailingLog(id={self.id}, campaign_id={self.campaign_id}, chat_id={self.chat_telegram_id}, status={self.status.value})>"

    @property
    def is_success(self) -> bool:
        """Проверяет, успешна ли отправка."""
        return self.status == MailingStatus.SENT

    @property
    def is_failed(self) -> bool:
        """Проверяет, неудачна ли отправка."""
        return self.status == MailingStatus.FAILED

    @property
    def is_skipped(self) -> bool:
        """Проверяет, пропущена ли отправка."""
        return self.status == MailingStatus.SKIPPED


# Import BigInteger для корректной работы
