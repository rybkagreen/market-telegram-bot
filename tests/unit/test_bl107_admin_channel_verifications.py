"""BL-107 Phase B.5a — Admin channel-verifications endpoints tests.

Covers:
- GET /api/admin/channel-verifications (list, paginated, filtered)
- GET /api/admin/channel-verifications/{id} (detail с history)
- POST /api/admin/channel-verifications/{id}/verify (approve)
- POST /api/admin/channel-verifications/{id}/reject (reject)
- Permission: non-admin → 403

Mocks at boundaries — no DB, no live notifications.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import (
    get_current_admin_user,
    get_current_user,
    get_current_user_from_web_portal,
    get_db_session,
)
from src.api.main import app
from src.db.models.user import User


@pytest.fixture
def admin_user() -> User:
    return User(id=9001, telegram_id=900_000, username="admin", first_name="Admin", is_admin=True)


@pytest.fixture
def regular_user() -> User:
    return User(id=8001, telegram_id=800_000, username="regular", first_name="Reg", is_admin=False)


def _make_channel(
    channel_id: int = 555,
    owner_id: int = 7001,
    is_verified: bool = False,
    application_number: str | None = "A-2026-04-12345",
    member_count: int = 12_000,
) -> MagicMock:
    ch = MagicMock()
    ch.id = channel_id
    ch.owner_id = owner_id
    ch.username = "test_chan"
    ch.title = "Test Chan"
    ch.member_count = member_count
    ch.is_blogger_registry_verified = is_verified
    ch.blogger_registry_application_number = application_number
    ch.blogger_registry_verified_at = None
    ch.blogger_registry_verification_method = None
    ch.blogger_registry_verified_by_admin_id = None
    ch.member_count_at_verification = None
    ch.last_blogger_registry_check_at = datetime.now(UTC)
    return ch


@pytest.fixture
def session_stub() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest_asyncio.fixture
async def client_as_admin(
    admin_user: User,
    session_stub: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[tuple[AsyncClient, MagicMock]]:
    """Returns (client, session_stub) with admin dependency."""
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_current_user_from_web_portal] = lambda: admin_user
    app.dependency_overrides[get_current_admin_user] = lambda: admin_user

    async def _session_gen() -> AsyncGenerator[Any]:
        yield session_stub

    app.dependency_overrides[get_db_session] = _session_gen

    audit_repo = MagicMock(
        log=AsyncMock(return_value=None),
        query_logs=AsyncMock(return_value=[]),
    )
    monkeypatch.setattr("src.api.routers.admin.AuditLogRepo", lambda s: audit_repo)

    notify_owner_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "src.api.routers.admin.notify_owner_verification_decided",
        notify_owner_mock,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, session_stub

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_as_regular(
    regular_user: User,
    session_stub: MagicMock,
) -> AsyncGenerator[AsyncClient]:
    """Non-admin user — admin endpoints должны 403 from real get_current_admin_user."""
    # Override the upstream dependency so get_current_admin_user runs real
    # and raises 403 на is_admin=False.
    app.dependency_overrides[get_current_user_from_web_portal] = lambda: regular_user
    app.dependency_overrides[get_current_user] = lambda: regular_user

    async def _session_gen() -> AsyncGenerator[Any]:
        yield session_stub

    app.dependency_overrides[get_db_session] = _session_gen

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ─── List endpoint tests ───────────────────────────────────────────────────


async def test_list_empty(
    client_as_admin: tuple[AsyncClient, MagicMock],
) -> None:
    """Empty list when no submissions."""
    client, session = client_as_admin
    exec_result = MagicMock()
    exec_result.scalars.return_value.all.return_value = []
    exec_result.scalar.return_value = 0
    session.execute = AsyncMock(return_value=exec_result)
    session.get = AsyncMock(return_value=None)

    resp = await client.get("/api/admin/channel-verifications")

    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["limit"] == 50
    assert body["offset"] == 0


async def test_list_with_items(
    client_as_admin: tuple[AsyncClient, MagicMock],
) -> None:
    """Non-empty list shows pending submissions."""
    client, session = client_as_admin
    channel = _make_channel()
    owner = User(id=7001, telegram_id=100_000, username="owner_user", first_name="O")

    scalar_calls = [2, 0]
    exec_result_list = MagicMock()
    exec_result_list.scalars.return_value.all.return_value = [channel]

    async def _execute(*_a: Any, **_kw: Any) -> Any:
        result = MagicMock()
        result.scalars.return_value.all.return_value = [channel]
        if scalar_calls:
            result.scalar.return_value = scalar_calls.pop(0)
        else:
            result.scalar.return_value = 0
        return result

    session.execute = _execute
    session.get = AsyncMock(return_value=owner)

    resp = await client.get("/api/admin/channel-verifications?status=pending_review&limit=10")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["limit"] == 10
    assert len(body["items"]) == 1
    assert body["items"][0]["channel_id"] == 555
    assert body["items"][0]["application_number"] == "A-2026-04-12345"
    assert body["items"][0]["status"] == "pending_review"


async def test_list_filter_verified(
    client_as_admin: tuple[AsyncClient, MagicMock],
) -> None:
    """status=verified filter accepted."""
    client, session = client_as_admin

    async def _execute(*_a: Any, **_kw: Any) -> Any:
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        result.scalar.return_value = 0
        return result

    session.execute = _execute
    session.get = AsyncMock(return_value=None)

    resp = await client.get("/api/admin/channel-verifications?status=verified")

    assert resp.status_code == 200
    assert resp.json()["items"] == []


# ─── Detail endpoint tests ─────────────────────────────────────────────────


async def test_detail_returns_history(
    client_as_admin: tuple[AsyncClient, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Detail returns channel data + history list."""
    client, session = client_as_admin
    channel = _make_channel()
    owner = User(id=7001, telegram_id=100_000, username="owner_user", first_name="O")

    log_entry = MagicMock()
    log_entry.action = "blogger_registry_evidence_submitted"
    log_entry.user_id = 7001
    log_entry.created_at = datetime.now(UTC)
    log_entry.extra = {"application_number": "A-2026-04-12345"}
    log_entry.resource_id = 555

    audit_repo = MagicMock(
        log=AsyncMock(return_value=None),
        query_logs=AsyncMock(return_value=[log_entry]),
    )
    monkeypatch.setattr("src.api.routers.admin.AuditLogRepo", lambda s: audit_repo)
    monkeypatch.setattr(
        "src.api.routers.admin.notify_owner_verification_decided",
        AsyncMock(return_value=True),
    )

    session.get = AsyncMock(side_effect=[channel, owner])

    resp = await client.get("/api/admin/channel-verifications/555")

    assert resp.status_code == 200
    body = resp.json()
    assert body["channel_id"] == 555
    assert body["application_number"] == "A-2026-04-12345"
    assert len(body["history"]) == 3  # query_logs called 3x (one per action), all return same entry
    assert body["history"][0]["action"] == "blogger_registry_evidence_submitted"


