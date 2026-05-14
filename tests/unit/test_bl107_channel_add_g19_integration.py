"""BL-107 Phase B.4 — Channel-add G19 integration tests.

Covers wiring of `verify_trustchannelbot_admin` + `check_gates_for_channel_add`
+ verification audit fields population в both:
- API router `src/api/routers/channels.py` create_channel endpoint
- Bot handler `src/bot/handlers/owner/channel_owner.py` add_channel_confirm

Mocks at boundaries (helper + LegalComplianceService methods) — no live Telegram
API, no DB. Tests verify wiring correctness, not gate body logic (covered в
Phase B.2 G19 tests).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_bot, get_current_user, get_db_session
from src.api.main import app
from src.bot.handlers.owner.channel_owner import add_channel_confirm
from src.core.enums.blogger_registry import BloggerRegistryVerificationMethod
from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.user import User

# ─── Helpers ───────────────────────────────────────────────────────────────


def _ok(gate: PlacementGate) -> GateResult:
    return GateResult(gate=gate, passed=True, blocker=False, reason_code="ok")


def _fail(gate: PlacementGate, reason: str) -> GateResult:
    return GateResult(
        gate=gate, passed=False, blocker=True, reason_code=reason, remediation_url=None
    )


@pytest.fixture
def owner_user() -> User:
    return User(id=7001, telegram_id=100_000, username="owner", first_name="Owner", is_admin=False)


@pytest.fixture
def admin_user() -> User:
    return User(id=9001, telegram_id=900_000, username="admin", first_name="Admin", is_admin=True)


async def _stub_session_dep() -> AsyncGenerator[Any]:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )
    session.refresh = AsyncMock()
    session.add = MagicMock()
    yield session


def _bot_dep_factory(member_count: int = 100) -> Any:
    """Builds bot mock с configurable member_count for G19 threshold tests.

    bot.get_chat_member returns MagicMock(spec=ChatMemberAdministrator) so
    `isinstance(chat_member, ChatMemberAdministrator)` passes — tests reach
    G19 wiring downstream.
    """
    from telegram import ChatMemberAdministrator

    bot = MagicMock()
    chat = MagicMock()
    chat.id = 1
    chat.type = "channel"
    chat.title = "Test"
    chat.username = "test_chan"
    chat.description = "Test description"
    chat.get_member_count = AsyncMock(return_value=member_count)
    bot.get_chat = AsyncMock(return_value=chat)
    # spec= makes isinstance(mock, ChatMemberAdministrator) return True
    chat_member_admin = MagicMock(spec=ChatMemberAdministrator)
    bot.get_chat_member = AsyncMock(return_value=chat_member_admin)
    bot.id = 999
    return bot


@pytest_asyncio.fixture
async def client_as_owner(owner_user: User) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_current_user] = lambda: owner_user
    app.dependency_overrides[get_db_session] = _stub_session_dep
    app.dependency_overrides[get_bot] = lambda: _bot_dep_factory(member_count=100)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_as_owner_large_channel(owner_user: User) -> AsyncGenerator[AsyncClient]:
    """Owner client с bot returning member_count=50_000 (≥10k threshold)."""
    app.dependency_overrides[get_current_user] = lambda: owner_user
    app.dependency_overrides[get_db_session] = _stub_session_dep
    app.dependency_overrides[get_bot] = lambda: _bot_dep_factory(member_count=50_000)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


def _ok_user_role_gates() -> list[GateResult]:
    return [
        _ok(PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE),
        _ok(PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED),
        _ok(PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID),
    ]


# ─── API router scenarios ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_below_threshold_creates_channel_audit_minimum(
    client_as_owner: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """<10k channel — G19 passes, audit fields minimum (last_check_at only)."""
    monkeypatch.setattr(
        "src.api.routers.channels.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(return_value=_ok_user_role_gates()),
    )
    monkeypatch.setattr(
        "src.api.routers.channels.verify_trustchannelbot_admin",
        AsyncMock(return_value=False),
    )

    captured: dict[str, Any] = {}

    async def fake_create(self, data):
        captured.update(data)
        new_ch = MagicMock()
        new_ch.id = 1
        new_ch.telegram_id = 1
        new_ch.username = "test_chan"
        new_ch.title = "Test"
        new_ch.owner_id = 7001
        new_ch.member_count = 100
        new_ch.last_er = 0.0
        new_ch.avg_views = 0
        new_ch.rating = 0.0
        new_ch.category = None
        new_ch.is_active = True
        new_ch.is_test = False
        new_ch.created_at = MagicMock(isoformat=lambda: "2026-05-14T00:00:00")
        return new_ch

    monkeypatch.setattr(
        "src.db.repositories.telegram_chat_repo.TelegramChatRepository.create", fake_create
    )

    response = await client_as_owner.post("/api/channels/", json={"username": "test_chan"})

    assert response.status_code == 200
    assert captured["is_blogger_registry_verified"] is False
    assert captured["blogger_registry_verified_at"] is None
    assert captured["blogger_registry_verification_method"] is None
    assert captured["member_count_at_verification"] is None
    assert captured["last_blogger_registry_check_at"] is not None  # check timestamp set


@pytest.mark.asyncio
async def test_api_verified_channel_creates_with_audit(
    client_as_owner_large_channel: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """≥10k + Trustchannelbot admin → channel created with TRUSTCHANNELBOT_ADMIN method."""
    monkeypatch.setattr(
        "src.api.routers.channels.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(return_value=_ok_user_role_gates()),
    )
    monkeypatch.setattr(
        "src.api.routers.channels.verify_trustchannelbot_admin",
        AsyncMock(return_value=True),
    )

    captured: dict[str, Any] = {}

    async def fake_create(self, data):
        captured.update(data)
        new_ch = MagicMock()
        new_ch.id = 1
        new_ch.telegram_id = 1
        new_ch.username = "big_chan"
        new_ch.title = "Big"
        new_ch.owner_id = 7001
        new_ch.member_count = 50_000
        new_ch.last_er = 0.0
        new_ch.avg_views = 0
        new_ch.rating = 0.0
        new_ch.category = None
        new_ch.is_active = True
        new_ch.is_test = False
        new_ch.created_at = MagicMock(isoformat=lambda: "2026-05-14T00:00:00")
        return new_ch

    monkeypatch.setattr(
        "src.db.repositories.telegram_chat_repo.TelegramChatRepository.create", fake_create
    )

    response = await client_as_owner_large_channel.post(
        "/api/channels/", json={"username": "big_chan"}
    )

    assert response.status_code == 200
    assert captured["is_blogger_registry_verified"] is True
    assert captured["blogger_registry_verified_at"] is not None
    assert (
        captured["blogger_registry_verification_method"]
        == BloggerRegistryVerificationMethod.TRUSTCHANNELBOT_ADMIN
    )
    assert captured["member_count_at_verification"] == 50_000
    assert captured["last_blogger_registry_check_at"] is not None


@pytest.mark.asyncio
async def test_api_large_channel_unverified_blocked_g19(
    client_as_owner_large_channel: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """≥10k без Trustchannelbot → 403 channel_add_declined с G19 blocker."""
    monkeypatch.setattr(
        "src.api.routers.channels.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(return_value=_ok_user_role_gates()),
    )
    monkeypatch.setattr(
        "src.api.routers.channels.verify_trustchannelbot_admin",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr("src.api.routers.channels.AuditLogRepo.log", AsyncMock(return_value=None))

    response = await client_as_owner_large_channel.post(
        "/api/channels/", json={"username": "big_chan"}
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error_code"] == "channel_add_declined"
    blockers = body["extra"]["blockers"]
    assert len(blockers) == 1
    assert blockers[0]["gate"] == PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED.value
    assert blockers[0]["reason_code"] == GateReason.BLOGGER_REGISTRY_NOT_VERIFIED.value


@pytest.mark.asyncio
async def test_api_trustchannelbot_resolution_error_blocked(
    client_as_owner_large_channel: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TrustchannelbotResolutionError → 403 с SUBSCRIBER_COUNT_UNKNOWN."""
    from src.utils.telegram.verify_blogger_registry import TrustchannelbotResolutionError

    monkeypatch.setattr(
        "src.api.routers.channels.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(return_value=_ok_user_role_gates()),
    )
    monkeypatch.setattr(
        "src.api.routers.channels.verify_trustchannelbot_admin",
        AsyncMock(side_effect=TrustchannelbotResolutionError("API down")),
    )
    monkeypatch.setattr("src.api.routers.channels.AuditLogRepo.log", AsyncMock(return_value=None))

    response = await client_as_owner_large_channel.post(
        "/api/channels/", json={"username": "big_chan"}
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error_code"] == "channel_add_declined"
    blockers = body["extra"]["blockers"]
    assert len(blockers) == 1
    assert blockers[0]["gate"] == PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED.value
    assert blockers[0]["reason_code"] == GateReason.SUBSCRIBER_COUNT_UNKNOWN.value


@pytest.mark.asyncio
async def test_api_admin_test_bypass_skips_g19(monkeypatch: pytest.MonkeyPatch) -> None:
    """Admin + is_test=True → G19 verify_trustchannelbot_admin NOT called."""
    admin = User(id=9001, telegram_id=900_000, username="admin", first_name="Admin", is_admin=True)
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_db_session] = _stub_session_dep
    app.dependency_overrides[get_bot] = lambda: _bot_dep_factory(member_count=50_000)

    user_role_spy = AsyncMock()
    monkeypatch.setattr(
        "src.api.routers.channels.LegalComplianceService.check_gates_for_user_role",
        user_role_spy,
    )
    verify_spy = AsyncMock()
    monkeypatch.setattr("src.api.routers.channels.verify_trustchannelbot_admin", verify_spy)

    async def fake_create(self, data):
        new_ch = MagicMock()
        new_ch.id = 1
        new_ch.telegram_id = 1
        new_ch.username = "test_chan"
        new_ch.title = "Test"
        new_ch.owner_id = 9001
        new_ch.member_count = 50_000
        new_ch.last_er = 0.0
        new_ch.avg_views = 0
        new_ch.rating = 0.0
        new_ch.category = None
        new_ch.is_active = True
        new_ch.is_test = True
        new_ch.created_at = MagicMock(isoformat=lambda: "2026-05-14T00:00:00")
        return new_ch

    monkeypatch.setattr(
        "src.db.repositories.telegram_chat_repo.TelegramChatRepository.create", fake_create
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/channels/", json={"username": "test_chan", "is_test": True}
        )

    user_role_spy.assert_not_called()  # compliance skipped per existing admin_test_bypass
    verify_spy.assert_not_called()  # G19 ALSO skipped per same bypass
    # Admin test bypass passes through happily (200) when fake_create matches
    assert response.status_code == 200

    app.dependency_overrides.clear()


