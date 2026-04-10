"""DocumentUploadRepository for DocumentUpload model operations."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from src.db.models.document_upload import DocumentUpload
from src.db.repositories.base import BaseRepository


class DocumentUploadRepository(BaseRepository[DocumentUpload]):
    """Репозиторий для работы с загрузками документов."""

    model = DocumentUpload

    async def get_by_user(self, user_id: int, limit: int = 50) -> list[DocumentUpload]:
        """Получить загрузки документов пользователя."""
        result = await self.session.execute(
            select(DocumentUpload)
            .where(DocumentUpload.user_id == user_id)
            .order_by(DocumentUpload.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_pending_processing(self, limit: int = 20) -> list[DocumentUpload]:
        """Получить документы, ожидающие обработки."""
        result = await self.session.execute(
            select(DocumentUpload)
            .where(DocumentUpload.validation_status == "pending")
            .order_by(DocumentUpload.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_processing(self, document_id: int) -> bool:
        """Отметить документ как обрабатываемый."""
        doc = await self.get_by_id(document_id)
        if doc is None:
            return False
        doc.validation_status = "processing"
        doc.processing_started_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(doc)
        return True

    async def mark_completed(self, document_id: int, score: float | None = None) -> bool:
        """Отметить документ как обработанный."""
        doc = await self.get_by_id(document_id)
        if doc is None:
            return False
        doc.validation_status = "completed"
        doc.completed_at = datetime.now(UTC)
        if score is not None:
            doc.image_quality_score = score
        await self.session.flush()
        await self.session.refresh(doc)
        return True

    async def mark_failed(self, document_id: int, error: str) -> bool:
        """Отметить документ как ошибочный."""
        doc = await self.get_by_id(document_id)
        if doc is None:
            return False
        doc.validation_status = "failed"
        doc.error_message = error
        await self.session.flush()
        await self.session.refresh(doc)
        return True

    async def get_stale_processing(self, hours: int = 2) -> list[DocumentUpload]:
        """Получить зависшие в обработке документы."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        result = await self.session.execute(
            select(DocumentUpload)
            .where(
                DocumentUpload.validation_status == "processing",
                DocumentUpload.processing_started_at < cutoff,
            )
        )
        return list(result.scalars().all())
