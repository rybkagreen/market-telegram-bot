"""
Category model for channel categories.
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class Category(Base):
    """
    Модель категории канала.
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name_ru: Mapped[str] = mapped_column(String(128), nullable=False)
    emoji: Mapped[str] = mapped_column(String(8), nullable=False)

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, key={self.key}, name_ru={self.name_ru})>"
