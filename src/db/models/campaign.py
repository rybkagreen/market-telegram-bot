"""
Модель рекламной кампании Campaign.
Хранит информацию о рекламных кампаниях пользователей.
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.mailing_log import MailingLog
    from src.db.models.user import User


class CampaignStatus(str, Enum):
    """Статусы рекламной кампании."""

    DRAFT = "draft"  # Черновик, не готов к запуску
    QUEUED = "queued"  # В очереди на запуск (запланирован)
    RUNNING = "running"  # В процессе рассылки
    DONE = "done"  # Завершена успешно
    ERROR = "error"  # Завершена с ошибкой
    PAUSED = "paused"  # На паузе
    CANCELLED = "cancelled"  # Отменена пользователем
    ACCOUNT_BANNED = "banned"  # Telegram-аккаунт заблокирован


class Campaign(Base, TimestampMixin):
    """
    Модель рекламной кампании.

    Attributes:
        id: Уникальный идентификатор кампании.
        user_id: ID владельца кампании (FK на User).
        title: Заголовок кампании (для внутреннего использования).
        text: Текст рекламного сообщения.
        ai_description: Описание для ИИ (если текст генерировался ИИ).
        status: Статус кампании.
        filters_json: JSONB с фильтрами таргетинга.
        scheduled_at: Запланированное время запуска.
        started_at: Фактическое время начала рассылки.
        completed_at: Время завершения рассылки.
        error_message: Сообщение об ошибке (если статус error).
        total_chats: Общее количество чатов для рассылки.
        sent_count: Количество отправленных сообщений.
        failed_count: Количество неудачных отправок.
        skipped_count: Количество пропущенных чатов.
        cost: Стоимость кампании в рублях.
    """

    __tablename__ = "campaigns"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID владельца кампании",
    )

    # Основные поля
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Заголовок кампании",
    )

    topic: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Тематика кампании",
    )

    header: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Заголовок рекламного текста (первая строка)",
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Текст рекламного сообщения",
    )

    image_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Telegram file ID изображения (опционально)",
    )

    ai_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Описание для ИИ-генерации",
    )

    # Статус
    status: Mapped[CampaignStatus] = mapped_column(
        String(50),
        default=CampaignStatus.DRAFT,
        nullable=False,
        index=True,
        doc="Статус кампании",
    )

    # Фильтры таргетинга (JSONB)
    filters_json: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        doc="JSONB с фильтрами таргетинга (темы, размер чатов, blacklist)",
    )

    # Планирование
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        doc="Запланированное время запуска",
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Фактическое время начала рассылки",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Время завершения рассылки",
    )

    # Ошибки
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Сообщение об ошибке",
    )

    # Статистика
    total_chats: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Общее количество чатов для рассылки",
    )

    sent_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Количество отправленных сообщений",
    )

    failed_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Количество неудачных отправок",
    )

    skipped_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Количество пропущенных чатов",
    )

    # Стоимость
    cost: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
        doc="Стоимость кампании в рублях",
    )

    # Отношения
    user: Mapped["User"] = relationship(
        back_populates="campaigns",
        lazy="selectin",
    )

    mailing_logs: Mapped[list["MailingLog"]] = relationship(
        back_populates="campaign",
        lazy="selectin",
        cascade="all, delete-orphan",
        doc="Логи рассылки кампании",
    )

    # Индексы
    __table_args__ = (
        Index("ix_campaigns_user_status", "user_id", "status"),
        Index("ix_campaigns_scheduled_status", "scheduled_at", "status"),
        {
            "comment": "Рекламные кампании пользователей",
        },
    )

    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, title={self.title!r}, status={self.status.value})>"

    @property
    def success_rate(self) -> float:
        """Процент успешных отправок."""
        if self.total_chats == 0:
            return 0.0
        return (self.sent_count / self.total_chats) * 100

    @property
    def progress(self) -> float:
        """Прогресс выполнения кампании (0-100%)."""
        if self.total_chats == 0:
            return 0.0
        processed = self.sent_count + self.failed_count + self.skipped_count
        return min((processed / self.total_chats) * 100, 100.0)

    @property
    def filters(self) -> dict:
        """Возвращает фильтры как dict (с дефолтными значениями)."""
        return self.filters_json or {}

    def get_filter_topics(self) -> list[str]:
        """Возвращает список тем для фильтра."""
        return self.filters.get("topics", [])

    def get_filter_min_members(self) -> int:
        """Возвращает минимальное количество участников."""
        return self.filters.get("min_members", 0)

    def get_filter_max_members(self) -> int:
        """Возвращает максимальное количество участников."""
        return self.filters.get("max_members", 1000000)

    def get_blacklist(self) -> list[int]:
        """Возвращает blacklist чатов."""
        return self.filters.get("blacklist", [])

    def is_scheduled(self) -> bool:
        """Проверяет, запланирована ли кампания."""
        return self.status == CampaignStatus.QUEUED and self.scheduled_at is not None

    def is_running(self) -> bool:
        """Проверяет, запущена ли кампания."""
        return self.status == CampaignStatus.RUNNING

    def is_finished(self) -> bool:
        """Проверяет, завершена ли кампания."""
        return self.status in (CampaignStatus.DONE, CampaignStatus.ERROR, CampaignStatus.CANCELLED)
