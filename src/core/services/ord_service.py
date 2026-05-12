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
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.settings import settings
from src.core.services.ord_provider import OrdProvider
from src.core.services.stub_ord_provider import StubOrdProvider
from src.core.services.yandex_ord_provider import YandexOrdProvider
from src.db.models.legal_profile import LegalProfile
from src.db.models.ord_audit_log import OrdAuditEventType
from src.db.models.ord_registration import OrdRegistration, OrdRegistrationStatus
from src.db.models.placement_request import PlacementRequest
from src.db.repositories.ord_audit_log_repo import OrdAuditLogRepo
from src.db.repositories.ord_registration_repo import OrdRegistrationRepo

logger = logging.getLogger(__name__)

# ─── DI factory for ORD provider (lazy singleton) ────────────────
#
# Pattern mirrors src/api/dependencies.py:get_bot — the provider is built on
# first access, not at module import. This avoids two failure modes that the
# previous module-state singleton suffered from:
#   • pytest collection crashing when ORD_PROVIDER=yandex but no keys set
#   • Celery workers pre-fork import order picking the wrong provider class
# Worker processes pre-warm the cache via worker_process_init signal.

_provider_singleton: OrdProvider | None = None


def _build_ord_provider_from_settings() -> OrdProvider:
    if settings.ord_provider == "yandex":
        if not settings.ord_api_key or not settings.ord_api_url:
            raise RuntimeError("ORD_PROVIDER=yandex, but ORD_API_KEY or ORD_API_URL not set")
        return YandexOrdProvider(
            api_key=settings.ord_api_key,
            base_url=settings.ord_api_url,
            rekharbor_org_id=settings.ord_rekharbor_org_id,
            rekharbor_inn=settings.ord_rekharbor_inn,
        )
    return StubOrdProvider()


def get_ord_provider() -> OrdProvider:
    """Return the process-wide ORD provider, constructing it on first access."""
    global _provider_singleton
    if _provider_singleton is None:
        _provider_singleton = _build_ord_provider_from_settings()
    return _provider_singleton


