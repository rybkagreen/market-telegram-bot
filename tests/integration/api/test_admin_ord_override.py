"""Integration tests for admin ORD override endpoint (BL-080 8c, Q5=(a)).

POST /api/admin/ord-registrations/{registration_id}/override

Validates auth, state guards, status transitions, и audit log dual-write.
Pattern mirrors tests/integration/api/test_admin_payouts.py (single
get_db_session override; real auth chain).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth_utils import create_jwt_token
from src.api.dependencies import get_db_session
from src.api.main import app
from src.db.models.ord_audit_log import OrdAuditEventType, OrdAuditLog
from src.db.models.ord_registration import OrdRegistration, OrdRegistrationStatus
from src.db.models.placement_request import PlacementRequest
from src.db.models.user import User


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        telegram_id=900_000_500,
        username="admin_ord",
        first_name="AdminOrd",
        is_admin=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_client(admin_user: User, db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
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


async def _seed_blocked_registration(
    db_session: AsyncSession, placement: PlacementRequest
) -> OrdRegistration:
    reg = OrdRegistration(
        placement_request_id=placement.id,
        status=OrdRegistrationStatus.ord_blocked,
        ord_provider="yandex",
        correlation_id=uuid.uuid4(),
        error_message="ORD provider rejected creative",
    )
    db_session.add(reg)
    await db_session.commit()
    await db_session.refresh(reg)
    return reg


class TestAdminOrdOverrideAuth:
    """Override requires admin role."""

    async def test_advertiser_gets_403(
        self,
        advertiser_client: AsyncClient,
        placement_request: PlacementRequest,
        db_session: AsyncSession,
    ) -> None:
        reg = await _seed_blocked_registration(db_session, placement_request)
        resp = await advertiser_client.post(
            f"/api/admin/ord-registrations/{reg.id}/override",
            json={"action": "retry", "reason": "test retry"},
        )
        assert resp.status_code == 403, resp.text

    async def test_anonymous_gets_401_or_403(
        self,
        placement_request: PlacementRequest,
        db_session: AsyncSession,
    ) -> None:
        reg = await _seed_blocked_registration(db_session, placement_request)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/admin/ord-registrations/{reg.id}/override",
                json={"action": "retry", "reason": "test retry"},
            )
        assert resp.status_code in (401, 403), resp.text


class TestAdminOrdOverrideRetry:
    """action=retry: resets к pending + enqueues register_creative."""

    async def test_retry_from_ord_blocked_resets_to_pending(
        self,
        admin_client: AsyncClient,
        placement_request: PlacementRequest,
        db_session: AsyncSession,
    ) -> None:
        reg = await _seed_blocked_registration(db_session, placement_request)
        old_correlation = reg.correlation_id

        with patch("src.tasks.ord_tasks.register_creative_task.delay") as mock_enqueue:
            resp = await admin_client.post(
                f"/api/admin/ord-registrations/{reg.id}/override",
                json={"action": "retry", "reason": "Yandex outage cleared"},
            )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == OrdRegistrationStatus.pending.value
        assert body["error_message"] is None
        new_correlation = uuid.UUID(body["correlation_id"])
        assert new_correlation != old_correlation

        # Celery task enqueued
        mock_enqueue.assert_called_once_with(placement_request.id)

        # Audit log entry created
        await db_session.commit()
        audit = await db_session.execute(
            select(OrdAuditLog)
            .where(OrdAuditLog.ord_registration_id == reg.id)
            .where(OrdAuditLog.event_type == OrdAuditEventType.ADMIN_OVERRIDE)
        )
        entries = list(audit.scalars())
        assert len(entries) == 1
        entry = entries[0]
        assert entry.correlation_id == new_correlation
        assert entry.payload is not None
        assert entry.payload["action"] == "retry"
        assert "Yandex outage" in entry.payload["reason"]

    async def test_retry_from_pending_returns_409(
        self,
        admin_client: AsyncClient,
        placement_request: PlacementRequest,
        db_session: AsyncSession,
    ) -> None:
        reg = OrdRegistration(
            placement_request_id=placement_request.id,
            status=OrdRegistrationStatus.pending,
            ord_provider="yandex",
        )
        db_session.add(reg)
        await db_session.commit()
        await db_session.refresh(reg)

        resp = await admin_client.post(
            f"/api/admin/ord-registrations/{reg.id}/override",
            json={"action": "retry", "reason": "wrong state"},
        )
        assert resp.status_code == 409, resp.text


class TestAdminOrdOverrideCancel:
    """action=cancel: marks cancelled + writes audit entry."""

    async def test_cancel_from_ord_blocked(
        self,
        admin_client: AsyncClient,
        placement_request: PlacementRequest,
        db_session: AsyncSession,
    ) -> None:
        reg = await _seed_blocked_registration(db_session, placement_request)
        resp = await admin_client.post(
            f"/api/admin/ord-registrations/{reg.id}/override",
            json={"action": "cancel", "reason": "advertiser withdrew"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == OrdRegistrationStatus.cancelled.value

    async def test_cancel_from_erir_confirmed_returns_409(
        self,
        admin_client: AsyncClient,
        placement_request: PlacementRequest,
        db_session: AsyncSession,
    ) -> None:
        reg = OrdRegistration(
            placement_request_id=placement_request.id,
            status=OrdRegistrationStatus.erir_confirmed,
            ord_provider="yandex",
        )
        db_session.add(reg)
        await db_session.commit()
        await db_session.refresh(reg)

        resp = await admin_client.post(
            f"/api/admin/ord-registrations/{reg.id}/override",
            json={"action": "cancel", "reason": "too late, ERIR confirmed"},
        )
        assert resp.status_code == 409, resp.text


class TestAdminOrdOverrideValidation:
    """Body validation."""

    async def test_missing_reason_returns_422(
        self,
        admin_client: AsyncClient,
        placement_request: PlacementRequest,
        db_session: AsyncSession,
    ) -> None:
        reg = await _seed_blocked_registration(db_session, placement_request)
        resp = await admin_client.post(
            f"/api/admin/ord-registrations/{reg.id}/override",
            json={"action": "retry"},
        )
        assert resp.status_code == 422, resp.text

    async def test_invalid_action_returns_422(
        self,
        admin_client: AsyncClient,
        placement_request: PlacementRequest,
        db_session: AsyncSession,
    ) -> None:
        reg = await _seed_blocked_registration(db_session, placement_request)
        resp = await admin_client.post(
            f"/api/admin/ord-registrations/{reg.id}/override",
            json={"action": "delete", "reason": "wrong action"},
        )
        assert resp.status_code == 422, resp.text

    async def test_unknown_registration_returns_404(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post(
            "/api/admin/ord-registrations/999999/override",
            json={"action": "cancel", "reason": "no such row"},
        )
        assert resp.status_code == 404, resp.text


pytestmark = pytest.mark.asyncio