async def test_detail_not_found(
    client_as_admin: tuple[AsyncClient, MagicMock],
) -> None:
    """Detail для non-existent channel → 404."""
    client, session = client_as_admin
    session.get = AsyncMock(return_value=None)

    resp = await client.get("/api/admin/channel-verifications/999")

    assert resp.status_code == 404


# ─── Verify endpoint tests ─────────────────────────────────────────────────


async def test_verify_happy_path(
    client_as_admin: tuple[AsyncClient, MagicMock],
) -> None:
    """Verify: channel marked verified, all audit fields populated."""
    client, session = client_as_admin
    channel = _make_channel(application_number="A-2026-04-12345", is_verified=False)
    session.get = AsyncMock(return_value=channel)

    resp = await client.post(
        "/api/admin/channel-verifications/555/verify",
        json={"notes": "Validated via Госуслуги"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["channel_id"] == 555
    assert body["is_blogger_registry_verified"] is True
    assert body["blogger_registry_verification_method"] == "manual_evidence"
    assert body["blogger_registry_verified_by_admin_id"] == 9001
    # Channel state mutated
    assert channel.is_blogger_registry_verified is True
    assert channel.blogger_registry_verified_at is not None
    assert channel.blogger_registry_verification_method == "manual_evidence"
    assert channel.blogger_registry_verified_by_admin_id == 9001
    assert channel.member_count_at_verification == 12_000


async def test_verify_no_submission_conflict(
    client_as_admin: tuple[AsyncClient, MagicMock],
) -> None:
    """Verify with no application_number → 409."""
    client, session = client_as_admin
    channel = _make_channel(application_number=None)
    session.get = AsyncMock(return_value=channel)

    resp = await client.post(
        "/api/admin/channel-verifications/555/verify",
        json={"notes": "Trying to verify with nothing"},
    )

    assert resp.status_code == 409


async def test_verify_already_verified_conflict(
    client_as_admin: tuple[AsyncClient, MagicMock],
) -> None:
    """Verify already-verified channel → 409."""
    client, session = client_as_admin
    channel = _make_channel(is_verified=True)
    session.get = AsyncMock(return_value=channel)

    resp = await client.post(
        "/api/admin/channel-verifications/555/verify",
        json={},
    )

    assert resp.status_code == 409


async def test_verify_channel_not_found(
    client_as_admin: tuple[AsyncClient, MagicMock],
) -> None:
    """Verify non-existent channel → 404."""
    client, session = client_as_admin
    session.get = AsyncMock(return_value=None)

    resp = await client.post(
        "/api/admin/channel-verifications/999/verify",
        json={},
    )

    assert resp.status_code == 404


# ─── Reject endpoint tests ─────────────────────────────────────────────────


async def test_reject_happy_path(
    client_as_admin: tuple[AsyncClient, MagicMock],
) -> None:
    """Reject: application_number reset, audit written, owner notified."""
    client, session = client_as_admin
    channel = _make_channel(application_number="A-2026-04-12345")
    session.get = AsyncMock(return_value=channel)

    resp = await client.post(
        "/api/admin/channel-verifications/555/reject",
        json={"reason": "Application number not found в реестре"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["channel_id"] == 555
    assert body["reason"] == "Application number not found в реестре"
    # application_number reset
    assert channel.blogger_registry_application_number is None


async def test_reject_no_submission_conflict(
    client_as_admin: tuple[AsyncClient, MagicMock],
) -> None:
    """Reject without submission → 409."""
    client, session = client_as_admin
    channel = _make_channel(application_number=None)
    session.get = AsyncMock(return_value=channel)

    resp = await client.post(
        "/api/admin/channel-verifications/555/reject",
        json={"reason": "Nothing to reject"},
    )

    assert resp.status_code == 409


async def test_reject_reason_required(
    client_as_admin: tuple[AsyncClient, MagicMock],
) -> None:
    """Reject without reason → 422."""
    client, session = client_as_admin
    channel = _make_channel()
    session.get = AsyncMock(return_value=channel)

    resp = await client.post(
        "/api/admin/channel-verifications/555/reject",
        json={},
    )

    assert resp.status_code == 422


# ─── Permission tests ──────────────────────────────────────────────────────


async def test_non_admin_forbidden_list(
    client_as_regular: AsyncClient,
) -> None:
    """Non-admin → 403 on list endpoint."""
    resp = await client_as_regular.get("/api/admin/channel-verifications")
    assert resp.status_code == 403


async def test_non_admin_forbidden_verify(
    client_as_regular: AsyncClient,
) -> None:
    """Non-admin → 403 on verify endpoint."""
    resp = await client_as_regular.post(
        "/api/admin/channel-verifications/555/verify",
        json={},
    )
    assert resp.status_code == 403
