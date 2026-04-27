"""PlacementRequestRepository for PlacementRequest model operations."""

import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from src.db.models.placement_request import PlacementRequest, PlacementStatus
from src.db.repositories.base import BaseRepository


class PlacementRequestRepository(BaseRepository[PlacementRequest]):
    """Репозиторий для работы с заявками на размещение."""

    model = PlacementRequest

    async def create_placement(
        self,
        advertiser_id: int,
        channel_id: int,
        proposed_price: Decimal,
        final_text: str,
        proposed_schedule: datetime | None = None,
        proposed_frequency: int | None = None,
        campaign_id: int | None = None,
        is_test: bool = False,
        test_label: str | None = None,
        publication_format: str | None = None,
    ) -> PlacementRequest:
        """
        Создать новую заявку на размещение.

        Args:
            advertiser_id: ID рекламодателя.
            channel_id: ID канала.
            proposed_price: Предлагаемая цена.
            final_text: Текст рекламы.
            proposed_schedule: Желаемое время публикации.
            proposed_frequency: Частота (для пакетов).
            campaign_id: ID кампании.
            is_test: Флаг тестовой кампании.
            test_label: Пометка тестовой кампании.

        Returns:
            Созданная заявка.
        """
        from src.db.models.telegram_chat import TelegramChat

        # Get channel to get owner_id
        channel_result = await self.session.execute(
            select(TelegramChat).where(TelegramChat.id == channel_id)
        )
        channel = channel_result.scalar_one_or_none()
        if not channel:
            raise ValueError(f"Channel {channel_id} not found")

        from src.db.models.placement_request import PublicationFormat

        fmt = (
            PublicationFormat(publication_format)
            if publication_format
            else PublicationFormat.post_24h
        )

        from datetime import UTC, timedelta

        placement = PlacementRequest(
            advertiser_id=advertiser_id,
            owner_id=channel.owner_id,
            channel_id=channel_id,
            proposed_price=proposed_price,
            ad_text=final_text,
            proposed_schedule=proposed_schedule,
            is_test=is_test,
            test_label=test_label,
            publication_format=fmt,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )

        self.session.add(placement)
        await self.session.flush()
        await self.session.refresh(placement)
        # Explicitly set channel relationship so Pydantic can serialize PlacementResponse
        placement.channel = channel
        return placement

    async def get_by_advertiser(
        self, advertiser_id: int, statuses: list[PlacementStatus] | None = None
    ) -> list[PlacementRequest]:
        """Получить заявки рекламодателя."""

        conditions = [PlacementRequest.advertiser_id == advertiser_id]
        if statuses:
            conditions.append(PlacementRequest.status.in_(statuses))
        result = await self.session.execute(
            select(PlacementRequest)
            .options(selectinload(PlacementRequest.channel))
            .where(and_(*conditions))
            .order_by(PlacementRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_channel(
        self, channel_id: int, statuses: list[PlacementStatus] | None = None
    ) -> list[PlacementRequest]:
        """Получить заявки по ID канала."""
        conditions = [PlacementRequest.channel_id == channel_id]
        if statuses:
            conditions.append(PlacementRequest.status.in_(statuses))
        result = await self.session.execute(
            select(PlacementRequest)
            .where(and_(*conditions))
            .order_by(PlacementRequest.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_owner(
        self, owner_id: int, statuses: list[PlacementStatus] | None = None
    ) -> list[PlacementRequest]:
        """Получить заявки владельца канала."""
        from src.db.models.telegram_chat import TelegramChat

        conditions = [TelegramChat.owner_id == owner_id]
        if statuses:
            conditions.append(PlacementRequest.status.in_(statuses))
        result = await self.session.execute(
            select(PlacementRequest)
            .options(selectinload(PlacementRequest.channel))
            .join(TelegramChat, PlacementRequest.channel_id == TelegramChat.id)
            .where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def get_pending_for_owner(self, owner_id: int) -> list[PlacementRequest]:
        """Получить ожидающие заявки для владельца."""
        return await self.get_by_owner(
            owner_id, statuses=[PlacementStatus.pending_owner, PlacementStatus.counter_offer]
        )

    async def get_active_escrow(self) -> list[PlacementRequest]:
        """Получить активные заявки в эскроу."""
        result = await self.session.execute(
            select(PlacementRequest).where(PlacementRequest.status == PlacementStatus.escrow)
        )
        return list(result.scalars().all())

    async def get_published_active(self) -> list[PlacementRequest]:
        """Получить опубликованные активные заявки."""
        result = await self.session.execute(
            select(PlacementRequest).where(
                PlacementRequest.status == PlacementStatus.published,
                PlacementRequest.scheduled_delete_at > datetime.now(UTC),
            )
        )
        return list(result.scalars().all())

    async def count_active_for_advertiser(self, advertiser_id: int) -> int:
        """Посчитать активные заявки рекламодателя."""
        active_statuses = [
            PlacementStatus.pending_owner,
            PlacementStatus.counter_offer,
            PlacementStatus.pending_payment,
            PlacementStatus.escrow,
            PlacementStatus.published,
        ]
        result = await self.session.execute(
            select(func.count())
            .select_from(PlacementRequest)
            .where(
                PlacementRequest.advertiser_id == advertiser_id,
                PlacementRequest.status.in_(active_statuses),
            )
        )
        return result.scalar() or 0

    async def get_expired(self, before: datetime) -> list[PlacementRequest]:
        """Получить просроченные заявки."""
        result = await self.session.execute(
            select(PlacementRequest).where(
                PlacementRequest.status.in_([
                    PlacementStatus.pending_owner,
                    PlacementStatus.pending_payment,
                ]),
                PlacementRequest.expires_at < before,
            )
        )
        return list(result.scalars().all())

    async def count_cancellations_in_30_days(self, advertiser_id: int) -> int:
        """Количество отменённых заявок рекламодателя за последние 30 дней."""
        since = datetime.now(UTC) - timedelta(days=30)
        result = await self.session.execute(
            select(func.count())
            .select_from(PlacementRequest)
            .where(
                PlacementRequest.advertiser_id == advertiser_id,
                PlacementRequest.status == PlacementStatus.cancelled,
                PlacementRequest.updated_at >= since,
            )
        )
        return result.scalar() or 0

    async def set_message_id(
        self,
        session_or_none: object,
        placement_id: int,
        message_id: int,
        scheduled_delete_at: datetime,
    ) -> PlacementRequest | None:
        """Сохранить message_id и scheduled_delete_at после публикации."""
        placement = await self.get_by_id(placement_id)
        if not placement:
            return None
        placement.message_id = message_id
        placement.scheduled_delete_at = scheduled_delete_at
        if not placement.tracking_short_code:
            placement.tracking_short_code = secrets.token_urlsafe(8)[:16]
        await self.session.flush()
        return placement

    async def get_total_escrow_sum(self) -> Decimal:
        """Получить сумму final_price по активным PlacementRequest в статусе escrow."""
        result = await self.session.execute(
            select(func.coalesce(func.sum(PlacementRequest.final_price), Decimal("0"))).where(
                PlacementRequest.status == PlacementStatus.escrow
            )
        )
        return result.scalar_one() or Decimal("0")

    async def has_active_placements(self, channel_id: int) -> bool:
        """Проверить, есть ли у канала активные размещения (escrow/published)."""
        result = await self.session.execute(
            select(func.count())
            .select_from(PlacementRequest)
            .where(
                PlacementRequest.channel_id == channel_id,
                PlacementRequest.status.in_([PlacementStatus.escrow, PlacementStatus.published]),
            )
        )
        return (result.scalar_one() or 0) > 0

    async def count_published_by_channel(self, channel_id: int) -> int:
        """Посчитать количество опубликованных размещений канала."""
        result = await self.session.execute(
            select(func.count())
            .select_from(PlacementRequest)
            .where(
                PlacementRequest.channel_id == channel_id,
                PlacementRequest.status == PlacementStatus.published,
            )
        )
        return result.scalar_one() or 0

    async def get_frozen_for_advertiser(
        self, advertiser_id: int, limit: int = 50
    ) -> list[PlacementRequest]:
        """
        Получить placements рекламодателя в escrow/pending_payment для BalanceHero.

        Eager-loads `channel` для сериализации channel_title без N+1.
        """
        result = await self.session.execute(
            select(PlacementRequest)
            .options(selectinload(PlacementRequest.channel))
            .where(
                PlacementRequest.advertiser_id == advertiser_id,
                PlacementRequest.status.in_(
                    [PlacementStatus.escrow, PlacementStatus.pending_payment]
                ),
            )
            .order_by(PlacementRequest.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


# Алиас для обратной совместимости
PlacementRequestRepo = PlacementRequestRepository
