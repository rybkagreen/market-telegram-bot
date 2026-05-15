"""Unit tests for BL-107 Phase B.7 — O.7 carve-out closure (bot is_test parity).

Verifies bot/API symmetry for is_test channel creation:

* Admin user reaches selecting_is_test state after category selection.
* Non-admin user proceeds directly к confirming (is_test=False default).
* Admin choosing test=1 / test=0 captures FSM choice + transitions к confirming.
* Defense-in-depth: non-admin somehow reaching is_test handler → rejected.
* add_channel_confirm reads is_test from FSM data (not hardcoded False).
* add_channel_confirm defense-in-depth: is_test=True + non-admin → rejected.

Pure unit tests — mocks FSMContext, AsyncSession, UserRepository, CategoryRepo,
and LegalComplianceService. No DB, no Telegram API.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.owner.channel_owner import (
    add_channel_confirm,
    add_channel_select_category,
    add_channel_select_is_test,
)
from src.bot.states.channel_owner import AddChannelStates
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.user import User

pytestmark = pytest.mark.asyncio


def _ok(gate: PlacementGate) -> GateResult:
    return GateResult(gate=gate, passed=True, blocker=True, reason_code="ok")


def _make_callback(*, callback_data: str = "own:add_channel:cat:tech") -> MagicMock:
    cb = MagicMock()
    cb.from_user = MagicMock(id=100_000)
    cb.message = MagicMock()
    cb.message.edit_text = AsyncMock()
    cb.answer = AsyncMock()
    cb.data = callback_data
    return cb


def _make_state(*, data: dict | None = None) -> MagicMock:
    state = MagicMock()
    state.get_data = AsyncMock(
        return_value=data
        if data is not None
        else {
            "channel_telegram_id": 555,
            "username": "test_chan",
            "title": "Test Chan",
            "member_count": 1000,
            "can_post": True,
            "can_delete": True,
            "can_pin": True,
        }
    )
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.clear = AsyncMock()
    return state


def _make_session() -> MagicMock:
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


def _make_user(*, is_admin: bool = False) -> User:
    user = User(id=42, telegram_id=100_000, username="owner", first_name="Owner")
    user.is_admin = is_admin
    return user


def _make_category() -> MagicMock:
    cat = MagicMock()
    cat.slug = "tech"
    cat.emoji = "💻"
    cat.name_ru = "Технологии"
    return cat


@pytest.fixture(autouse=True)
def _patch_isinstance(monkeypatch: pytest.MonkeyPatch) -> None:
    """``isinstance(callback.message, Message)`` early-returns; bypass."""
    import src.bot.handlers.owner.channel_owner as mod

    monkeypatch.setattr(mod, "isinstance", lambda obj, cls: True, raising=False)


def _patch_repos(monkeypatch: pytest.MonkeyPatch, *, user: User, category: MagicMock) -> None:
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.UserRepository",
        lambda s: MagicMock(get_by_telegram_id=AsyncMock(return_value=user)),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.CategoryRepo",
        lambda s: MagicMock(get_by_slug=AsyncMock(return_value=category)),
    )


# ─── add_channel_select_category branching ──────────────────────────────────


async def test_admin_reaches_selecting_is_test_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Admin user после category selection переходит в selecting_is_test, видит keyboard."""
    session = _make_session()
    callback = _make_callback()
    state = _make_state()
    _patch_repos(monkeypatch, user=_make_user(is_admin=True), category=_make_category())

    await add_channel_select_category(callback, state, session)

    state.set_state.assert_awaited_with(AddChannelStates.selecting_is_test)
    callback.message.edit_text.assert_awaited_once()
    edit_kwargs = callback.message.edit_text.await_args.kwargs
    assert "Тип канала" in edit_kwargs.get("text", "") or "Тип канала" in (
        callback.message.edit_text.await_args.args[0]
        if callback.message.edit_text.await_args.args
        else ""
    )
    assert edit_kwargs.get("reply_markup") is not None


