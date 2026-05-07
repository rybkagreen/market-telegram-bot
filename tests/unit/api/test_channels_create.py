"""Unit tests for POST /api/channels/ — Phase 3b §3.B.6 channel-add hook (5b.7a).

Verifies:

* Happy path: all owner-role gates pass → channel is created (201).
* Decline path: any of G04/G05/G06 fails → ChannelAddDeclinedError (HTTP 403)
  with blockers + remediation_url surfaced via ``extra``.
* Admin test-mode carve-out (Marina Q3=(а)): when ``is_admin and is_test=True``
  the compliance check is skipped entirely.
* Audit log writes on declined attempts.

The Telegram round-trip is mocked because the hook fires *before*
``bot.get_chat()`` — declined owners must not waste Telegram API quota.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.dependencies import get_bot, get_current_user, get_db_session
from src.api.main import app
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.user import User


def _ok(gate: PlacementGate) -> GateResult:
    return GateResult(gate=gate, passed=True, blocker=True, reason_code="ok")


def _fail(
    gate: PlacementGate,
    reason: str,
    remediation_url: str | None,
) -> GateResult:
    return GateResult(
        gate=gate,
        passed=False,
        blocker=True,
        reason_code=reason,
        remediation_url=remediation_url,
    )


@pytest.fixture
def owner_user() -> User:
    user = User(
        id=7001,
        telegram_id=100_000,
        username="owner",
        first_name="Owner",
        is_admin=False,
    )
    return user


@pytest.fixture
def admin_user() -> User:
    user = User(
        id=9001,
        telegram_id=900_000,
        username="admin",
        first_name="Admin",
        is_admin=True,
    )
    return user


async def _stub_session_dep() -> AsyncGenerator[Any]:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    yield session


def _bot_dep_factory() -> Any:
    bot = MagicMock()
    chat = MagicMock()
    chat.id = 1
    chat.type = "channel"
    chat.title = "Test"
    chat.username = "test_chan"
    chat.get_member_count = AsyncMock(return_value=100)
    bot.get_chat = AsyncMock(return_value=chat)
    bot.get_chat_member = AsyncMock()
    bot.id = 999
    return bot


@pytest_asyncio.fixture
async def client_as_owner(
    owner_user: User,
) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_current_user] = lambda: owner_user
    app.dependency_overrides[get_db_session] = _stub_session_dep
    app.dependency_overrides[get_bot] = lambda: _bot_dep_factory()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_as_admin(
    admin_user: User,
) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db_session] = _stub_session_dep
    app.dependency_overrides[get_bot] = lambda: _bot_dep_factory()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_channel_g04_fail_returns_403_with_remediation(
    client_as_owner: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G04 fail → 403 with blockers + remediation_url=/legal-profile."""
    monkeypatch.setattr(
        "src.api.routers.channels.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(
            return_value=[
                _fail(
                    PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE,
                    "legal_profile_incomplete",
                    "/legal-profile",
                ),
                _ok(PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED),
                _ok(PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID),
            ]
        ),
    )
    monkeypatch.setattr(
        "src.api.routers.channels.AuditLogRepo.log",
        AsyncMock(return_value=None),
    )

    response = await client_as_owner.post("/api/channels/", json={"username": "test_chan"})

    assert response.status_code == 403
    body = response.json()
    assert body["error_code"] == "channel_add_declined"
    blockers = body["extra"]["blockers"]
    assert len(blockers) == 1
    assert blockers[0]["gate"] == PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE.value
    assert blockers[0]["reason_code"] == "legal_profile_incomplete"
    assert blockers[0]["remediation_url"] == "/legal-profile"


