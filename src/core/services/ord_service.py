"""
OrdService — регистрация рекламных материалов в ОРД.
Delegates to an OrdProvider implementation (default: StubOrdProvider).
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.ord_provider import OrdProvider
from src.core.services.stub_ord_provider import StubOrdProvider
from src.db.models.ord_registration import OrdRegistration
from src.db.models.placement_request import PlacementRequest
from src.db.repositories.ord_registration_repo import OrdRegistrationRepo

logger = logging.getLogger(__name__)


class OrdService:
    """Сервис для регистрации рекламных материалов в ОРД."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._provider: OrdProvider = StubOrdProvider()
        if isinstance(self._provider, StubOrdProvider):
            logger.warning("OrdService: используется stub-провайдер")

    def set_provider(self, provider: OrdProvider) -> None:
        """Inject a real ORD provider (called at startup when ORD_PROVIDER != 'stub')."""
        self._provider = provider

    async def register_advertiser(self, user_id: int, name: str = "", inn: str | None = None) -> str:
        """Зарегистрировать рекламодателя в ОРД."""
        return await self._provider.register_advertiser(user_id, name, inn)

    async def register_creative(
        self, placement_request_id: int, ad_text: str, media_type: str
    ) -> OrdRegistration:
        """
        Зарегистрировать рекламный материал (креатив) в ОРД и получить erid.
        Saves erid to OrdRegistration and PlacementRequest.
        """
        repo = OrdRegistrationRepo(self.session)
        existing = await repo.get_by_placement(placement_request_id)
        if existing:
            return existing

        erid = await self._provider.register_creative(
            placement_request_id=placement_request_id,
            ad_text=ad_text,
            media_type=media_type,
            advertiser_ord_id="stub",
        )

        now = datetime.now(UTC)
        from sqlalchemy import insert

        result = await self.session.execute(
            insert(OrdRegistration)
            .values(
                placement_request_id=placement_request_id,
                status="token_received",
                erid=erid,
                ord_provider="stub",
                token_received_at=now,
            )
            .returning(OrdRegistration)
        )
        registration = result.scalar_one()

        await self.session.execute(
            sa_update(PlacementRequest)
            .where(PlacementRequest.id == placement_request_id)
            .values(erid=erid)
        )
        await self.session.flush()
        return registration

    async def get_erid(self, placement_request_id: int) -> str | None:
        """Получить erid для размещения."""
        return await OrdRegistrationRepo(self.session).get_erid(placement_request_id)

    async def report_publication(
        self,
        placement_request_id: int,
        channel_id: int,
        published_at: datetime,
        post_url: str,
    ) -> None:
        """Сообщить в ОРД о факте публикации."""
        repo = OrdRegistrationRepo(self.session)
        registration = await repo.get_by_placement(placement_request_id)
        if not registration or not registration.erid:
            return
        await self._provider.report_publication(
            erid=registration.erid,
            published_at=published_at,
            placement_request_id=placement_request_id,
        )
        await repo.update_status(registration.id, "reported", reported_at=published_at)

    async def get_status(self, placement_request_id: int) -> OrdRegistration | None:
        """Получить статус регистрации в ОРД."""
        return await OrdRegistrationRepo(self.session).get_by_placement(placement_request_id)
