"""
Модель выплат владельцам каналов.
Спринт 1 — базовая система учёта выплат (80% от цены поста).
Реальная интеграция с CryptoBot добавляется в Спринте 2.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.analytics import TelegramChat
    from src.db.models.mailing_log import MailingLog
    from src.db.models.user import User


class PayoutStatus(str, Enum):
    """Статусы выплаты."""

    PENDING = "pending"  # начислено, ожидает выплаты
    PROCESSING = "processing"  # в процессе перевода
    PAID = "paid"  # выплачено
    FAILED = "failed"  # ошибка выплаты
    CANCELLED = "cancelled"  # отменено


class PayoutCurrency(str, Enum):
    """Валюты выплат."""

    USDT = "USDT"
    TON = "TON"
    RUB = "RUB"


class Payout(Base, TimestampMixin):
    """
    Запись о выплате владельцу канала за одно рекламное размещение.

    Создаётся автоматически после факта публикации поста.
    80% от цены поста — владельцу, 20% — комиссия платформы.

    Attributes:
        id: Уникальный идентификатор выплаты.
        owner_id: ID владельца канала (FK на users.id).
        channel_id: ID канала (FK на telegram_chats.id).
        placement_id: ID размещения (FK на mailing_logs.id).
        amount: Сумма выплаты в рублях (80% от price_per_post).
        platform_fee: Комиссия платформы (20%).
        currency: Валюта выплаты (RUB/USDT/TON).
        status: Статус выплаты.
        wallet_address: Адрес кошелька для выплаты.
        tx_hash: Хэш транзакции после выплаты.
        paid_at: Время фактической выплаты.
    """

    __tablename__ = "payouts"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID владельца канала (внутренний users.id)",
    )

    channel_id: Mapped[int] = mapped_column(
        ForeignKey("telegram_chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID канала (telegram_chats.id)",
    )

    placement_id: Mapped[int | None] = mapped_column(
        ForeignKey("mailing_logs.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
        index=True,
        doc="ID размещения (mailing_logs.id). NULL для агрегированных выплат",
    )

    # Суммы (v4.2 — gross/fee/net)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        doc="Сумма выплаты владельцу (80% от цены поста) — legacy поле",
    )

    platform_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        doc="Комиссия платформы (20% от цены поста) — legacy поле",
    )

    # v4.2 — новая схема выплат
    gross_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Запрошено владельцем (списывается с earned_rub)",
    )

    fee_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Комиссия платформы (gross × 0.015)",
    )

    net_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        doc="Фактически перечисляется (gross - fee)",
    )

    tax_withheld: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        default=None,
        doc="Удержанный налог (NULL в MVP, заполняется post-MVP)",
    )

    # Валюта и статус
    currency: Mapped[PayoutCurrency] = mapped_column(
        String(10),
        default=PayoutCurrency.RUB,
        nullable=False,
        doc="Валюта выплаты",
    )

    status: Mapped[PayoutStatus] = mapped_column(
        String(20),
        default=PayoutStatus.PENDING,
        nullable=False,
        index=True,
        doc="Статус выплаты",
    )

    # Детали выплаты
    wallet_address: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        doc="Адрес кошелька для выплаты (USDT/TON)",
    )

    tx_hash: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        doc="Хэш транзакции после выплаты",
    )

    # Время выплаты
    paid_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        index=True,
        doc="Время фактической выплаты",
    )

    # Отношения
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="payouts",
        lazy="select",
        foreign_keys=[owner_id],
    )

    channel: Mapped["TelegramChat"] = relationship(
        "TelegramChat",
        back_populates="payouts",
        lazy="select",
    )

    placement: Mapped["MailingLog"] = relationship(
        "MailingLog",
        back_populates="payout",
        lazy="select",
    )

    # Индексы
    __table_args__ = (
        {
            "comment": "Выплаты владельцам каналов за рекламные размещения",
        },
    )

    def __repr__(self) -> str:
        return (
            f"<Payout(id={self.id}, owner_id={self.owner_id}, "
            f"amount={self.amount}, status={self.status.value})>"
        )

    @property
    def is_paid(self) -> bool:
        """Проверяет, выплачена ли выплата."""
        return self.status == PayoutStatus.PAID

    @property
    def is_pending(self) -> bool:
        """Проверяет, ожидает ли выплата выплаты."""
        return self.status == PayoutStatus.PENDING
