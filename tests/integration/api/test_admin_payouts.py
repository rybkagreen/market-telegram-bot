"""
Integration-тесты роутера /api/admin/payouts (FIX_PLAN_06 §6.5).

Покрывают контракт API-слоя:
    * `GET /api/admin/payouts` — 403 для не-админа.
    * `POST /api/admin/payouts/{id}/approve` — 200 + сериализация, 404, 400.
    * `POST /api/admin/payouts/{id}/reject` — 200, 422 при пустой `reason`.

Логика `payout_service.{approve,reject}_request` замокана: этот слой
проверяется в `tests/integration/test_payout_lifecycle.py` — там же
происходит реальное перемещение средств.

Relocated from tests/unit/api/ (D4): T1.2.4b commit 5de1ded refactored
auth chain to use single Depends(get_db_session); _resolve_user_for_audience
выполняет selectinload(User.legal_profile) — требует full schema.
unit/conftest SQLite (3-table subset) этого не выдерживает; integration
testcontainer PostgreSQL держит каноническую схему. Auth resolvers
(get_current_admin_user, get_current_user_from_web_portal) запускаются
реально на seeded users — fixture override'ит только get_db_session
(single-override pattern из tests/conftest.py:461-528 api_client_with_auth).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth_utils import create_jwt_token
from src.api.dependencies import get_db_session
from src.api.main import app
from src.core.exceptions import PayoutAlreadyFinalizedError, PayoutNotFoundError
from src.core.services.payout_service import payout_service
from src.db.models.payout import PayoutRequest, PayoutStatus
from src.db.models.user import User


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """DB-seeded admin user (testcontainer PostgreSQL)."""
    user = User(
        telegram_id=900_000_001,
        username="admin_user",
        first_name="Admin",
        is_admin=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def fake_payout_paid(admin_user: User) -> PayoutRequest:
    """Возврат сервиса после успешного approve — status=paid."""
    now = datetime.now(UTC)
    return PayoutRequest(
        id=42,
        owner_id=7001,
        gross_amount=Decimal("1000"),
        fee_amount=Decimal("15"),
        net_amount=Decimal("985"),
        status=PayoutStatus.paid,
        requisites="40802810000000000001",
        admin_id=admin_user.id,
        processed_at=now,
        rejection_reason=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def fake_payout_rejected(admin_user: User) -> PayoutRequest:
    now = datetime.now(UTC)
    return PayoutRequest(
        id=43,
        owner_id=7001,
        gross_amount=Decimal("500"),
        fee_amount=Decimal("7.5"),
        net_amount=Decimal("492.5"),
        status=PayoutStatus.rejected,
        requisites="40802810000000000002",
        admin_id=admin_user.id,
        processed_at=now,
        rejection_reason="Реквизиты не прошли проверку.",
        created_at=now,
        updated_at=now,
    )


@pytest_asyncio.fixture
async def admin_client(
    admin_user: User, db_session: AsyncSession
) -> AsyncGenerator[AsyncClient]:
    """HTTP-клиент с админом — web_portal JWT, реальный auth chain.

    Pattern: tests/conftest.py:461-494 api_client_with_auth (T1.2.4b B2).
    Single override get_db_session — _resolve_user_for_audience запускается
    на integration testcontainer session и находит seeded admin_user.
    Admin endpoint требует source="web_portal" (BL-049 audience hard-cut).
    """
    token = create_jwt_token(
        admin_user.id,
        admin_user.telegram_id,
        admin_user.plan,
        source="web_portal",
    )

    async def _override_get_db_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest_asyncio.fixture
async def advertiser_client(
    advertiser_user: User, db_session: AsyncSession
) -> AsyncGenerator[AsyncClient]:
    """HTTP-клиент с не-админом — web_portal JWT, fail на is_admin check.

    Pattern: tests/conftest.py:497-528 api_client_with_owner_auth.
    Token source="web_portal" чтобы пройти audience-check в
    get_current_user_from_web_portal — затем get_current_admin_user
    падает на is_admin=False с 403 "admin privileges required".
    advertiser_user — DB-seeded из tests/conftest.py:378.
    """
    token = create_jwt_token(
        advertiser_user.id,
        advertiser_user.telegram_id,
        advertiser_user.plan,
        source="web_portal",
    )

    async def _override_get_db_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db_session, None)


# ─── GET /api/admin/payouts ────────────────────────────────────────────


class TestListAdminPayoutsRequiresAdmin:
    """FIX_PLAN_06 §6.5 — обычный пользователь получает 403."""

    async def test_advertiser_gets_403(self, advertiser_client: AsyncClient) -> None:
        resp = await advertiser_client.get("/api/admin/payouts")
        assert resp.status_code == 403, resp.text
        assert "admin" in resp.json()["detail"].lower()

    async def test_anonymous_gets_401(self) -> None:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/admin/payouts")
        # 401 (missing Authorization) либо 403 — оба фиксируют «не-админ отфильтрован»
        assert resp.status_code in (401, 403), resp.text


# ─── POST /api/admin/payouts/{id}/approve ──────────────────────────────


class TestApprovePayoutChangesStatus:
    """FIX_PLAN_06 §6.5 — approve возвращает 200 с AdminPayoutResponse (status=paid)."""

    async def test_approve_returns_paid_response(
        self,
        admin_client: AsyncClient,
        admin_user: User,
        fake_payout_paid: PayoutRequest,
    ) -> None:
        # autospec=True привязывает сигнатуру мока к реальному
        # bound-method `payout_service.approve_request`. Если в сервисе
        # переименовать аргументы — тест упадёт на этапе assert_awaited_with.
        with patch.object(
            payout_service,
            "approve_request",
            autospec=True,
        ) as approve_mock:
            approve_mock.return_value = fake_payout_paid
            resp = await admin_client.post("/api/admin/payouts/42/approve")

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["id"] == 42
        assert body["status"] == "paid"
        assert Decimal(str(body["gross_amount"])) == Decimal("1000")
        assert body["admin_id"] == admin_user.id
        approve_mock.assert_awaited_once_with(42, admin_user.id)


class TestApproveAlreadyProcessed:
    """FIX_PLAN_06 §6.5 + plan-05: approve уже финализированной выплаты
    отдаёт 409 (PayoutAlreadyFinalizedError → ConflictError → 409) с
    error_code="payout_already_finalized".

    До plan-05 роутер мэппил substring "already finalized" → 400 (всё
    остальное — 400). Теперь маппинг по типу исключения через глобальный
    handler в src/api/main.py.
    """

    async def test_approve_already_finalized_returns_409(self, admin_client: AsyncClient) -> None:
        err = PayoutAlreadyFinalizedError(
            "PayoutRequest 42 already finalized (status=paid)",
            extra={"payout_id": 42, "status": "paid"},
        )
        with patch.object(
            payout_service,
            "approve_request",
            autospec=True,
        ) as approve_mock:
            approve_mock.side_effect = err
            resp = await admin_client.post("/api/admin/payouts/42/approve")

        assert resp.status_code == 409, resp.text
        body = resp.json()
        assert "already finalized" in body["detail"]
        assert body["error_code"] == "payout_already_finalized"
        assert body["extra"] == {"payout_id": 42, "status": "paid"}

    async def test_approve_missing_returns_404(self, admin_client: AsyncClient) -> None:
        err = PayoutNotFoundError(
            "PayoutRequest 9999 not found",
            extra={"payout_id": 9999},
        )
        with patch.object(
            payout_service,
            "approve_request",
            autospec=True,
        ) as approve_mock:
            approve_mock.side_effect = err
            resp = await admin_client.post("/api/admin/payouts/9999/approve")

        assert resp.status_code == 404, resp.text
        body = resp.json()
        assert "not found" in body["detail"].lower()
        assert body["error_code"] == "payout_not_found"


# ─── POST /api/admin/payouts/{id}/reject ───────────────────────────────


class TestRejectRequiresReason:
    """FIX_PLAN_06 §6.5 — reject без/с пустой reason → 422."""

    async def test_reject_without_body_returns_422(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post("/api/admin/payouts/42/reject")
        assert resp.status_code == 422, resp.text

    async def test_reject_with_empty_reason_returns_422(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post("/api/admin/payouts/42/reject", json={"reason": ""})
        assert resp.status_code == 422, resp.text

    async def test_reject_happy_path(
        self,
        admin_client: AsyncClient,
        admin_user: User,
        fake_payout_rejected: PayoutRequest,
    ) -> None:
        with patch.object(
            payout_service,
            "reject_request",
            autospec=True,
        ) as reject_mock:
            reject_mock.return_value = fake_payout_rejected
            resp = await admin_client.post(
                "/api/admin/payouts/43/reject",
                json={"reason": "Реквизиты не прошли проверку."},
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "rejected"
        assert body["rejection_reason"] == "Реквизиты не прошли проверку."
        reject_mock.assert_awaited_once_with(
            43, admin_user.id, "Реквизиты не прошли проверку."
        )

    async def test_reject_already_finalized_returns_409(self, admin_client: AsyncClient) -> None:
        # plan-05: ConflictError → 409 (was 400 pre-plan-05).
        err = PayoutAlreadyFinalizedError(
            "PayoutRequest 43 already finalized (status=rejected)",
            extra={"payout_id": 43, "status": "rejected"},
        )
        with patch.object(
            payout_service,
            "reject_request",
            autospec=True,
        ) as reject_mock:
            reject_mock.side_effect = err
            resp = await admin_client.post(
                "/api/admin/payouts/43/reject",
                json={"reason": "дубль отклонения"},
            )
        assert resp.status_code == 409, resp.text
        assert resp.json()["error_code"] == "payout_already_finalized"
