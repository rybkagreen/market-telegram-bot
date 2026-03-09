"""
Модели системы значков.

Badge — каталог всех возможных значков платформы (создаётся через seed).
UserBadge — факт выдачи значка конкретному пользователю.

PRD §9.2: значки за действия — Первый запуск, 100 размещений, Идеальный CTR и т.д.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.user import User


class BadgeCategory(str, PyEnum):
    """Категории значков."""

    ADVERTISER = "advertiser"  # только для рекламодателей
    OWNER = "owner"  # только для владельцев каналов
    BOTH = "both"  # для всех


class BadgeConditionType(str, PyEnum):
    """Типы условий для получения значка."""

    CAMPAIGNS_COUNT = "campaigns_count"  # количество кампаний
    SPEND_AMOUNT = "spend_amount"  # суммарно потрачено
    PLACEMENTS_COUNT = "placements_count"  # количество размещений (для владельцев)
    EARNED_AMOUNT = "earned_amount"  # суммарно заработано
    STREAK_DAYS = "streak_days"  # стрик активности
    REVIEW_COUNT = "review_count"  # количество оставленных отзывов
    MANUAL = "manual"  # выдаётся вручную администратором


class Badge(Base, TimestampMixin):
    """
    Каталог значков платформы.

    Attributes:
        id: Уникальный идентификатор значка.
        code: Уникальный код значка (например, "first_campaign", "hundred_posts").
        name: Название значка.
        description: Описание значка.
        icon_emoji: Emoji-иконка значка.
        xp_reward: Награда XP за получение значка.
        category: Категория значка (advertiser/owner/both).
        condition_type: Тип условия для получения.
        condition_value: Числовое значение условия (порог).
    """

    __tablename__ = "badges"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Основные поля
    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Уникальный код значка",
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Название значка",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Описание значка",
    )

    icon_emoji: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="Emoji-иконка значка",
    )

    xp_reward: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Награда XP за получение значка",
    )

    credits_reward: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Бонус кредитами за получение значка",
    )

    is_rare: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        doc="Редкий значок",
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        doc="Активен ли значок (можно выдавать)",
    )

    category: Mapped[BadgeCategory] = mapped_column(
        String(20),
        nullable=False,
        doc="Категория значка",
    )

    condition_type: Mapped[BadgeConditionType] = mapped_column(
        String(30),
        nullable=False,
        doc="Тип условия для получения",
    )

    condition_value: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Числовое значение условия (порог)",
    )

    # Индексы и ограничения
    __table_args__ = (
        {
            "comment": "Каталог значков платформы",
        },
    )

    # Отношения
    users: Mapped[list["UserBadge"]] = relationship(
        "UserBadge",
        back_populates="badge",
        lazy="select",
        cascade="all, delete-orphan",
        doc="Пользователи получившие этот значок",
    )

    def __repr__(self) -> str:
        return f"<Badge(id={self.id}, code={self.code!r}, name={self.name!r})>"


class UserBadge(Base, TimestampMixin):
    """
    Выданный значок пользователя.

    Attributes:
        id: Уникальный идентификатор записи.
        user_id: ID пользователя (FK на users.id).
        badge_id: ID значка (FK на badges.id).
        earned_at: Дата получения значка.
    """

    __tablename__ = "user_badges"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID пользователя",
    )

    badge_id: Mapped[int] = mapped_column(
        ForeignKey("badges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID значка",
    )

    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Дата получения значка",
    )

    # Отношения
    user: Mapped["User"] = relationship(
        "User",
        back_populates="badges",
        lazy="select",
    )

    badge: Mapped[Badge] = relationship(
        "Badge",
        back_populates="users",
        lazy="select",
    )

    # Индексы и ограничения
    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
        {
            "comment": "Выданные значки пользователей",
        },
    )

    def __repr__(self) -> str:
        return f"<UserBadge(user_id={self.user_id}, badge_id={self.badge_id}, earned_at={self.earned_at})>"


class BadgeAchievement(Base, TimestampMixin):
    """
    Шаблоны достижений для автоматического начисления значков.

    Связывает значок с условием получения.
    Используется сервисом badge_service для автоматической проверки достижений.

    Примеры:
    - "first_campaign" → Первая кампания (threshold=1)
    - "100_placements" → 100 успешных размещений (threshold=100)
    - "streak_7_days" → 7 дней стрика (threshold=7)
    - "top_advertiser" → Топ-10 рекламодателей месяца (threshold=10)
    """

    __tablename__ = "badge_achievements"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    badge_id: Mapped[int] = mapped_column(
        ForeignKey("badges.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID значка который выдаётся при достижении",
    )

    # Тип достижения
    achievement_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Тип достижения (campaign_count, placement_count, streak_days, etc.)",
    )

    # Порог срабатывания
    threshold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Порог срабатывания (например, 100 размещений)",
    )

    # Описание
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Описание достижения",
    )

    # Активность
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
        doc="Включено ли достижение",
    )

    # Отношения
    badge: Mapped[Badge] = relationship(
        "Badge",
        back_populates="achievements",
        lazy="select",
    )

    # Индексы и ограничения
    __table_args__ = (
        {
            "comment": "Шаблоны достижений для автоматической выдачи значков",
        },
    )

    def __repr__(self) -> str:
        return f"<BadgeAchievement(id={self.id}, badge_id={self.badge_id}, type={self.achievement_type}, threshold={self.threshold})>"


# Добавить relationship в модель Badge
Badge.achievements = relationship(
    "BadgeAchievement",
    back_populates="badge",
    lazy="select",
    cascade="all, delete-orphan",
    doc="Достижения связанные с этим значком",
)
