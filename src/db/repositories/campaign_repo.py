"""
Campaign Repository для работы с рекламными кампаниями.
Расширяет BaseRepository специфичными методами для Campaign.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Select, and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models.campaign import Campaign, CampaignStatus
from src.db.repositories.base import BaseRepository


class CampaignRepository(BaseRepository[Campaign]):
    """
    Репозиторий для работы с рекламными кампаниями.

    Методы:
        get_by_user: Получить кампании пользователя.
        update_status: Обновить статус кампании.
        get_scheduled_due: Получить запланированные кампании для запуска.
        get_running_campaigns: Получить активные кампании.
        get_with_stats: Получить кампанию со статистикой.
        create_with_content_flag: Создать кампанию с флагом контента.
    """

    model = Campaign

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        super().__init__(session)

    async def get_by_user(
        self,
        user_id: int,
        status: CampaignStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Campaign], int]:
        """
        Получить кампании пользователя с пагинацией.

        Args:
            user_id: ID пользователя.
            status: Фильтр по статусу (опционально).
            page: Номер страницы.
            page_size: Размер страницы.

        Returns:
            Кортеж (список кампаний, общее количество).
        """
        filters = [Campaign.user_id == user_id]
        if status is not None:
            filters.append(Campaign.status == status)

        total_query = select(func.count(Campaign.id)).where(*filters)
        total_result = await self.session.execute(total_query)
        total = total_result.scalar_one()

        query: Select[tuple[Campaign]] = (
            select(Campaign)
            .where(*filters)
            .order_by(Campaign.created_at.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
            .options(selectinload(Campaign.mailing_logs))
        )
        result = await self.session.execute(query)
        campaigns = list(result.scalars().all())

        return campaigns, total

    async def update_status(
        self,
        campaign_id: int,
        status: CampaignStatus,
        error_message: str | None = None,
    ) -> Campaign | None:
        """
        Обновить статус кампании.

        Args:
            campaign_id: ID кампании.
            status: Новый статус.
            error_message: Сообщение об ошибке (для статуса error).

        Returns:
            Обновленная кампания или None.
        """
        # ✅ БЛОКИРОВКА СТРОКИ для предотвращения race condition
        from sqlalchemy import select

        stmt = select(Campaign).where(Campaign.id == campaign_id).with_for_update()
        result = await self.session.execute(stmt)
        campaign = result.scalar_one_or_none()

        if campaign is None:
            return None

        update_data: dict[str, Any] = {"status": status}

        if status == CampaignStatus.RUNNING and campaign.started_at is None:
            update_data["started_at"] = datetime.now(tz=UTC)

        if status in (CampaignStatus.DONE, CampaignStatus.ERROR, CampaignStatus.CANCELLED):
            update_data["completed_at"] = datetime.now(tz=UTC)

        if error_message is not None:
            update_data["error_message"] = error_message

        await self.update(campaign_id, update_data)
        await self.refresh(campaign)

        return campaign

    async def get_scheduled_due(self, now: datetime | None = None) -> list[Campaign]:
        """
        Получить кампании, готовые к запуску по расписанию.

        Возвращает кампании со статусом queued, у которых
        scheduled_at <= now.

        Args:
            now: Текущее время (по умолчанию UTC now).

        Returns:
            Список кампаний для запуска.
        """
        if now is None:
            now = datetime.now(tz=UTC)

        query = select(Campaign).where(
            and_(
                Campaign.status == CampaignStatus.QUEUED,
                Campaign.scheduled_at <= now,
                Campaign.scheduled_at.isnot(None),
            )
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_running_campaigns(self) -> list[Campaign]:
        """
        Получить все активные кампании.

        Returns:
            Список активных кампаний.
        """
        query = select(Campaign).where(Campaign.status == CampaignStatus.RUNNING)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_with_stats(self, campaign_id: int) -> dict[str, Any] | None:
        """
        Получить кампанию со статистикой рассылки.

        Args:
            campaign_id: ID кампании.

        Returns:
            Словарь с кампанией и статистикой или None.
        """
        campaign = await self.get_by_id(campaign_id)
        if campaign is None:
            return None

        from src.db.models.mailing_log import MailingLog, MailingStatus

        stats_query = select(
            func.count(MailingLog.id).label("total"),
            func.sum(case((MailingLog.status == MailingStatus.SENT, 1), else_=0)).label("sent"),
            func.sum(case((MailingLog.status == MailingStatus.FAILED, 1), else_=0)).label("failed"),
            func.sum(case((MailingLog.status == MailingStatus.SKIPPED, 1), else_=0)).label(
                "skipped"
            ),
        ).where(MailingLog.campaign_id == campaign_id)

        result = await self.session.execute(stats_query)
        stats = result.one()

        return {
            "campaign": campaign,
            "total": stats.total or 0,
            "sent": stats.sent or 0,
            "failed": stats.failed or 0,
            "skipped": stats.skipped or 0,
        }

    async def create_with_content_flag(
        self,
        user_id: int,
        title: str,
        text: str,
        ai_description: str | None = None,
        filters_json: dict[str, Any] | None = None,
        scheduled_at: datetime | None = None,
    ) -> Campaign:
        """
        Создать кампанию с автоматической установкой статуса.

        Если есть scheduled_at — статус queued, иначе draft.

        Args:
            user_id: ID пользователя.
            title: Заголовок кампании.
            text: Текст рекламного сообщения.
            ai_description: Описание для ИИ.
            filters_json: Фильтры таргетинга.
            scheduled_at: Время запуска.

        Returns:
            Созданная кампания.
        """
        status = CampaignStatus.QUEUED if scheduled_at else CampaignStatus.DRAFT

        return await self.create(
            {
                "user_id": user_id,
                "title": title,
                "text": text,
                "ai_description": ai_description,
                "status": status,
                "filters_json": filters_json,
                "scheduled_at": scheduled_at,
            }
        )

    async def get_user_campaigns_count(
        self,
        user_id: int,
        status: CampaignStatus | None = None,
    ) -> int:
        """
        Получить количество кампаний пользователя.

        Args:
            user_id: ID пользователя.
            status: Фильтр по статусу.

        Returns:
            Количество кампаний.
        """
        from sqlalchemy import and_

        filters = [Campaign.user_id == user_id]
        if status is not None:
            filters.append(Campaign.status == status)
        return await self.count(and_(*filters))

    async def get_campaigns_for_period(
        self,
        user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> list[Campaign]:
        """
        Получить кампании пользователя за период.

        Args:
            user_id: ID пользователя.
            start_date: Начало периода.
            end_date: Конец периода.

        Returns:
            Список кампаний.
        """
        return await self.find_many(
            Campaign.user_id == user_id,
            Campaign.created_at >= start_date,
            Campaign.created_at <= end_date,
            order_by=Campaign.created_at.desc(),
        )

    def get_query_with_logs(self) -> Select[tuple[Campaign]]:
        """
        Получить query с подгрузкой mailing_logs.

        Returns:
            SQLAlchemy Select query.
        """
        return select(self.model).options(selectinload(Campaign.mailing_logs))

    async def update_statistics(
        self,
        campaign_id: int,
        sent_count: int | None = None,
        failed_count: int | None = None,
        skipped_count: int | None = None,
        total_chats: int | None = None,
    ) -> Campaign | None:
        """
        Обновить статистику кампании.

        Args:
            campaign_id: ID кампании.
            sent_count: Количество отправленных.
            failed_count: Количество неудачных.
            skipped_count: Количество пропущенных.
            total_chats: Общее количество чатов.

        Returns:
            Обновленная кампания или None.
        """
        campaign = await self.get_by_id(campaign_id)
        if campaign is None:
            return None

        update_data: dict[str, Any] = {}
        if sent_count is not None:
            update_data["sent_count"] = sent_count
        if failed_count is not None:
            update_data["failed_count"] = failed_count
        if skipped_count is not None:
            update_data["skipped_count"] = skipped_count
        if total_chats is not None:
            update_data["total_chats"] = total_chats

        await self.update(campaign_id, update_data)
        await self.refresh(campaign)

        return campaign

    async def count_by_status(self, status: CampaignStatus) -> int:
        """
        Количество кампаний в статусе.

        Args:
            status: Статус кампании.

        Returns:
            Количество кампаний.
        """
        stmt = select(func.count(Campaign.id)).where(Campaign.status == status)
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def count_done_today(self) -> int:
        """
        Количество завершённых кампаний за последние 24 часа.

        Returns:
            Количество кампаний.
        """
        since = datetime.now(tz=UTC) - timedelta(hours=24)
        stmt = select(func.count(Campaign.id)).where(
            Campaign.status == CampaignStatus.DONE,
            Campaign.completed_at >= since,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() or 0

    async def get_by_status(
        self,
        status: CampaignStatus,
        limit: int = 20,
    ) -> list[Campaign]:
        """
        Список кампаний в статусе, свежие первые.

        Args:
            status: Статус кампании.
            limit: Максимальное количество.

        Returns:
            Список кампаний.
        """
        stmt = (
            select(Campaign)
            .where(Campaign.status == status)
            .order_by(Campaign.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def has_campaigns(self, user_id: int) -> bool:
        """
        Проверить наличие кампаний у пользователя.

        Args:
            user_id: ID пользователя в БД.

        Returns:
            True если у пользователя есть хотя бы одна кампания.
        """
        return await self.exists(Campaign.user_id == user_id)
