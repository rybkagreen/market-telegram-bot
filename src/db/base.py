"""
Базовые классы SQLAlchemy для моделей.
DeclarativeBase и TimestampMixin для всех моделей.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """
    Базовый класс для всех SQLAlchemy моделей.
    
    Использует snake_case для именования таблиц автоматически.
    """

    # Автоматическое именование таблиц в snake_case
    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Генерирует имя таблицы из имени класса в snake_case."""
        name = cls.__name__
        # Добавляем 's' для множественного числа и конвертируем в snake_case
        result = ""
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                result += "_"
            result += char.lower()
        return result + "s"

    def to_dict(self) -> dict[str, Any]:
        """
        Конвертирует модель в словарь.
        Включает все колонки и отношения.
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result


class TimestampMixin:
    """
    Миксин для добавления временных меток created_at и updated_at.
    
    Все модели с этим миксином будут автоматически отслеживать
    время создания и последнего обновления записи.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Время создания записи",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Время последнего обновления записи",
    )

    @property
    def created_at_iso(self) -> str:
        """Возвращает created_at в ISO формате."""
        return self.created_at.isoformat() if self.created_at else ""

    @property
    def updated_at_iso(self) -> str:
        """Возвращает updated_at в ISO формате."""
        return self.updated_at.isoformat() if self.updated_at else ""
