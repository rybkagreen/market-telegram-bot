"""DocumentCounter model for sequential document numbering."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class DocumentCounter(Base):
    """Счётчик документов для сквозной нумерации.

    Составной первичный ключ (prefix, year) обеспечивает атомарный
    инкремент через SELECT ... FOR UPDATE.

    Формат номера: {PREFIX}-{YEAR}-{SEQ:04d}
    Пример: ДГ-2026-0001, АКТ-2026-0042, СЧ-2026-0100
    """

    __tablename__ = "document_counters"

    prefix: Mapped[str] = mapped_column(String(4), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    current_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    def __repr__(self) -> str:
        return (
            f"<DocumentCounter(prefix={self.prefix!r}, year={self.year}, seq={self.current_seq})>"
        )