async def test_non_admin_skips_is_test_goes_directly_to_confirming(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-admin user → state=confirming с is_test=False default."""
    session = _make_session()
    callback = _make_callback()
    state = _make_state()
    _patch_repos(monkeypatch, user=_make_user(is_admin=False), category=_make_category())

    await add_channel_select_category(callback, state, session)

    state.set_state.assert_awaited_with(AddChannelStates.confirming)
    # update_data вызывается дважды: category, then is_test=False
    update_calls = state.update_data.await_args_list
    is_test_calls = [c for c in update_calls if "is_test" in c.kwargs]
    assert len(is_test_calls) == 1
    assert is_test_calls[0].kwargs["is_test"] is False


# ─── add_channel_select_is_test handler ─────────────────────────────────────


async def test_admin_chooses_test_true_sets_fsm_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Admin clicks 'Тестовый' → FSM data['is_test']=True, state=confirming."""
    session = _make_session()
    callback = _make_callback(callback_data="own:add_channel:is_test:1")
    state = _make_state(
        data={
            "channel_telegram_id": 555,
            "username": "test_chan",
            "title": "Test Chan",
            "member_count": 1000,
            "category": "tech",
            "can_post": True,
            "can_delete": True,
            "can_pin": True,
        }
    )
    _patch_repos(monkeypatch, user=_make_user(is_admin=True), category=_make_category())

    await add_channel_select_is_test(callback, state, session)

    state.update_data.assert_any_await(is_test=True)
    state.set_state.assert_awaited_with(AddChannelStates.confirming)


async def test_admin_chooses_test_false_sets_fsm_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Admin clicks 'Реальный' → FSM data['is_test']=False, state=confirming."""
    session = _make_session()
    callback = _make_callback(callback_data="own:add_channel:is_test:0")
    state = _make_state(
        data={
            "channel_telegram_id": 555,
            "username": "test_chan",
            "title": "Test Chan",
            "member_count": 1000,
            "category": "tech",
            "can_post": True,
            "can_delete": True,
            "can_pin": True,
        }
    )
    _patch_repos(monkeypatch, user=_make_user(is_admin=True), category=_make_category())

    await add_channel_select_is_test(callback, state, session)

    state.update_data.assert_any_await(is_test=False)
    state.set_state.assert_awaited_with(AddChannelStates.confirming)


async def test_non_admin_blocked_at_is_test_handler(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defense-in-depth: non-admin reaching is_test handler → rejected, FSM cleared."""
    session = _make_session()
    callback = _make_callback(callback_data="own:add_channel:is_test:1")
    state = _make_state(
        data={
            "channel_telegram_id": 555,
            "username": "test_chan",
            "title": "Test Chan",
            "member_count": 1000,
            "category": "tech",
        }
    )
    _patch_repos(monkeypatch, user=_make_user(is_admin=False), category=_make_category())

    await add_channel_select_is_test(callback, state, session)

    callback.answer.assert_awaited_once()
    answer_args = callback.answer.await_args
    assert answer_args.kwargs.get("show_alert") is True
    state.clear.assert_awaited_once()
    # is_test NOT captured
    is_test_updates = [c for c in state.update_data.await_args_list if "is_test" in c.kwargs]
    assert is_test_updates == []


# ─── add_channel_confirm reads is_test from FSM ─────────────────────────────


async def test_add_channel_confirm_uses_is_test_from_fsm_for_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Admin с FSM is_test=True → TelegramChat created с is_test=True."""
    session = _make_session()
    callback = _make_callback()
    state = _make_state(
        data={
            "channel_telegram_id": 555,
            "username": "test_chan",
            "title": "Test Chan",
            "member_count": 1000,
            "category": "tech",
            "is_test": True,
        }
    )

    user = _make_user(is_admin=True)
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
        "src.bot.handlers.owner.channel_owner.LegalComplianceService.check_gates_for_channel_add",
        AsyncMock(return_value=[_ok(PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED)]),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.verify_trustchannelbot_admin",
        AsyncMock(return_value=False),
    )

    await add_channel_confirm(callback, state, session)

    # TelegramChat создан с is_test=True
    assert session.add.call_count == 2  # TelegramChat + ChannelSettings
    telegram_chat_arg = session.add.call_args_list[0].args[0]
    assert telegram_chat_arg.is_test is True


async def test_add_channel_confirm_defense_in_depth_non_admin_with_is_test_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defense-in-depth: non-admin reaching confirm с FSM is_test=True → rejected."""
    session = _make_session()
    callback = _make_callback()
    state = _make_state(
        data={
            "channel_telegram_id": 555,
            "username": "test_chan",
            "title": "Test Chan",
            "member_count": 1000,
            "category": "tech",
            "is_test": True,  # poisoned FSM state (theoretically unreachable)
        }
    )

    user = _make_user(is_admin=False)
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.UserRepository",
        lambda s: MagicMock(get_by_telegram_id=AsyncMock(return_value=user)),
    )

    await add_channel_confirm(callback, state, session)

    callback.answer.assert_awaited_once()
    answer_args = callback.answer.await_args
    assert answer_args.kwargs.get("show_alert") is True
    state.clear.assert_awaited_once()
    session.add.assert_not_called()


async def test_add_channel_confirm_uses_is_test_false_default_for_non_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-admin path с no is_test в FSM data → default False, channel created."""
    session = _make_session()
    callback = _make_callback()
    state = _make_state(
        data={
            "channel_telegram_id": 555,
            "username": "test_chan",
            "title": "Test Chan",
            "member_count": 1000,
            "category": "tech",
            # is_test absent — default False
        }
    )

    user = _make_user(is_admin=False)
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
        "src.bot.handlers.owner.channel_owner.LegalComplianceService.check_gates_for_channel_add",
        AsyncMock(return_value=[_ok(PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED)]),
    )
    monkeypatch.setattr(
        "src.bot.handlers.owner.channel_owner.verify_trustchannelbot_admin",
        AsyncMock(return_value=False),
    )

    await add_channel_confirm(callback, state, session)

    assert session.add.call_count == 2
    telegram_chat_arg = session.add.call_args_list[0].args[0]
    assert telegram_chat_arg.is_test is False