class OrdService:
    """Сервис для регистрации рекламных материалов в ОРД."""

    def __init__(self, session: AsyncSession, provider: OrdProvider | None = None) -> None:
        self.session = session
        self._provider: OrdProvider = provider or StubOrdProvider()
        if isinstance(self._provider, StubOrdProvider):
            logger.warning("OrdService: используется stub-провайдер (ORD_PROVIDER не настроен)")

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
        """Orchestrate full ORD registration for a placement.

        BL-080 8c reordering: the OrdRegistration row is INSERTed in `pending`
        state с a fresh correlation_id BEFORE any provider call. Subsequent
        provider calls and state updates are audited через OrdAuditLogRepo
        (SAVEPOINT-wrapped, fire-and-forget). On retry the EXISTS-check on
        placement_request_id UNIQUE short-circuits к the existing row.

        Steps:
          1. EXISTS check (returns existing registration if already created).
          2. Load PlacementRequest + LegalProfile.
          3. INSERT OrdRegistration{status=pending, correlation_id=uuid}.
          4. Audit: state_transition → pending.
          5. Provider calls (advertiser → platform → contract → creative);
             each audited with provider_request / provider_response events.
          6. UPDATE OrdRegistration с erid + ord ids + status=token_received.
          7. Audit: state_transition pending → token_received.
          8. UPDATE PlacementRequest.erid.
          9. Dispatch poll_erid_status Celery task (non-stub providers only).
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

        # 3. INSERT pending registration row + correlation_id BEFORE provider calls.
        # uuid4 is sufficient — correlation_id is a join key для audit log entries
        # within one register_creative call, not a sort key.
        correlation_id = uuid.uuid4()
        audit_repo = OrdAuditLogRepo(self.session)
        registration = OrdRegistration(
            placement_request_id=placement_request_id,
            status=OrdRegistrationStatus.pending,
            ord_provider=settings.ord_provider,
            correlation_id=correlation_id,
        )
        self.session.add(registration)
        await self.session.flush()
        await audit_repo.log(
            correlation_id=correlation_id,
            placement_id=placement_request_id,
            event_type=OrdAuditEventType.STATE_TRANSITION,
            ord_registration_id=registration.id,
            status_to=OrdRegistrationStatus.pending,
        )

        # 4. register_advertiser
        await audit_repo.log(
            correlation_id=correlation_id,
            placement_id=placement_request_id,
            event_type=OrdAuditEventType.PROVIDER_REQUEST,
            ord_registration_id=registration.id,
            payload={
                "operation": "register_advertiser",
                "user_id": placement.advertiser_id,
                "name": name,
                "inn": inn,
            },
        )
        advertiser_ord_id = await self._provider.register_advertiser(
            user_id=placement.advertiser_id,
            name=name,
            inn=inn,
        )

        # 5. register_platform
        channel = placement.channel
        channel_url = f"https://t.me/{channel.username}" if channel.username else ""
        channel_name = channel.title or channel.username or str(channel.telegram_id)

        await audit_repo.log(
            correlation_id=correlation_id,
            placement_id=placement_request_id,
            event_type=OrdAuditEventType.PROVIDER_REQUEST,
            ord_registration_id=registration.id,
            payload={
                "operation": "register_platform",
                "channel_id": channel.id,
                "channel_url": channel_url,
            },
        )
        platform_ord_id = await self._provider.register_platform(
            channel_id=channel.id,
            channel_url=channel_url,
            channel_name=channel_name,
        )

        # 6. register_contract
        amount = placement.final_price or placement.proposed_price
        amount_rub = str(float(amount))
        pub_date = (placement.final_schedule or datetime.now(UTC)).date().isoformat()

        await audit_repo.log(
            correlation_id=correlation_id,
            placement_id=placement_request_id,
            event_type=OrdAuditEventType.PROVIDER_REQUEST,
            ord_registration_id=registration.id,
            payload={
                "operation": "register_contract",
                "advertiser_ord_id": advertiser_ord_id,
                "amount_rub": amount_rub,
            },
        )
        contract_ord_id = await self._provider.register_contract(
            placement_request_id=placement_request_id,
            advertiser_ord_id=advertiser_ord_id,
            amount_rub=amount_rub,
            date_str=pub_date,
        )

        # 7. register_creative → erid (token)
        await audit_repo.log(
            correlation_id=correlation_id,
            placement_id=placement_request_id,
            event_type=OrdAuditEventType.PROVIDER_REQUEST,
            ord_registration_id=registration.id,
            payload={
                "operation": "register_creative",
                "media_type": media_type,
                "advertiser_ord_id": advertiser_ord_id,
            },
        )
        erid = await self._provider.register_creative(
            placement_request_id=placement_request_id,
            ad_text=ad_text,
            media_type=media_type,
            advertiser_ord_id=advertiser_ord_id,
        )
        await audit_repo.log(
            correlation_id=correlation_id,
            placement_id=placement_request_id,
            event_type=OrdAuditEventType.PROVIDER_RESPONSE,
            ord_registration_id=registration.id,
            payload={"erid": erid, "advertiser_ord_id": advertiser_ord_id},
        )

        # 8. UPDATE registration с обтянутыми полями + state transition.
        now = datetime.now(UTC)
        registration.erid = erid
        registration.advertiser_ord_id = advertiser_ord_id
        registration.platform_ord_id = platform_ord_id
        registration.contract_ord_id = contract_ord_id
        registration.token_received_at = now
        registration.status = OrdRegistrationStatus.token_received
        await audit_repo.log(
            correlation_id=correlation_id,
            placement_id=placement_request_id,
            event_type=OrdAuditEventType.STATE_TRANSITION,
            ord_registration_id=registration.id,
            status_from=OrdRegistrationStatus.pending,
            status_to=OrdRegistrationStatus.token_received,
            payload={"erid": erid},
        )

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
        # channel_id: int,  # Unused parameter removed
        published_at: datetime,
        # post_url: str,  # Unused parameter removed
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
        await repo.update_status(
            registration.id, OrdRegistrationStatus.reported, reported_at=published_at
        )

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
    return OrdService(session, provider=get_ord_provider())
