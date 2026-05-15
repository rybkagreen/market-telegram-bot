"""Unit tests for bot handler add_channel_confirm — Phase 3b §3.B.6 (5b.7a).

Verifies the bot-side compliance hook mirrors the API-side enforcement:

* Happy path: gates pass → TelegramChat + ChannelSettings persisted, FSM cleared.
* Decline path: any owner gate fails → callback alert + edit_text with
  remediation lines, FSM cleared, NO TelegramChat created.

Mocks the FSMContext and the AsyncSession; LegalComplianceService is patched
to return canned gate results so the handler logic is the unit under test.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.owner.channel_owner import add_channel_confirm
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.user import User

pytestmark = pytest.mark.asyncio


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


def _make_callback() -> MagicMock:
    cb = MagicMock()
    cb.from_user = MagicMock(id=100_000)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    return cb


def _make_state() -> MagicMock:
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value={
            "channel_telegram_id": 555,
            "username": "test_chan",
            "title": "Test Chan",
            "member_count": 1000,
            "category": None,
        }
    )
    state.clear = AsyncMock()
    return state


def _make_session() -> MagicMock:
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture(autouse=True)
def _patch_message_isinstance(monkeypatch: pytest.MonkeyPatch) -> None:
    """``isinstance(callback.message, Message)`` early-returns; bypass with patch."""
    import src.bot.handlers.owner.channel_owner as mod

    monkeypatch.setattr(mod, "isinstance", lambda obj, cls: True, raising=False)


async def test_add_channel_confirm_happy_path_creates_channel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All gates pass → session.add called for TelegramChat + ChannelSettings.

    Phase B.4: mocks `verify_trustchannelbot_admin` (helper hits Telegram API);
    G19 channel-add gate runs real on FSM data member_count=1000 (<10k threshold),
    so G19 returns passed=True naturally regardless of is_verified value.
    """
    session = _make_session()
    callback = _make_callback()
    state = _make_state()

    user = User(id=42, telegram_id=100_000, username="owner", first_name="Owner")
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.UserRepository",
        lambda s: MagicMock(get_by_telegram_id=AsyncMock(return_value=user)),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(
            return_value=[
                _ok(PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE),
                _ok(PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED),
                _ok(PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID),
            ]
        ),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.verify_trustchannelbot_admin",
        AsyncMock(return_value=False),
    )

    await add_channel_confirm(callback, state, session)

    # TelegramChat + ChannelSettings both added
    assert session.add.call_count == 2
    callback.answer.assert_called()
    state.clear.assert_called_once()


async def test_add_channel_confirm_gates_fail_no_channel_created(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Any gate fail → no TelegramChat created, FSM cleared."""
    session = _make_session()
    callback = _make_callback()
    state = _make_state()

    user = User(id=42, telegram_id=100_000, username="owner", first_name="Owner")
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.UserRepository",
        lambda s: MagicMock(get_by_telegram_id=AsyncMock(return_value=user)),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.LegalComplianceService.check_gates_for_user_role",
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
        "src.bot.handlers.owner.channel_owner.AuditLogRepo",
        lambda s: MagicMock(log=AsyncMock(return_value=None)),
    )

    await add_channel_confirm(callback, state, session)

    session.add.assert_not_called()
    callback.message.edit_text.assert_called_once()
    state.clear.assert_called_once()


async def test_add_channel_confirm_remediation_message_includes_blocker_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decline message must include gate name + reason in user-facing text."""
    session = _make_session()
    callback = _make_callback()
    state = _make_state()

    user = User(id=42, telegram_id=100_000, username="owner", first_name="Owner")
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.UserRepository",
        lambda s: MagicMock(get_by_telegram_id=AsyncMock(return_value=user)),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(
            return_value=[
                _fail(
                    PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED,
                    "framework_contract_unsigned",
                    "/contracts",
                ),
                _ok(PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE),
                _ok(PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID),
            ]
        ),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.AuditLogRepo",
        lambda s: MagicMock(log=AsyncMock(return_value=None)),
    )

    await add_channel_confirm(callback, state, session)

    call_args = callback.message.edit_text.call_args
    text_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("text", "")
    assert PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED.value in text_arg
    assert "framework_contract_unsigned" in text_arg
    assert "/contracts" in text_arg


async def test_add_channel_confirm_logs_audit_on_decline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bot decline path also writes channel_add_declined audit entry."""
    session = _make_session()
    callback = _make_callback()
    state = _make_state()

    user = User(id=42, telegram_id=100_000, username="owner", first_name="Owner")
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.UserRepository",
        lambda s: MagicMock(get_by_telegram_id=AsyncMock(return_value=user)),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.LegalComplianceService.check_gates_for_user_role",
        AsyncMock(
            return_value=[
                _fail(
                    PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID,
                    "payout_method_invalid",
                    None,
                ),
                _ok(PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE),
                _ok(PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED),
            ]
        ),
    )
    audit_log = MagicMock(log=AsyncMock(return_value=None))
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.AuditLogRepo",
        lambda s: audit_log,
    )

    await add_channel_confirm(callback, state, session)

    audit_log.log.assert_called_once()
    kwargs = audit_log.log.call_args.kwargs
    assert kwargs["action"] == "channel_add_declined"
    assert kwargs["resource_type"] == "channel"
    assert kwargs["user_id"] == 42
