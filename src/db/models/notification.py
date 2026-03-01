"""
Модель уведомления Notification.
Хранит историю всех отправленных уведомлений пользователям.
"""

from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.user import User


class NotificationType(str, Enum):
    """Типы уведомлений."""

    CAMPAIGN_STARTED = "campaign_started"  # Кампания запущена
    CAMPAIGN_DONE = "campaign_done"  # Кампания завершена
    CAMPAIGN_ERROR = "campaign_error"  # Ошибка кампании
    LOW_BALANCE = "low_balance"  # Низкий баланс
    REFERRAL_BONUS = "referral_bonus"  # Реферальный бонус
    PAYMENT_SUCCESS = "payment_success"  # Успешная оплата
    PAYMENT_ERROR = "payment_error"  # Ошибка оплаты
    SYSTEM = "system"  # Системное уведомление


class Notification(Base, TimestampMixin):
    """
    Модель уведомления для пользователя.

    Attributes:
        id: Уникальный идентификатор в БД (автоинкремент).
        user_id: ID пользователя (FK на users).
        notification_type: Тип уведомления.
        title: Заголовок уведомления.
        message: Текст сообщения.
        is_read: Прочитано ли уведомление.
        campaign_id: ID связанной кампании (опционально).
        transaction_id: ID связанной транзакции (опционально).
        error_code: Код ошибки (для уведомлений об ошибках).
    """

    __tablename__ = "notifications"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # FK на пользователя
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID пользователя",
    )

    # Тип уведомления
    notification_type: Mapped[NotificationType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Тип уведомления",
    )

    # Заголовок и сообщение
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=True,
        doc="Заголовок уведомления",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Текст сообщения",
    )

    # Статус прочтения
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        doc="Прочитано ли уведомление",
    )

    # Связанные объекты (опционально)
    campaign_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="ID связанной кампании",
    )

    transaction_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
        doc="ID связанной транзакции",
    )

    # Код ошибки (для уведомлений об ошибках)
    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        doc="Код ошибки",
    )

    # Отношения
    user: Mapped["User"] = relationship(
        back_populates="notifications",
        lazy="joined",
        doc="Пользователь, получивший уведомление",
    )

    # Индексы
    __table_args__ = (
        {
            "comment": "История уведомлений пользователей",
        },
    )

    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, user_id={self.user_id}, "
            f"type={self.notification_type.value}, is_read={self.is_read})>"
        )

    def mark_as_read(self) -> None:
        """Отметить уведомление как прочитанное."""
        self.is_read = True