# ─── Bot handler scenarios ─────────────────────────────────────────────────


def _make_bot_callback() -> MagicMock:
    cb = MagicMock()
    cb.from_user = MagicMock(id=100_000)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.message.bot = MagicMock()
    cb.answer = AsyncMock()
    return cb


def _make_bot_state(member_count: int = 1000) -> MagicMock:
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "channel_telegram_id": 555,
            "username": "test_chan",
            "title": "Test Chan",
            "member_count": member_count,
            "category": None,
        }
    )
    state.clear = AsyncMock()
    return state


def _make_bot_session() -> MagicMock:
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture(autouse=True)
def _patch_message_isinstance(monkeypatch: pytest.MonkeyPatch) -> None:
    """``isinstance(callback.message, Message)`` early-returns; bypass with patch."""
    import src.bot.handlers.owner.channel_owner as mod

    monkeypatch.setattr(mod, "isinstance", lambda obj, cls: True, raising=False)


@pytest.mark.asyncio
async def test_bot_below_threshold_creates_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bot handler: <10k → channel created with minimal audit (last_check_at only)."""
    session = _make_bot_session()
    callback = _make_bot_callback()
    state = _make_bot_state(member_count=1000)

    user = User(id=42, telegram_id=100_000, username="owner", first_name="Owner")
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.UserRepository",
        lambda s: MagicMock(get_by_telegram_id=AsyncMock(return_value=user)),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(return_value=_ok_user_role_gates()),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.verify_trustchannelbot_admin",
        AsyncMock(return_value=False),
    )

    await add_channel_confirm(callback, state, session)

    # TelegramChat + ChannelSettings added
    assert session.add.call_count == 2
    # Inspect TelegramChat audit fields (first session.add call)
    ch = session.add.call_args_list[0].args[0]
    assert ch.is_blogger_registry_verified is False
    assert ch.blogger_registry_verified_at is None
    assert ch.blogger_registry_verification_method is None
    assert ch.member_count_at_verification is None
    assert ch.last_blogger_registry_check_at is not None  # check timestamp set


@pytest.mark.asyncio
async def test_bot_verified_large_channel_audit_full(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bot handler: ≥10k + verified → all audit fields populated."""
    session = _make_bot_session()
    callback = _make_bot_callback()
    state = _make_bot_state(member_count=50_000)

    user = User(id=42, telegram_id=100_000, username="owner", first_name="Owner")
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.UserRepository",
        lambda s: MagicMock(get_by_telegram_id=AsyncMock(return_value=user)),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(return_value=_ok_user_role_gates()),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.verify_trustchannelbot_admin",
        AsyncMock(return_value=True),
    )

    await add_channel_confirm(callback, state, session)

    assert session.add.call_count == 2
    ch = session.add.call_args_list[0].args[0]
    assert ch.is_blogger_registry_verified is True
    assert ch.blogger_registry_verified_at is not None
    assert (
        ch.blogger_registry_verification_method
        == BloggerRegistryVerificationMethod.TRUSTCHANNELBOT_ADMIN
    )
    assert ch.member_count_at_verification == 50_000
    assert ch.last_blogger_registry_check_at is not None


