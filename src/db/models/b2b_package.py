"""
Пакетные предложения B2B-маркетплейса.
6 ниш по PRD §5.2: it, business, realestate, crypto, marketing, finance.
Пакет = набор каналов с гарантированным охватом и скидкой 10-25%.
"""

from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass


class B2BNiche(str, PyEnum):
    """B2B ниши."""

    IT = "it"
    BUSINESS = "business"
    REALESTATE = "realestate"
    CRYPTO = "crypto"
    MARKETING = "marketing"
    FINANCE = "finance"


class B2BPackage(Base, TimestampMixin):
    """
    Модель пакетного предложения B2B-маркетплейса.

    Attributes:
        id: Уникальный идентификатор пакета.
        name: Название пакета (например, "IT Starter Pack").
        niche: Ниша пакета (IT, Business, и т.д.).
        description: Описание целевой аудитории пакета.
        channels_count: Количество каналов в пакете.
        guaranteed_reach: Гарантированный охват (просмотры/24ч).
        min_er: Минимальный ER по всем каналам пакета.
        price: Цена пакета в рублях.
        discount_pct: Скидка % (10-25%) по сравнению с разовыми размещениями.
        is_active: Активен ли пакет.
        channel_ids: JSONB список ID каналов в пакете.
    """

    __tablename__ = "b2b_packages"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Основные поля
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Название пакета",
    )

    niche: Mapped[B2BNiche] = mapped_column(
        String(30),
        nullable=False,
        index=True,
        doc="Ниша пакета",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Описание целевой аудитории",
    )

    channels_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Количество каналов в пакете",
    )

    guaranteed_reach: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Гарантированный охват (просмотры/24ч)",
    )

    min_er: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Минимальный ER по пакету",
    )

    price: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        doc="Цена пакета в рублях",
    )

    discount_pct: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Скидка % (10-25%)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Активен ли пакет",
    )

    channel_ids: Mapped[list[int]] = mapped_column(
        JSONB,
        nullable=False,
        doc="Список ID каналов в пакете",
    )

    # Индексы
    __table_args__ = (
        {
            "comment": "Пакетные предложения B2B-маркетплейса",
        },
    )

    def __repr__(self) -> str:
        return f"<B2BPackage(id={self.id}, name={self.name!r}, niche={self.niche.value})>"

    @property
    def is_available(self) -> bool:
        """Проверяет доступен ли пакет для покупки."""
        return self.is_active and len(self.channel_ids) > 0
