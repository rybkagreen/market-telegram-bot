"""
Модель флага контента ContentFlag.
Хранит результаты модерации рекламных кампаний.
"""

from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ARRAY, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.db.models.campaign import Campaign
    from src.db.models.user import User


class ContentFlagDecision(str, Enum):
    """Решения модерации."""

    PENDING = "pending"  # Ожидает проверки
    APPROVED = "approved"  # Одобрено
    REJECTED = "rejected"  # Отклонено
    FLAGGED = "flagged"  # Помечено (требует ручной проверки)
    AUTO_APPROVED = "auto_approved"  # Автоматически одобрено (filter passed)


class ContentFlagCategory(str, Enum):
    """Категории запрещенного контента."""

    DRUGS = "drugs"  # Наркотики
    TERRORISM = "terrorism"  # Терроризм
    WEAPONS = "weapons"  # Оружие
    ADULT = "adult"  # Контент 18+
    FRAUD = "fraud"  # Мошенничество
    SUICIDE = "suicide"  # Суицид
    EXTREMISM = "extremism"  # Экстремизм
    GAMBLING = "gambling"  # Азартные игры


class ContentFlag(Base, TimestampMixin):
    """
    Модель флага контента для модерации.

    Attributes:
        id: Уникальный идентификатор флага.
        campaign_id: ID кампании (FK на Campaign).
        categories: Список категорий нарушений (ARRAY).
        flagged_fragments: JSONB с помеченными фрагментами текста.
        decision: Решение модерации.
        reviewed_by_id: ID модератора (админа).
        review_comment: Комментарий модератора.
        filter_score: Оценка фильтра контента (0.0 - 1.0).
        llm_analysis: Результат анализа LLM (Claude/OpenAI).
        auto_checked: Проверено автоматически (без участия человека).
    """

    __tablename__ = "content_flags"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="ID кампании",
    )

    # Категории нарушений (ARRAY)
    categories: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)),
        default=list,
        nullable=False,
        doc="Список категорий нарушений",
    )

    # Помеченные фрагменты (JSONB)
    flagged_fragments: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        doc="JSONB с помеченными фрагментами текста",
    )

    # Решение
    decision: Mapped[ContentFlagDecision] = mapped_column(
        String(50),
        default=ContentFlagDecision.PENDING,
        nullable=False,
        index=True,
        doc="Решение модерации",
    )

    # Модератор
    reviewed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID модератора (админа)",
    )

    review_comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Комментарий модератора",
    )

    # Оценка фильтра
    filter_score: Mapped[float] = mapped_column(
        default=0.0,
        nullable=False,
        doc="Оценка фильтра контента (0.0 - 1.0)",
    )

    # LLM анализ
    llm_analysis: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Результат анализа LLM",
    )

    llm_categories: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(String(50)),
        nullable=True,
        doc="Категории от LLM",
    )

    # Автопроверка
    auto_checked: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        doc="Проверено автоматически",
    )

    # Отношения
    campaign: Mapped["Campaign"] = relationship(
        lazy="selectin",
    )

    reviewer: Mapped[Optional["User"]] = relationship(
        foreign_keys=[reviewed_by_id],
        lazy="selectin",
    )

    # Индексы
    __table_args__ = (
        UniqueConstraint("campaign_id", name="uq_content_flags_campaign_id"),
        Index("ix_content_flags_decision", "decision"),
        Index("ix_content_flags_categories", "categories", postgresql_using="gin"),
        {
            "comment": "Флаги модерации контента",
        },
    )

    def __repr__(self) -> str:
        return f"<ContentFlag(id={self.id}, campaign_id={self.campaign_id}, decision={self.decision.value})>"

    @property
    def is_pending(self) -> bool:
        """Проверяет, ожидает ли флаг проверки."""
        return self.decision == ContentFlagDecision.PENDING

    @property
    def is_approved(self) -> bool:
        """Проверяет, одобрено ли содержимое."""
        return self.decision in (ContentFlagDecision.APPROVED, ContentFlagDecision.AUTO_APPROVED)

    @property
    def is_rejected(self) -> bool:
        """Проверяет, отклонено ли содержимое."""
        return self.decision == ContentFlagDecision.REJECTED

    @property
    def requires_manual_review(self) -> bool:
        """Проверяет, требуется ли ручная проверка."""
        return self.decision == ContentFlagDecision.FLAGGED

    @property
    def has_violations(self) -> bool:
        """Проверяет, есть ли нарушения."""
        return len(self.categories) > 0

    def add_category(self, category: str) -> None:
        """Добавляет категорию нарушения."""
        if category not in self.categories:
            self.categories.append(category)

    def get_flagged_text_fragments(self) -> list[str]:
        """Возвращает список помеченных текстовых фрагментов."""
        if not self.flagged_fragments:
            return []
        return self.flagged_fragments.get("fragments", [])

    def get_category_descriptions(self) -> list[str]:
        """Возвращает описания категорий нарушений."""
        descriptions = {
            ContentFlagCategory.DRUGS.value: "Наркотические вещества",
            ContentFlagCategory.TERRORISM.value: "Терроризм и экстремизм",
            ContentFlagCategory.WEAPONS.value: "Оружие и боеприпасы",
            ContentFlagCategory.ADULT.value: "Контент для взрослых (18+)",
            ContentFlagCategory.FRAUD.value: "Мошенничество и обман",
            ContentFlagCategory.SUICIDE.value: "Пропаганда суицида",
            ContentFlagCategory.EXTREMISM.value: "Экстремистские материалы",
            ContentFlagCategory.GAMBLING.value: "Азартные игры и ставки",
        }
        return [descriptions.get(cat, cat) for cat in self.categories]
