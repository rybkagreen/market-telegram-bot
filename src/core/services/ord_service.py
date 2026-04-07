"""
OrdService — регистрация рекламных материалов в ОРД.
Delegates to an OrdProvider implementation (default: StubOrdProvider).

S-28 Phase 2: register_creative orchestrates the full flow:
  1. Load PlacementRequest with channel + advertiser
  2. Load LegalProfile for advertiser (inn, legal_status)
  3. register_advertiser → get advertiser_ord_id
  4. register_platform → get platform_ord_id
  5. register_contract → get contract_ord_id
  6. register_creative → get erid (token) + request_id
  7. Save OrdRegistration with all ORD IDs
  8. Dispatch Celery task poll_erid_status
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import insert, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.settings import settings
from src.core.services.ord_provider import OrdProvider
from src.core.services.stub_ord_provider import StubOrdProvider
from src.db.models.legal_profile import LegalProfile
from src.db.models.ord_registration import OrdRegistration
from src.db.models.placement_request import PlacementRequest
from src.db.repositories.ord_registration_repo import OrdRegistrationRepo

logger = logging.getLogger(__name__)

# ─── Module-level global provider (injected at startup) ────────

_global_provider: OrdProvider = StubOrdProvider()


class OrdService:
    """Сервис для регистрации рекламных материалов в ОРД."""

    def __init__(self, session: AsyncSession, provider: OrdProvider | None = None) -> None:
        self.session = session
        self._provider: OrdProvider = provider or StubOrdProvider()
        if isinstance(self._provider, StubOrdProvider):
            logger.warning("OrdService: используется stub-провайдер (ORD_PROVIDER не настроен)")

    # ─── Provider injection ────────────────────────────────────

    @staticmethod
    def get_default_provider() -> OrdProvider:
        """Get the globally configured ORD provider (set at startup)."""
        return _global_provider

    @staticmethod
    def set_default_provider(provider: OrdProvider) -> None:
        """Set the global ORD provider (called at startup)."""
        global _global_provider
        _global_provider = provider
        logger.info("OrdService: global ORD provider set to %s", type(provider).__name__)

    # ─── Business methods ──────────────────────────────────────

    async def register_advertiser(
        self, user_id: int, name: str = "", inn: str | None = None
    ) -> str:
        """Зарегистрировать рекламодателя в ОРД."""
        return await self._provider.register_advertiser(user_id, name, inn)

    async def register_creative(
        self,
        placement_request_id: int,
        ad_text: str,
        media_type: str,
    ) -> OrdRegistration:
        """
        Полная оркестрация регистрации креатива в ОРД:
        1. Загрузить PlacementRequest с channel и advertiser
        2. Загрузить LegalProfile рекламодателя
        3. register_advertiser → advertiser_ord_id
        4. register_platform → platform_ord_id
        5. register_contract → contract_ord_id
        6. register_creative → erid (token) + request_id
        7. Сохранить OrdRegistration
        8. Запустить Celery task poll_erid_status
        """
        repo = OrdRegistrationRepo(self.session)
        existing = await repo.get_by_placement(placement_request_id)
        if existing:
            return existing

        # 1. Загрузить PlacementRequest с связанными данными
        stmt = (
            select(PlacementRequest)
            .where(PlacementRequest.id == placement_request_id)
            .options(
                selectinload(PlacementRequest.channel),
                selectinload(PlacementRequest.advertiser),
            )
        )
        result = await self.session.execute(stmt)
        placement = result.scalar_one_or_none()
        if not placement:
            raise ValueError(f"PlacementRequest #{placement_request_id} not found")

        # 2. LegalProfile рекламодателя
        lp_stmt = select(LegalProfile).where(LegalProfile.user_id == placement.advertiser_id)
        lp_result = await self.session.execute(lp_stmt)
        legal_profile = lp_result.scalar_one_or_none()

        inn = legal_profile.inn if legal_profile else None
        name = ""
        if legal_profile:
            name = legal_profile.legal_name or ""

        # 3. register_advertiser
        advertiser_ord_id = await self._provider.register_advertiser(
            user_id=placement.advertiser_id,
            name=name,
            inn=inn,
        )

        # 4. register_platform
        channel = placement.channel
        channel_url = f"https://t.me/{channel.username}" if channel.username else ""
        channel_name = channel.title or channel.username or str(channel.telegram_id)

        platform_ord_id = await self._provider.register_platform(
            channel_id=channel.id,
            channel_url=channel_url,
            channel_name=channel_name,
        )

        # 5. register_contract
        amount = placement.final_price or placement.proposed_price
        amount_rub = str(float(amount))
        pub_date = (placement.final_schedule or datetime.now(UTC)).date().isoformat()

        contract_ord_id = await self._provider.register_contract(
            placement_request_id=placement_request_id,
            advertiser_ord_id=advertiser_ord_id,
            amount_rub=amount_rub,
            date_str=pub_date,
        )

        # 6. register_creative → erid (token)
        erid = await self._provider.register_creative(
            placement_request_id=placement_request_id,
            ad_text=ad_text,
            media_type=media_type,
            advertiser_ord_id=advertiser_ord_id,
        )

        # 7. Save OrdRegistration
        now = datetime.now(UTC)
        insert_stmt = (
            insert(OrdRegistration)
            .values(
                placement_request_id=placement_request_id,
                status="token_received",
                erid=erid,
                ord_provider=settings.ord_provider,
                advertiser_ord_id=advertiser_ord_id,
                platform_ord_id=platform_ord_id,
                contract_ord_id=contract_ord_id,
                token_received_at=now,
            )
            .returning(OrdRegistration)
        )
        result = await self.session.execute(insert_stmt)
        registration: OrdRegistration = result.scalar_one()

        # Обновить erid в PlacementRequest
        await self.session.execute(
            sa_update(PlacementRequest)
            .where(PlacementRequest.id == placement_request_id)
            .values(erid=erid)
        )
        await self.session.flush()
        await self.session.refresh(registration)

        # 8. Dispatch Celery polling task (только для не-stub провайдера)
        if not isinstance(self._provider, StubOrdProvider):
            try:
                from src.tasks.ord_tasks import poll_erid_status

                poll_erid_status.apply_async(args=[registration.id], countdown=60)
                logger.info(
                    "ORD: dispatched poll_erid_status for registration %s",
                    registration.id,
                )
            except Exception as e:
                logger.warning(
                    "ORD: failed to dispatch poll_erid_status: %s",
                    e,
                    exc_info=True,
                )

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

    async def poll_erid_status_by_request_id(self, yandex_request_id: str) -> str:
        """Poll /status endpoint by yandex_request_id. Returns status string."""
        if isinstance(self._provider, StubOrdProvider):
            return "stub"
        return await self._provider.get_status(yandex_request_id)


# ─── Factory function ──────────────────────────────────────────


def get_ord_service(session: AsyncSession) -> OrdService:
    """Factory: создать OrdService с глобальным провайдером."""
    return OrdService(session, provider=_global_provider)
