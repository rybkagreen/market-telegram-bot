"""
Mailing Log Repository для работы с логами рассылок.
Расширяет BaseRepository специфичными методами для MailingLog.
"""

from dataclasses import dataclass
from datetime import UTC
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.mailing_log import MailingLog, MailingStatus
from src.db.repositories.base import BaseRepository


@dataclass
class LogData:
    """Data class для лога рассылки."""

    campaign_id: int
    chat_id: int | None
    chat_telegram_id: int
    status: MailingStatus
    error_msg: str | None = None
    message_id: int | None = None
    retry_count: int = 0
    cost: float = 0.0


class MailingLogRepository(BaseRepository[MailingLog]):
    """
    Репозиторий для работы с логами рассылок.

    Методы:
        bulk_insert: Пакетная вставка логов.
        get_stats_by_campaign: Получить статистику по кампании.
        get_by_campaign_and_chat: Получить лог по кампании и чату.
        update_status: Обновить статус лога.
        get_failed_logs: Получить неудачные логи.
        delete_old_logs: Удалить старые логи.
    """

    model = MailingLog

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        super().__init__(session)

    async def bulk_insert(
        self,
        logs_data: list[LogData],
        *,
        batch_size: int = 100,
    ) -> int:
        """
        Пакетная вставка логов рассылки.

        Args:
            logs_data: Список данных логов.
            batch_size: Размер батча для вставки.

        Returns:
            Количество вставленных логов.
        """
        if not logs_data:
            return 0

        from sqlalchemy.dialects.postgresql import insert

        inserted_count = 0

        # Разбиваем на батчи
        for i in range(0, len(logs_data), batch_size):
            batch = logs_data[i : i + batch_size]

            values_list = [
                {
                    "campaign_id": log.campaign_id,
                    "chat_id": log.chat_id,
                    "chat_telegram_id": log.chat_telegram_id,
                    "status": log.status.value,
                    "error_msg": log.error_msg,
                    "message_id": log.message_id,
                    "retry_count": log.retry_count,
                    "cost": log.cost,
                }
                for log in batch
            ]

            stmt = insert(MailingLog).values(values_list)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=[
                    MailingLog.campaign_id,
                    MailingLog.chat_telegram_id,
                ]
            )

            await self.session.execute(stmt)
            inserted_count += len(batch)

        await self.session.flush()
        return inserted_count

    async def get_stats_by_campaign(
        self,
        campaign_id: int,
    ) -> dict[str, Any]:
        """
        Получить статистику по кампании.

        Args:
            campaign_id: ID кампании.

        Returns:
            Словарь со статистикой.
        """
        query = select(
            func.count(MailingLog.id).label("total"),
            func.sum(case((MailingLog.status == MailingStatus.SENT, 1), else_=0)).label("sent"),
            func.sum(case((MailingLog.status == MailingStatus.FAILED, 1), else_=0)).label("failed"),
            func.sum(case((MailingLog.status == MailingStatus.SKIPPED, 1), else_=0)).label(
                "skipped"
            ),
            func.sum(case((MailingLog.status == MailingStatus.PENDING, 1), else_=0)).label(
                "pending"
            ),
            func.coalesce(func.sum(MailingLog.cost), 0).label("total_cost"),
        ).where(MailingLog.campaign_id == campaign_id)

        result = await self.session.execute(query)
        stats = result.one()

        total = stats.total or 0
        sent = stats.sent or 0
        failed = stats.failed or 0
        skipped = stats.skipped or 0
        pending = stats.pending or 0

        success_rate = (sent / total * 100) if total > 0 else 0.0

        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
            "pending": pending,
            "total_cost": float(stats.total_cost or 0),
            "success_rate": round(success_rate, 2),
        }

    async def get_by_campaign_and_chat(
        self,
        campaign_id: int,
        chat_telegram_id: int,
    ) -> MailingLog | None:
        """
        Получить лог по кампании и чату.

        Args:
            campaign_id: ID кампании.
            chat_telegram_id: Telegram ID чата.

        Returns:
            Лог или None.
        """
        return await self.find_one(
            MailingLog.campaign_id == campaign_id,
            MailingLog.chat_telegram_id == chat_telegram_id,
        )

    async def update_status(
        self,
        log_id: int,
        status: MailingStatus,
        error_msg: str | None = None,
        message_id: int | None = None,
    ) -> MailingLog | None:
        """
        Обновить статус лога.

        Args:
            log_id: ID лога.
            status: Новый статус.
            error_msg: Сообщение об ошибке.
            message_id: ID сообщения в Telegram.

        Returns:
            Обновленный лог или None.
        """
        update_data: dict[str, Any] = {"status": status}

        if error_msg is not None:
            update_data["error_msg"] = error_msg

        if message_id is not None:
            update_data["message_id"] = message_id

        await self.update(log_id, update_data)
        return await self.get_by_id(log_id)

    async def get_failed_logs(
        self,
        campaign_id: int | None = None,
        limit: int = 100,
    ) -> list[MailingLog]:
        """
        Получить неудачные логи.

        Args:
            campaign_id: ID кампании (опционально).
            limit: Максимальное количество результатов.

        Returns:
            Список логов.
        """
        filters = [MailingLog.status == MailingStatus.FAILED]

        if campaign_id is not None:
            filters.append(MailingLog.campaign_id == campaign_id)

        return await self.find_many(
            *filters,
            limit=limit,
            order_by=MailingLog.created_at.desc(),
        )

    async def delete_old_logs(
        self,
        days: int = 90,
    ) -> int:
        """
        Удалить старые логи.

        Args:
            days: Удалять логи старше этого количества дней.

        Returns:
            Количество удаленных логов.
        """
        from datetime import datetime, timedelta

        from sqlalchemy import delete

        cutoff_date = datetime.now(tz=UTC) - timedelta(days=days)

        stmt = delete(MailingLog).where(MailingLog.created_at < cutoff_date)
        result = await self.session.execute(stmt)
        await self.session.flush()

        return result.rowcount  # type: ignore

    async def get_logs_for_campaign(
        self,
        campaign_id: int,
        status: MailingStatus | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[MailingLog], int]:
        """
        Получить логи кампании с пагинацией.

        Args:
            campaign_id: ID кампании.
            status: Фильтр по статусу.
            page: Номер страницы.
            page_size: Размер страницы.

        Returns:
            Кортеж (список логов, общее количество).
        """
        filters = [MailingLog.campaign_id == campaign_id]

        if status is not None:
            filters.append(MailingLog.status == status)

        # Общее количество
        count_query = select(func.count(MailingLog.id)).where(*filters)
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Логи с пагинацией
        query = (
            select(MailingLog)
            .where(*filters)
            .order_by(MailingLog.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )

        result = await self.session.execute(query)
        logs = list(result.scalars().all())

        return logs, total

    async def get_chat_statistics(
        self,
        chat_telegram_id: int,
    ) -> dict[str, Any]:
        """
        Получить статистику по чату.

        Args:
            chat_telegram_id: Telegram ID чата.

        Returns:
            Словарь со статистикой.
        """
        query = select(
            func.count(MailingLog.id).label("total"),
            func.sum(case((MailingLog.status == MailingStatus.SENT, 1), else_=0)).label("sent"),
            func.sum(case((MailingLog.status == MailingStatus.FAILED, 1), else_=0)).label("failed"),
            func.avg(MailingLog.cost).label("avg_cost"),
        ).where(MailingLog.chat_telegram_id == chat_telegram_id)

        result = await self.session.execute(query)
        stats = result.one()

        total = stats.total or 0
        sent = stats.sent or 0
        failed = stats.failed or 0

        success_rate = (sent / total * 100) if total > 0 else 0.0

        return {
            "total": total,
            "sent": sent,
            "failed": failed,
            "success_rate": round(success_rate, 2),
            "avg_cost": float(stats.avg_cost or 0),
        }
