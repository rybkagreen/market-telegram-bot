"""
PlacementRequest Repository для работы с заявками на размещение.
Расширяет BaseRepository специфичными методами для PlacementRequest.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.repositories.base import BaseRepository


class PlacementRequestRepo(BaseRepository[PlacementRequest]):
    """
    Репозиторий для работы с заявками на размещение.
    """

    model = PlacementRequest

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        super().__init__(session)

    async def create(
        self,
        advertiser_id: int,
        campaign_id: int,
        channel_id: int,
        proposed_price: Decimal,
        final_text: str,
        proposed_schedule: datetime | None = None,
        proposed_frequency: int | None = None,
    ) -> PlacementRequest:
        """
        Создать заявку. expires_at = now() + 24h. status = pending_owner.

        Args:
            advertiser_id: ID рекламодателя.
            campaign_id: ID кампании.
            channel_id: ID канала.
            proposed_price: Предлагаемая цена.
            final_text: Финальный текст рекламы.
            proposed_schedule: Желаемое время публикации.
            proposed_frequency: Частота (для пакетов).

        Returns:
            Созданная заявка.
        """
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=24)

        attributes = {
            "advertiser_id": advertiser_id,
            "campaign_id": campaign_id,
            "channel_id": channel_id,
            "proposed_price": proposed_price,
            "final_text": final_text,
            "proposed_schedule": proposed_schedule,
            "proposed_frequency": proposed_frequency,
            "status": PlacementStatus.PENDING_OWNER,
            "counter_offer_count": 0,
            "expires_at": expires_at,
            "created_at": now,
            "updated_at": now,
        }

        return await super().create(attributes)

    async def get_by_advertiser(
        self,
        advertiser_id: int,
        status: PlacementStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[PlacementRequest]:
        """
        Список заявок рекламодателя, опционально фильтр по статусу.

        Args:
            advertiser_id: ID рекламодателя.
            status: Фильтр по статусу.
            limit: Максимальное количество записей.
            offset: Смещение.

        Returns:
            Список заявок.
        """
        filters = [PlacementRequest.advertiser_id == advertiser_id]
        if status is not None:
            filters.append(PlacementRequest.status == status)

        query = (
            select(PlacementRequest)
            .where(*filters)
            .order_by(PlacementRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(PlacementRequest.campaign))
            .options(selectinload(PlacementRequest.channel))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_channel(
        self,
        channel_id: int,
        status: PlacementStatus | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[PlacementRequest]:
        """
        Список заявок для канала (для владельца).

        Args:
            channel_id: ID канала.
            status: Фильтр по статусу.
            limit: Максимальное количество записей.
            offset: Смещение.

        Returns:
            Список заявок.
        """
        filters = [PlacementRequest.channel_id == channel_id]
        if status is not None:
            filters.append(PlacementRequest.status == status)

        query = (
            select(PlacementRequest)
            .where(*filters)
            .order_by(PlacementRequest.created_at.desc())
            .limit(limit)
            .offset(offset)
            .options(selectinload(PlacementRequest.campaign))
            .options(selectinload(PlacementRequest.advertiser))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_pending_for_owner(
        self, owner_id: int
    ) -> list[PlacementRequest]:
        """
        Все заявки со статусом pending_owner для всех каналов владельца.
        JOIN с telegram_chats по owner_id.

        Args:
            owner_id: ID владельца канала.

        Returns:
            Список заявок.
        """
        from src.db.models.analytics import TelegramChat

        query = (
            select(PlacementRequest)
            .join(TelegramChat, PlacementRequest.channel_id == TelegramChat.id)
            .where(
                TelegramChat.owner_user_id == owner_id,
                PlacementRequest.status == PlacementStatus.PENDING_OWNER,
            )
            .order_by(PlacementRequest.created_at.desc())
            .options(selectinload(PlacementRequest.campaign))
            .options(selectinload(PlacementRequest.advertiser))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_expired(self) -> list[PlacementRequest]:
        """
        Заявки с expires_at < now() и статусом pending_owner или counter_offer.
        Используется Celery-задачей для авто-отклонения.

        Returns:
            Список просроченных заявок.
        """
        now = datetime.now(UTC)
        query = (
            select(PlacementRequest)
            .where(
                PlacementRequest.expires_at < now,
                PlacementRequest.status.in_(
                    [PlacementStatus.PENDING_OWNER, PlacementStatus.COUNTER_OFFER]
                ),
            )
            .options(selectinload(PlacementRequest.campaign))
            .options(selectinload(PlacementRequest.channel))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_expired_pending_owner(self) -> list[PlacementRequest]:
        """
        Заявки со статусом pending_owner и expires_at < now().

        Returns:
            Список просроченных заявок.
        """
        now = datetime.now(UTC)
        query = (
            select(PlacementRequest)
            .where(
                PlacementRequest.status == PlacementStatus.PENDING_OWNER,
                PlacementRequest.expires_at < now,
            )
            .options(selectinload(PlacementRequest.channel))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_expired_pending_payment(self) -> list[PlacementRequest]:
        """
        Заявки со статусом pending_payment и expires_at < now().

        Returns:
            Список просроченных заявок.
        """
        now = datetime.now(UTC)
        query = (
            select(PlacementRequest)
            .where(
                PlacementRequest.status == PlacementStatus.PENDING_PAYMENT,
                PlacementRequest.expires_at < now,
            )
            .options(selectinload(PlacementRequest.channel))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_expired_counter_offer(self) -> list[PlacementRequest]:
        """
        Заявки со статусом counter_offer и expires_at < now().

        Returns:
            Список просроченных заявок.
        """
        now = datetime.now(UTC)
        query = (
            select(PlacementRequest)
            .where(
                PlacementRequest.status == PlacementStatus.COUNTER_OFFER,
                PlacementRequest.expires_at < now,
            )
            .options(selectinload(PlacementRequest.channel))
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update_status(
        self,
        placement_id: int,
        status: PlacementStatus,
        rejection_reason: str | None = None,
    ) -> PlacementRequest | None:
        """
        Обновить статус. Обновить updated_at.

        Args:
            placement_id: ID заявки.
            status: Новый статус.
            rejection_reason: Причина отклонения.

        Returns:
            Обновленная заявка или None.
        """
        instance = await self.get_by_id(placement_id)
        if instance is None:
            return None

        instance.status = status
        instance.updated_at = datetime.now(UTC)
        if rejection_reason is not None:
            instance.rejection_reason = rejection_reason

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def accept(
        self,
        placement_id: int,
        final_price: Decimal | None = None,
        final_schedule: datetime | None = None,
    ) -> PlacementRequest | None:
        """
        Владелец принял заявку. status → pending_payment.
        Если final_price/final_schedule не переданы — копировать из proposed_*.

        Args:
            placement_id: ID заявки.
            final_price: Итоговая цена.
            final_schedule: Итоговое время публикации.

        Returns:
            Обновленная заявка или None.
        """
        instance = await self.get_by_id(placement_id)
        if instance is None:
            return None

        instance.status = PlacementStatus.PENDING_PAYMENT
        instance.final_price = final_price or instance.proposed_price
        instance.final_schedule = final_schedule or instance.proposed_schedule
        instance.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def reject(
        self,
        placement_id: int,
        rejection_reason: str,
    ) -> PlacementRequest | None:
        """
        Владелец отклонил заявку. status → cancelled. Сохранить rejection_reason.

        Args:
            placement_id: ID заявки.
            rejection_reason: Причина отклонения.

        Returns:
            Обновленная заявка или None.
        """
        instance = await self.get_by_id(placement_id)
        if instance is None:
            return None

        instance.status = PlacementStatus.CANCELLED
        instance.rejection_reason = rejection_reason
        instance.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def counter_offer(
        self,
        placement_id: int,
        proposed_price: Decimal | None = None,
        proposed_schedule: datetime | None = None,
    ) -> PlacementRequest | None:
        """
        Контр-предложение. status → counter_offer.
        counter_offer_count += 1. last_counter_at = now().
        Обновить expires_at = now() + 24h для нового раунда.
        Если counter_offer_count >= 3 после инкремента — вернуть None (исчерпан лимит).

        Args:
            placement_id: ID заявки.
            proposed_price: Новая цена.
            proposed_schedule: Новое время публикации.

        Returns:
            Обновленная заявка или None если лимит исчерпан.
        """
        instance = await self.get_by_id(placement_id)
        if instance is None:
            return None

        # Инкремент счётчика
        instance.counter_offer_count += 1

        # Проверка лимита
        if instance.counter_offer_count >= 3:
            return None

        instance.status = PlacementStatus.COUNTER_OFFER
        instance.last_counter_at = datetime.now(UTC)
        instance.expires_at = datetime.now(UTC) + timedelta(hours=24)

        if proposed_price is not None:
            instance.proposed_price = proposed_price
        if proposed_schedule is not None:
            instance.proposed_schedule = proposed_schedule

        instance.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def set_escrow(
        self,
        placement_id: int,
        escrow_transaction_id: int,
    ) -> PlacementRequest | None:
        """
        status → escrow. Сохранить escrow_transaction_id.

        Args:
            placement_id: ID заявки.
            escrow_transaction_id: ID транзакции эскроу.

        Returns:
            Обновленная заявка или None.
        """
        instance = await self.get_by_id(placement_id)
        if instance is None:
            return None

        instance.status = PlacementStatus.ESCROW
        instance.escrow_transaction_id = escrow_transaction_id
        instance.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def set_published(
        self,
        placement_id: int,
        published_at: datetime | None = None,
    ) -> PlacementRequest | None:
        """
        status → published. published_at = now() если не передан.

        Args:
            placement_id: ID заявки.
            published_at: Время публикации.

        Returns:
            Обновленная заявка или None.
        """
        instance = await self.get_by_id(placement_id)
        if instance is None:
            return None

        instance.status = PlacementStatus.PUBLISHED
        instance.published_at = published_at or datetime.now(UTC)
        instance.updated_at = datetime.now(UTC)

        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def count_pending_for_owner(self, owner_id: int) -> int:
        """
        Количество pending_owner заявок для owner. Для счётчика в меню.

        Args:
            owner_id: ID владельца канала.

        Returns:
            Количество заявок.
        """
        from src.db.models.analytics import TelegramChat

        query = (
            select(func.count(PlacementRequest.id))
            .join(TelegramChat, PlacementRequest.channel_id == TelegramChat.id)
            .where(
                TelegramChat.owner_user_id == owner_id,
                PlacementRequest.status == PlacementStatus.PENDING_OWNER,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def count_cancellations_in_30_days(
        self, advertiser_id: int
    ) -> int:
        """
        Количество cancelled заявок advertiser_id за последние 30 дней.
        Используется ReputationService для правила '3 отмены за 30 дней'.

        Args:
            advertiser_id: ID рекламодателя.

        Returns:
            Количество отмен.
        """
        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

        query = (
            select(func.count(PlacementRequest.id))
            .where(
                PlacementRequest.advertiser_id == advertiser_id,
                PlacementRequest.status == PlacementStatus.CANCELLED,
                PlacementRequest.updated_at >= thirty_days_ago,
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one() or 0
