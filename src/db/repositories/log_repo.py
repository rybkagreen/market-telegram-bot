"""
Mailing Log Repository для работы с логами рассылок.
Расширяет BaseRepository специфичными методами для MailingLog.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Date, case, cast, func, select
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

    async def get_campaign_stats(
        self,
        campaign_id: int,
    ) -> dict[str, Any]:
        """
        Получить полную статистику кампании с охватом.

        Args:
            campaign_id: ID кампании.

        Returns:
            Словарь со статистикой включая reach_estimate.
        """
        # Базовая статистика
        base_stats = await self.get_stats_by_campaign(campaign_id)

        # Получаем оценку охвата (сумма member_count чатов)
        from src.db.models.chat import Chat

        reach_query = (
            select(func.coalesce(func.sum(Chat.member_count), 0))
            .select_from(
                MailingLog.__table__.join(Chat, MailingLog.chat_telegram_id == Chat.telegram_id)
            )
            .where(MailingLog.campaign_id == campaign_id)
        )

        result = await self.session.execute(reach_query)
        reach_estimate = result.scalar_one() or 0

        base_stats["reach_estimate"] = reach_estimate
        return base_stats

    async def get_top_chats(
        self,
        user_id: int | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Получить лучшие чаты по success rate.

        Args:
            user_id: ID пользователя (опционально).
            limit: Количество чатов.

        Returns:
            Список чатов со статистикой.
        """
        from src.db.models.campaign import Campaign
        from src.db.models.chat import Chat

        # Фильтр по пользователю
        filters = []
        if user_id is not None:
            filters.append(Campaign.user_id == user_id)

        query = (
            select(
                Chat.telegram_id.label("chat_telegram_id"),
                Chat.title.label("chat_title"),
                func.count(MailingLog.id).label("total_sent"),
                func.sum(case((MailingLog.status == MailingStatus.SENT, 1), else_=0)).label("sent"),
                func.avg(Chat.rating).label("avg_rating"),
            )
            .select_from(
                MailingLog.__table__.join(
                    Chat, MailingLog.chat_telegram_id == Chat.telegram_id
                ).join(Campaign, MailingLog.campaign_id == Campaign.id)
            )
            .where(*filters)
            .group_by(Chat.telegram_id, Chat.title, Chat.rating)
            .order_by(func.avg(Chat.rating).desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        rows = result.all()

        top_chats = []
        for row in rows:
            total = row.total_sent or 0
            sent = row.sent or 0
            success_rate = (sent / total * 100) if total > 0 else 0.0

            top_chats.append(
                {
                    "chat_telegram_id": row.chat_telegram_id,
                    "chat_title": row.chat_title or "",
                    "total_sent": total,
                    "success_rate": round(success_rate, 2),
                    "avg_rating": float(row.avg_rating or 0),
                }
            )

        return top_chats

    async def get_daily_stats(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """
        Получить ежедневную статистику.

        Args:
            user_id: ID пользователя.
            start_date: Начало периода.
            end_date: Конец периода.

        Returns:
            Список статистик по дням.
        """
        from src.db.models.campaign import Campaign

        query = (
            select(
                cast(MailingLog.sent_at, Date).label("date"),
                func.count(MailingLog.id).label("total"),
                func.sum(case((MailingLog.status == MailingStatus.SENT, 1), else_=0)).label("sent"),
                func.sum(case((MailingLog.status == MailingStatus.FAILED, 1), else_=0)).label(
                    "failed"
                ),
                func.coalesce(func.sum(MailingLog.cost), 0).label("total_cost"),
            )
            .select_from(MailingLog.__table__.join(Campaign, MailingLog.campaign_id == Campaign.id))
            .where(
                Campaign.user_id == user_id,
                MailingLog.sent_at >= start_date,
                MailingLog.sent_at <= end_date,
            )
            .group_by(cast(MailingLog.sent_at, Date))
            .order_by(cast(MailingLog.sent_at, Date).desc())
        )

        result = await self.session.execute(query)
        rows = result.all()

        daily_stats = []
        for row in rows:
            daily_stats.append(
                {
                    "date": str(row.date),
                    "total": row.total or 0,
                    "sent": row.sent or 0,
                    "failed": row.failed or 0,
                    "total_cost": float(row.total_cost or 0),
                }
            )

        return daily_stats
