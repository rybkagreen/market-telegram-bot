"""
Unit-тесты unified PATCH /api/placements/{id} (FIX_PLAN_06 §6.6).

Закрепляют контракт action-based эндпойнта, который заменил legacy
`POST /accept`, `/reject`, `/counter`, `/pay`, `/cancel` в S-44.
Проверяется пять action'ов + граничные случаи (право роли, конфликт
статуса, пустой body).

Сервис-слой (`PlacementRequestService`) и репозитории замоканы — цель
теста зафиксировать маршрутизацию и сериализацию, а не бизнес-логику
(она покрыта в `tests/test_counter_offer_flow.py` и
`tests/integration/test_payout_lifecycle.py`).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_current_user, get_db_session
from src.api.main import app
from src.core.services.placement_request_service import PlacementRequestService
from src.db.models.placement_request import PlacementStatus
from src.db.models.user import User

# ─── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def owner_user() -> User:
    return User(
        id=7001,
        telegram_id=222_222_222,
        username="owner",
        first_name="Owner",
        is_active=True,
    )


@pytest.fixture
def advertiser_user() -> User:
    return User(
        id=8001,
        telegram_id=111_111_111,
        username="advertiser",
        first_name="Advertiser",
        is_active=True,
    )


def _make_placement(
    *,
    status: PlacementStatus = PlacementStatus.pending_owner,
    advertiser_id: int = 8001,
    owner_id: int = 7001,
    channel_id: int = 501,
    final_price: Decimal | None = None,
    counter_price: Decimal | None = None,
) -> SimpleNamespace:
    """Создать SimpleNamespace, совместимый с `PlacementResponse.model_validate`."""
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=4242,
        advertiser_id=advertiser_id,
        owner_id=owner_id,
        channel_id=channel_id,
        channel=SimpleNamespace(id=channel_id, username="ch", title="Test Channel"),
        status=status.value,
        publication_format="post_24h",
        proposed_price=Decimal("1500"),
        final_price=final_price,
        final_schedule=None,
        ad_text="Ad text that is long enough to pass validators",
        proposed_schedule=now,
        published_at=None,
        expires_at=None,
        scheduled_delete_at=None,
        deleted_at=None,
        counter_offer_count=0,
        counter_price=counter_price,
        counter_schedule=None,
        counter_comment=None,
        advertiser_counter_price=None,
        advertiser_counter_schedule=None,
        advertiser_counter_comment=None,
        rejection_reason=None,
        clicks_count=0,
        published_reach=None,
        tracking_short_code=None,
        has_dispute=False,
        dispute_status=None,
        erid=None,
        is_test=False,
        test_label=None,
        media_type="none",
        video_file_id=None,
        video_url=None,
        video_thumbnail_file_id=None,
        video_duration=None,
        created_at=now,
        updated_at=now,
    )


def _make_channel(owner_id: int, channel_id: int = 501) -> SimpleNamespace:
    return SimpleNamespace(
        id=channel_id,
        owner_id=owner_id,
        username="ch",
        title="Test Channel",
    )


@pytest_asyncio.fixture
async def client_as_owner(owner_user: User) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_current_user] = lambda: owner_user
    app.dependency_overrides[get_db_session] = _stub_session_dep

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_as_advertiser(
    advertiser_user: User,
) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_current_user] = lambda: advertiser_user
    app.dependency_overrides[get_db_session] = _stub_session_dep

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


async def _stub_session_dep() -> AsyncGenerator[Any]:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    yield session


def _patch_router_repos(
    placement: SimpleNamespace,
    channel: SimpleNamespace,
    *,
    service_method_name: str,
    service_return: SimpleNamespace,
) -> Any:
    """Патчит PlacementRequestRepository / TelegramChatRepository / PlacementRequestService.

    `PlacementRequestService` мокается через `create_autospec(..., instance=True,
    spec_set=True)` — это гарантирует, что тест упадёт, если в сервисе
    переименуют/удалят метод (`owner_accept`, `owner_reject`,
    `owner_counter_offer`, `process_payment`, `advertiser_cancel`) или
    поменяют его арность. MagicMock в этом месте ловил регрессии тестов,
    а не drift сервиса, что и было написано в FIX_PLAN_06 §6.6.
    """
    placement_repo = MagicMock()
    placement_repo.get_by_id = AsyncMock(return_value=placement)

    channel_repo = MagicMock()
    channel_repo.get_by_id = AsyncMock(return_value=channel)

    service = create_autospec(PlacementRequestService, instance=True, spec_set=True)
    # autospec авто-создаёт AsyncMock для async-методов; задаём return_value
    # на конкретной цели, не вызывая setattr (spec_set запрещает новые атрибуты,
    # но существующий атрибут уже является AsyncMock).
    getattr(service, service_method_name).return_value = service_return

    return (
        patch(
            "src.api.routers.placements.PlacementRequestRepository",
            return_value=placement_repo,
        ),
        patch(
            "src.api.routers.placements.TelegramChatRepository",
            return_value=channel_repo,
        ),
        patch(
            "src.api.routers.placements.PlacementRequestService",
            return_value=service,
        ),
        service,
    )


# ─── Tests ─────────────────────────────────────────────────────────────


class TestPatchAccept:
    """PATCH {action: 'accept'} → owner_accept, status=pending_payment."""

    async def test_owner_accepts(self, client_as_owner: AsyncClient) -> None:
        placement = _make_placement()
        channel = _make_channel(owner_id=7001)
        updated = _make_placement(status=PlacementStatus.pending_payment)
        p1, p2, p3, service = _patch_router_repos(
            placement,
            channel,
            service_method_name="owner_accept",
            service_return=updated,
        )
        with p1, p2, p3:
            resp = await client_as_owner.patch("/api/placements/4242", json={"action": "accept"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "pending_payment"
        service.owner_accept.assert_awaited_once_with(4242, 7001)

    async def test_non_owner_gets_403(self, client_as_advertiser: AsyncClient) -> None:
        placement = _make_placement(owner_id=9999)  # not advertiser.id, not owner
        channel = _make_channel(owner_id=9999)
        p1, p2, p3, _ = _patch_router_repos(
            placement,
            channel,
            service_method_name="owner_accept",
            service_return=placement,
        )
        with p1, p2, p3:
            resp = await client_as_advertiser.patch(
                "/api/placements/4242", json={"action": "accept"}
            )
        # advertiser.id=8001 совпадает с placement.advertiser_id=8001 → роль = advertiser,
        # accept доступен только owner → 403
        assert resp.status_code == 403, resp.text


class TestPatchReject:
    """PATCH {action: 'reject', reason_text} → owner_reject."""

    async def test_owner_rejects_with_reason(self, client_as_owner: AsyncClient) -> None:
        placement = _make_placement()
        channel = _make_channel(owner_id=7001)
        updated = _make_placement(status=PlacementStatus.cancelled)
        p1, p2, p3, service = _patch_router_repos(
            placement,
            channel,
            service_method_name="owner_reject",
            service_return=updated,
        )
        with p1, p2, p3:
            resp = await client_as_owner.patch(
                "/api/placements/4242",
                json={"action": "reject", "reason_text": "Не подходит тематика"},
            )
        assert resp.status_code == 200, resp.text
        service.owner_reject.assert_awaited_once_with(4242, 7001, "Не подходит тематика")

    async def test_reject_without_reason_falls_back_to_default(
        self, client_as_owner: AsyncClient
    ) -> None:
        placement = _make_placement()
        channel = _make_channel(owner_id=7001)
        p1, p2, p3, service = _patch_router_repos(
            placement,
            channel,
            service_method_name="owner_reject",
            service_return=placement,
        )
        with p1, p2, p3:
            resp = await client_as_owner.patch("/api/placements/4242", json={"action": "reject"})
        assert resp.status_code == 200, resp.text
        # Роутер подставляет literal "rejected" если ни reason_text, ни reason_code нет
        service.owner_reject.assert_awaited_once()
        args = service.owner_reject.await_args.args
        assert args[0] == 4242
        assert args[1] == 7001
        assert args[2] == "rejected"


class TestPatchCounter:
    """PATCH {action: 'counter', price} → owner_counter_offer."""

    async def test_owner_counters_with_price(self, client_as_owner: AsyncClient) -> None:
        placement = _make_placement()
        channel = _make_channel(owner_id=7001)
        updated = _make_placement(
            status=PlacementStatus.counter_offer,
            counter_price=Decimal("2000"),
        )
        p1, p2, p3, service = _patch_router_repos(
            placement,
            channel,
            service_method_name="owner_counter_offer",
            service_return=updated,
        )
        with p1, p2, p3:
            resp = await client_as_owner.patch(
                "/api/placements/4242",
                json={"action": "counter", "price": 2000},
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "counter_offer"
        assert Decimal(body["counter_price"]) == Decimal("2000")
        service.owner_counter_offer.assert_awaited_once_with(4242, 7001, Decimal("2000"))

    async def test_counter_without_price_returns_400(self, client_as_owner: AsyncClient) -> None:
        placement = _make_placement()
        channel = _make_channel(owner_id=7001)
        p1, p2, p3, _ = _patch_router_repos(
            placement,
            channel,
            service_method_name="owner_counter_offer",
            service_return=placement,
        )
        with p1, p2, p3:
            resp = await client_as_owner.patch("/api/placements/4242", json={"action": "counter"})
        assert resp.status_code == 400, resp.text
        assert "price required" in resp.json()["detail"]


class TestPatchPay:
    """PATCH {action: 'pay'} → process_payment, status=escrow."""

    async def test_advertiser_pays_moves_to_escrow(self, client_as_advertiser: AsyncClient) -> None:
        placement = _make_placement(status=PlacementStatus.pending_payment)
        channel = _make_channel(owner_id=7001)
        updated = _make_placement(
            status=PlacementStatus.escrow,
            final_price=Decimal("1500"),
        )
        p1, p2, p3, service = _patch_router_repos(
            placement,
            channel,
            service_method_name="process_payment",
            service_return=updated,
        )
        with p1, p2, p3:
            resp = await client_as_advertiser.patch("/api/placements/4242", json={"action": "pay"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "escrow"
        service.process_payment.assert_awaited_once_with(4242, 8001)

    async def test_pay_in_wrong_status_returns_409(self, client_as_advertiser: AsyncClient) -> None:
        # placement в pending_owner — нельзя платить
        placement = _make_placement(status=PlacementStatus.pending_owner)
        channel = _make_channel(owner_id=7001)
        p1, p2, p3, _ = _patch_router_repos(
            placement,
            channel,
            service_method_name="process_payment",
            service_return=placement,
        )
        with p1, p2, p3:
            resp = await client_as_advertiser.patch("/api/placements/4242", json={"action": "pay"})
        assert resp.status_code == 409, resp.text
        assert "pending_payment" in resp.json()["detail"]


class TestPatchCancel:
    """PATCH {action: 'cancel'} → advertiser_cancel, status=cancelled."""

    async def test_advertiser_cancels(self, client_as_advertiser: AsyncClient) -> None:
        placement = _make_placement(status=PlacementStatus.pending_owner)
        channel = _make_channel(owner_id=7001)
        updated = _make_placement(status=PlacementStatus.cancelled)
        p1, p2, p3, service = _patch_router_repos(
            placement,
            channel,
            service_method_name="advertiser_cancel",
            service_return=updated,
        )
        with p1, p2, p3:
            resp = await client_as_advertiser.patch(
                "/api/placements/4242", json={"action": "cancel"}
            )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "cancelled"
        service.advertiser_cancel.assert_awaited_once_with(4242, 8001)

    async def test_non_advertiser_cancel_returns_403(self, client_as_owner: AsyncClient) -> None:
        placement = _make_placement(status=PlacementStatus.pending_owner)
        channel = _make_channel(owner_id=7001)
        p1, p2, p3, _ = _patch_router_repos(
            placement,
            channel,
            service_method_name="advertiser_cancel",
            service_return=placement,
        )
        with p1, p2, p3:
            resp = await client_as_owner.patch("/api/placements/4242", json={"action": "cancel"})
        assert resp.status_code == 403, resp.text


class TestPatchNotFound:
    async def test_unknown_placement_id_returns_404(self, client_as_owner: AsyncClient) -> None:
        placement_repo = MagicMock()
        placement_repo.get_by_id = AsyncMock(return_value=None)
        with patch(
            "src.api.routers.placements.PlacementRequestRepository",
            return_value=placement_repo,
        ):
            resp = await client_as_owner.patch("/api/placements/999", json={"action": "accept"})
        assert resp.status_code == 404, resp.text
