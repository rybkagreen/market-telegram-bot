"""DocumentNumberService — атомарная генерация номеров документов.

Формат: {PREFIX}-{YEAR}-{SEQ:04d}
Примеры: ДГ-2026-0001, АКТ-2026-0042, СЧ-2026-0100
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.repositories.document_counter_repo import DocumentCounterRepository

logger = logging.getLogger(__name__)


class DocumentNumberService:
    """Сервис для генерации последовательных номеров документов.

    Использует SELECT ... FOR UPDATE для атомарного инкремента
    счётчика в таблице document_counters.

    Usage:
        doc_num = await DocumentNumberService.generate_next(
            session, prefix="АКТ"
        )
        # → "АКТ-2026-0001"
    """

    @classmethod
    async def generate_next(cls, session: AsyncSession, prefix: str) -> str:
        """Сгенерировать следующий номер документа.

        Args:
            session: Асинхронная сессия.
            prefix: Префикс документа (ДГ, АКТ, СЧ).

        Returns:
            Строка номера в формате {PREFIX}-{YEAR}-{SEQ:04d}.
        """
        year = datetime.now(UTC).year

        repo = DocumentCounterRepository(session)
        seq = await repo.get_or_create_and_increment(prefix, year)

        doc_number = f"{prefix}-{year}-{seq:04d}"

        logger.info(
            f"Generated document number: {doc_number} (prefix={prefix}, year={year}, seq={seq})"
        )

        return doc_number