@pytest.mark.asyncio
async def test_bot_large_channel_unverified_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bot handler: ≥10k без verification → no channel created, user-facing message."""
    session = _make_bot_session()
    callback = _make_bot_callback()
    state = _make_bot_state(member_count=50_000)

    user = User(id=42, telegram_id=100_000, username="owner", first_name="Owner")
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.UserRepository",
        lambda s: MagicMock(get_by_telegram_id=AsyncMock(return_value=user)),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(return_value=_ok_user_role_gates()),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.verify_trustchannelbot_admin",
        AsyncMock(return_value=False),
    )
    audit_log_spy = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.AuditLogRepo",
        lambda s: MagicMock(log=audit_log_spy),
    )

    await add_channel_confirm(callback, state, session)

    # No TelegramChat OR ChannelSettings added
    session.add.assert_not_called()
    # User-facing error message shown
    callback.message.edit_text.assert_called_once()
    state.clear.assert_called_once()
    # Audit log written с G19 blocker
    audit_log_spy.assert_called_once()
    kwargs = audit_log_spy.call_args.kwargs
    assert kwargs["action"] == "channel_add_declined"
    assert PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED.value in kwargs["extra"]["blockers"]


@pytest.mark.asyncio
async def test_bot_trustchannelbot_resolution_error_user_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bot handler: API failure → user-facing message, no channel created."""
    from src.utils.telegram.verify_blogger_registry import TrustchannelbotResolutionError

    session = _make_bot_session()
    callback = _make_bot_callback()
    state = _make_bot_state(member_count=50_000)

    user = User(id=42, telegram_id=100_000, username="owner", first_name="Owner")
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.UserRepository",
        lambda s: MagicMock(get_by_telegram_id=AsyncMock(return_value=user)),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(return_value=_ok_user_role_gates()),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.verify_trustchannelbot_admin",
        AsyncMock(side_effect=TrustchannelbotResolutionError("API down")),
    )
    audit_log_spy = AsyncMock(return_value=None)
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.AuditLogRepo",
        lambda s: MagicMock(log=audit_log_spy),
    )

    await add_channel_confirm(callback, state, session)

    session.add.assert_not_called()
    callback.answer.assert_called()
    state.clear.assert_called_once()
    # Audit logged
    audit_log_spy.assert_called_once()
