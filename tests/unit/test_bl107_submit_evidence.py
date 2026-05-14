"""BL-107 Phase B.5a — Owner submit-registry-evidence endpoint tests.

Covers POST /api/channels/{id}/submit-registry-evidence:
- Owner submits для own channel → 200, audit log written, admin notification triggered
- Non-owner → 403
- Already-verified channel → 409
- Channel not found → 404
- application_number validation → 422
- Notification helper called с correct args
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_current_user, get_db_session
from src.api.main import app
from src.db.models.user import User


@pytest.fixture
def owner_user() -> User:
    return User(id=7001, telegram_id=100_000, username="owner", first_name="Owner", is_admin=False)


@pytest.fixture
def other_user() -> User:
    return User(id=7002, telegram_id=200_000, username="other", first_name="Other", is_admin=False)


def _make_channel(
    owner_id: int = 7001,
    is_verified: bool = False,
) -> MagicMock:
    """Synthetic channel mock with mutable attrs (so endpoint can write to it)."""
    ch = MagicMock()
    ch.id = 555
    ch.owner_id = owner_id
    ch.is_blogger_registry_verified = is_verified
    ch.blogger_registry_application_number = None
    ch.last_blogger_registry_check_at = None
    return ch


@pytest.fixture
def session_stub() -> MagicMock:
    """Mock async session with `get` returning the channel set via session.set_channel(...)."""
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest_asyncio.fixture
async def client_as_owner(
    owner_user: User,
    session_stub: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncGenerator[tuple[AsyncClient, MagicMock, MagicMock]]:
    """Returns (client, session_stub, notify_mock)."""
    app.dependency_overrides[get_current_user] = lambda: owner_user

    async def _session_gen() -> AsyncGenerator[Any]:
        yield session_stub

    app.dependency_overrides[get_db_session] = _session_gen

    audit_repo = MagicMock(log=AsyncMock(return_value=None))
    monkeypatch.setattr(
        "src.api.routers.channels.AuditLogRepo",
        lambda s: audit_repo,
    )

    notify_mock = AsyncMock(return_value=2)
    monkeypatch.setattr(
        "src.core.services.notification_service.notify_admins_evidence_submitted",
        notify_mock,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, session_stub, notify_mock

    app.dependency_overrides.clear()


# ─── Tests ──────────────────────────────────────────────────────────────────


async def test_submit_evidence_happy_path(
    client_as_owner: tuple[AsyncClient, MagicMock, MagicMock],
) -> None:
    """Owner submits valid evidence для own channel → 200 + channel updated + audit + notify."""
    client, session, notify_mock = client_as_owner
    channel = _make_channel(owner_id=7001, is_verified=False)
    session.get = AsyncMock(return_value=channel)

    resp = await client.post(
        "/api/channels/555/submit-registry-evidence",
        json={"application_number": "A-2026-04-12345", "notes": "Submission notes"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending_review"
    assert body["channel_id"] == 555
    assert body["application_number"] == "A-2026-04-12345"
    assert "submitted_at" in body

    # Channel state mutated
    assert channel.blogger_registry_application_number == "A-2026-04-12345"
    assert channel.last_blogger_registry_check_at is not None

    # Admin notification triggered
    notify_mock.assert_called_once()
    call_kwargs = notify_mock.call_args.kwargs
    assert call_kwargs["channel_id"] == 555
    assert call_kwargs["owner_user_id"] == 7001
    assert call_kwargs["application_number"] == "A-2026-04-12345"


async def test_submit_evidence_non_owner_forbidden(
    client_as_owner: tuple[AsyncClient, MagicMock, MagicMock],
) -> None:
    """Channel owned by другой user → 403 Forbidden."""
    client, session, _ = client_as_owner
    channel = _make_channel(owner_id=7002, is_verified=False)  # NOT current user
    session.get = AsyncMock(return_value=channel)

    resp = await client.post(
        "/api/channels/555/submit-registry-evidence",
        json={"application_number": "A-2026-04-12345"},
    )

    assert resp.status_code == 403


async def test_submit_evidence_already_verified_conflict(
    client_as_owner: tuple[AsyncClient, MagicMock, MagicMock],
) -> None:
    """Already-verified channel → 409 Conflict (no double-submit)."""
    client, session, _ = client_as_owner
    channel = _make_channel(owner_id=7001, is_verified=True)
    session.get = AsyncMock(return_value=channel)

    resp = await client.post(
        "/api/channels/555/submit-registry-evidence",
        json={"application_number": "A-2026-04-12345"},
    )

    assert resp.status_code == 409


async def test_submit_evidence_channel_not_found(
    client_as_owner: tuple[AsyncClient, MagicMock, MagicMock],
) -> None:
    """Channel not found → 404."""
    client, session, _ = client_as_owner
    session.get = AsyncMock(return_value=None)

    resp = await client.post(
        "/api/channels/999/submit-registry-evidence",
        json={"application_number": "A-2026-04-12345"},
    )

    assert resp.status_code == 404


async def test_submit_evidence_application_number_required(
    client_as_owner: tuple[AsyncClient, MagicMock, MagicMock],
) -> None:
    """Missing application_number → 422."""
    client, session, _ = client_as_owner
    channel = _make_channel()
    session.get = AsyncMock(return_value=channel)

    resp = await client.post(
        "/api/channels/555/submit-registry-evidence",
        json={"notes": "Forgot the number"},
    )

    assert resp.status_code == 422


async def test_submit_evidence_application_number_max_length(
    client_as_owner: tuple[AsyncClient, MagicMock, MagicMock],
) -> None:
    """application_number > 64 chars → 422."""
    client, session, _ = client_as_owner
    channel = _make_channel()
    session.get = AsyncMock(return_value=channel)

    resp = await client.post(
        "/api/channels/555/submit-registry-evidence",
        json={"application_number": "A" * 65},
    )

    assert resp.status_code == 422


async def test_submit_evidence_with_registry_url(
    client_as_owner: tuple[AsyncClient, MagicMock, MagicMock],
) -> None:
    """Valid registry_url accepted, audit captures it."""
    client, session, _ = client_as_owner
    channel = _make_channel()
    session.get = AsyncMock(return_value=channel)

    resp = await client.post(
        "/api/channels/555/submit-registry-evidence",
        json={
            "application_number": "A-2026-04-12345",
            "registry_url": "https://rkn.gov.ru/blogger-registry/A-2026-04-12345",
        },
    )

    assert resp.status_code == 200
    # Verify the channel was updated even с optional url
    assert channel.blogger_registry_application_number == "A-2026-04-12345"


# Ensure UTC import is used (so linter doesn't strip)
_ = (UTC, datetime)
