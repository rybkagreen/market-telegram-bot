"""DocumentCounterRepository — атомарный инкремент счётчиков документов."""

import logging

from sqlalchemy import select

from src.db.models.document_counter import DocumentCounter
from src.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class DocumentCounterRepository(BaseRepository[DocumentCounter]):
    """Репозиторий для работы со счётчиками документов.

    Обеспечивает атомарную генерацию последовательных номеров через
    SELECT ... FOR UPDATE.
    """

    model = DocumentCounter

    async def get_or_create_and_increment(self, prefix: str, year: int) -> int:
        """Получить или создать счётчик и инкрементировать.

        Атомарная операция: блокирует строку через FOR UPDATE,
        инкрементирует current_seq и возвращает новое значение.

        Args:
            prefix: Префикс документа (ДГ, АКТ, СЧ).
            year: Год.

        Returns:
            Новое значение последовательности.
        """
        # Попытка найти существующую строку с блокировкой
        result = await self.session.execute(
            select(DocumentCounter)
            .where(
                DocumentCounter.prefix == prefix,
                DocumentCounter.year == year,
            )
            .with_for_update()
        )
        counter = result.scalar_one_or_none()

        if counter is not None:
            counter.current_seq += 1
            await self.session.flush()
            await self.session.refresh(counter)
            return counter.current_seq

        # Создаём новый счётчик
        counter = DocumentCounter(prefix=prefix, year=year, current_seq=1)
        self.session.add(counter)
        await self.session.flush()
        await self.session.refresh(counter)

        logger.info(f"Created new document counter: {prefix}-{year}, seq=1")
        return counter.current_seq