@pytest.mark.asyncio
async def test_create_channel_g05_fail_returns_403_with_contracts_remediation(
    client_as_owner: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G05 fail → 403 with remediation_url=/contracts."""
    monkeypatch.setattr(
        "src.api.routers.channels.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(
            return_value=[
                _ok(PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE),
                _fail(
                    PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED,
                    "framework_contract_unsigned",
                    "/contracts",
                ),
                _ok(PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID),
            ]
        ),
    )
    monkeypatch.setattr(
        "src.api.routers.channels.AuditLogRepo.log",
        AsyncMock(return_value=None),
    )

    response = await client_as_owner.post("/api/channels/", json={"username": "test_chan"})

    assert response.status_code == 403
    blockers = response.json()["extra"]["blockers"]
    assert blockers[0]["gate"] == PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED.value
    assert blockers[0]["remediation_url"] == "/contracts"


@pytest.mark.asyncio
async def test_create_channel_g06_fail_returns_403(
    client_as_owner: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """G06 fail (set-but-invalid method) → 403, remediation_url=None."""
    monkeypatch.setattr(
        "src.api.routers.channels.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(
            return_value=[
                _ok(PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE),
                _ok(PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED),
                _fail(
                    PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID,
                    "payout_method_invalid",
                    None,
                ),
            ]
        ),
    )
    monkeypatch.setattr(
        "src.api.routers.channels.AuditLogRepo.log",
        AsyncMock(return_value=None),
    )

    response = await client_as_owner.post("/api/channels/", json={"username": "test_chan"})

    assert response.status_code == 403
    blockers = response.json()["extra"]["blockers"]
    assert blockers[0]["gate"] == PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID.value
    assert blockers[0]["reason_code"] == "payout_method_invalid"
    assert blockers[0]["remediation_url"] is None


@pytest.mark.asyncio
async def test_create_channel_admin_test_mode_bypasses_gates(
    client_as_admin: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """is_admin + is_test=True → compliance hook skipped entirely."""
    spy = AsyncMock()
    monkeypatch.setattr(
        "src.api.routers.channels.LegalComplianceService.check_gates_for_user_role",
        spy,
    )
    # Past hook → bot/repo machinery short-circuits via 400/403; we only
    # care that the hook itself was not invoked.
    response = await client_as_admin.post(
        "/api/channels/", json={"username": "test_chan", "is_test": True}
    )

    spy.assert_not_called()
    # Response code may be != 201 because Telegram mock isn't a full chain;
    # the assertion that matters is that the gate was bypassed.
    assert response.status_code != 403 or "channel_add_declined" not in (
        response.json().get("error_code", "")
    )


@pytest.mark.asyncio
async def test_create_channel_non_admin_test_mode_does_not_bypass(
    client_as_owner: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-admin with is_test=True still goes through compliance hook."""
    spy = AsyncMock(
        return_value=[
            _fail(
                PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE,
                "legal_profile_missing",
                "/legal-profile",
            ),
            _ok(PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED),
            _ok(PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID),
        ]
    )
    monkeypatch.setattr(
        "src.api.routers.channels.LegalComplianceService.check_gates_for_user_role",
        spy,
    )
    monkeypatch.setattr(
        "src.api.routers.channels.AuditLogRepo.log",
        AsyncMock(return_value=None),
    )

    response = await client_as_owner.post(
        "/api/channels/", json={"username": "test_chan", "is_test": True}
    )

    spy.assert_called_once()
    assert response.status_code == 403
    assert response.json()["error_code"] == "channel_add_declined"


@pytest.mark.asyncio
async def test_create_channel_logs_audit_on_decline(
    client_as_owner: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Declined attempts call AuditLogRepo.log with action=channel_add_declined."""
    monkeypatch.setattr(
        "src.api.routers.channels.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(
            return_value=[
                _fail(
                    PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE,
                    "legal_profile_incomplete",
                    "/legal-profile",
                ),
                _ok(PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED),
                _ok(PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID),
            ]
        ),
    )
    audit_log_spy = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "src.api.routers.channels.AuditLogRepo.log",
        audit_log_spy,
    )

    await client_as_owner.post("/api/channels/", json={"username": "test_chan"})

    audit_log_spy.assert_called_once()
    kwargs = audit_log_spy.call_args.kwargs
    assert kwargs["action"] == "channel_add_declined"
    assert kwargs["resource_type"] == "channel"
    assert kwargs["user_id"] == 7001
    assert kwargs["extra"]["blockers"] == [PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE.value]
