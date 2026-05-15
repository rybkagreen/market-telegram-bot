"""BL-107 Phase B.6 — periodic re-verification Celery task tests.

Pure unit tests, no DB connection, no live bot. Mocks:

* ``ephemeral_bot()`` / ``async_session_factory()`` — replaced with
  ``asynccontextmanager`` stubs yielding pre-built AsyncMock instances.
* ``bot.get_chat(...).get_member_count()`` — AsyncMock returning fixed
  member count.
* ``verify_trustchannelbot_admin`` — module-level monkeypatch.
* ``AuditLogRepo`` — class replaced with MagicMock so ``.log(...)`` calls
  don't touch the (mocked) session's ``begin_nested``.
* ``notify_owner_verification_lost`` — module-level monkeypatch с AsyncMock.

Verifies:

1. Feature-flag short-circuit
2. Empty channel set
3. Trustchannelbot still admin → ``still_verified`` ++
4. Trustchannelbot removed → reset fields + audit + notify
5. MANUAL_EVIDENCE channels NOT re-checked by Trustchannelbot logic
6. Threshold crossing counter increment
7. ``bot.get_chat`` exception → ``api_failures`` ++
8. TrustchannelbotResolutionError → ``api_failures`` ++, no reset
9. Member-count refresh counter increment
10. Multi-channel aggregation
11. ``session.commit()`` invoked once at task end
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.enums.blogger_registry import BloggerRegistryVerificationMethod
from src.tasks import channel_registry_tasks
from src.utils.telegram.verify_blogger_registry import TrustchannelbotResolutionError


def _make_chat(*, member_count: int) -> AsyncMock:
    """Build aiogram Chat-like async mock with get_member_count()."""
    chat = AsyncMock()
    chat.get_member_count = AsyncMock(return_value=member_count)
    return chat


def _make_channel(
    *,
    chat_id: int = 1,
    telegram_id: int = -100123,
    owner_id: int = 42,
    member_count: int = 15_000,
    member_count_at_verification: int | None = 15_000,
    is_blogger_registry_verified: bool = True,
    verification_method: BloggerRegistryVerificationMethod | None = (
        BloggerRegistryVerificationMethod.TRUSTCHANNELBOT_ADMIN
    ),
) -> MagicMock:
    """Build TelegramChat-like mock with mutable attributes."""
    channel = MagicMock()
    channel.id = chat_id
    channel.telegram_id = telegram_id
    channel.owner_id = owner_id
    channel.member_count = member_count
    channel.member_count_at_verification = member_count_at_verification
    channel.is_blogger_registry_verified = is_blogger_registry_verified
    channel.blogger_registry_verification_method = verification_method
    channel.blogger_registry_verified_at = datetime(2026, 5, 1, tzinfo=UTC)
    channel.blogger_registry_verified_by_admin_id = 99
    channel.last_blogger_registry_check_at = None
    return channel


def _patch_factories(
    monkeypatch: pytest.MonkeyPatch,
    *,
    channels: list[MagicMock],
    bot: AsyncMock,
) -> AsyncMock:
    """Replace ephemeral_bot + async_session_factory + return mocked session."""
    session = AsyncMock()
    session.commit = AsyncMock()

    scalars_result = MagicMock()
    scalars_result.scalars.return_value.all.return_value = channels
    session.execute = AsyncMock(return_value=scalars_result)

    @asynccontextmanager
    async def _bot_cm():
        yield bot

    @asynccontextmanager
    async def _sess_cm():
        yield session

    monkeypatch.setattr(channel_registry_tasks, "ephemeral_bot", _bot_cm)
    monkeypatch.setattr(channel_registry_tasks, "async_session_factory", _sess_cm)
    return session


def _patch_audit_and_notify(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[AsyncMock, AsyncMock]:
    """Stub AuditLogRepo + notify_owner_verification_lost."""
    audit_instance = MagicMock()
    audit_instance.log = AsyncMock()
    monkeypatch.setattr(
        channel_registry_tasks,
        "AuditLogRepo",
        MagicMock(return_value=audit_instance),
    )
    notify_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(channel_registry_tasks, "notify_owner_verification_lost", notify_mock)
    return audit_instance.log, notify_mock


@pytest.mark.asyncio
class TestPeriodicReVerificationTask:
    """BL-107 Phase B.6 — periodic Celery task scenarios."""

    async def test_feature_flag_disabled_short_circuits(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """rkn_periodic_check_enabled=False → no DB or bot work."""
        monkeypatch.setattr(channel_registry_tasks.settings, "rkn_periodic_check_enabled", False)
        result = await channel_registry_tasks._check_channel_registry_status_async()
        assert result == {"skipped": "disabled"}

    async def test_no_channels_match_criteria(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty channel set → counters all 0, task completes без errors."""
        monkeypatch.setattr(channel_registry_tasks.settings, "rkn_periodic_check_enabled", True)
        bot = AsyncMock()
        session = _patch_factories(monkeypatch, channels=[], bot=bot)
        _patch_audit_and_notify(monkeypatch)

        result = await channel_registry_tasks._check_channel_registry_status_async()

        assert result["processed"] == 0
        assert result["verification_lost"] == 0
        assert result["still_verified"] == 0
        session.commit.assert_awaited_once()

    async def test_trustchannelbot_still_admin_keeps_verification(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verified channel + Trustchannelbot все ещё admin → still_verified ++."""
        monkeypatch.setattr(channel_registry_tasks.settings, "rkn_periodic_check_enabled", True)
        channel = _make_channel()
        bot = AsyncMock()
        bot.get_chat = AsyncMock(return_value=_make_chat(member_count=15_000))
        _patch_factories(monkeypatch, channels=[channel], bot=bot)
        audit_log, notify_mock = _patch_audit_and_notify(monkeypatch)
        monkeypatch.setattr(
            channel_registry_tasks, "verify_trustchannelbot_admin", AsyncMock(return_value=True)
        )

        result = await channel_registry_tasks._check_channel_registry_status_async()

        assert result["processed"] == 1
        assert result["still_verified"] == 1
        assert result["verification_lost"] == 0
        assert channel.is_blogger_registry_verified is True
        audit_log.assert_not_awaited()
        notify_mock.assert_not_awaited()

    async def test_trustchannelbot_removed_resets_verification(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """@Trustchannelbot выпал → reset fields + audit log + owner notification."""
        monkeypatch.setattr(channel_registry_tasks.settings, "rkn_periodic_check_enabled", True)
        channel = _make_channel(chat_id=7, owner_id=42)
        bot = AsyncMock()
        bot.get_chat = AsyncMock(return_value=_make_chat(member_count=15_000))
        _patch_factories(monkeypatch, channels=[channel], bot=bot)
        audit_log, notify_mock = _patch_audit_and_notify(monkeypatch)
        monkeypatch.setattr(
            channel_registry_tasks, "verify_trustchannelbot_admin", AsyncMock(return_value=False)
        )

        result = await channel_registry_tasks._check_channel_registry_status_async()

        assert result["verification_lost"] == 1
        assert result["still_verified"] == 0
        assert channel.is_blogger_registry_verified is False
        assert channel.blogger_registry_verified_at is None
        assert channel.blogger_registry_verification_method is None
        assert channel.blogger_registry_verified_by_admin_id is None
        assert channel.member_count_at_verification is None

        audit_log.assert_awaited_once()
        audit_kwargs = audit_log.await_args.kwargs
        assert audit_kwargs["action"] == "blogger_registry_auto_unverified"
        assert audit_kwargs["resource_type"] == "telegram_chat"
        assert audit_kwargs["resource_id"] == 7
        assert audit_kwargs["user_id"] is None
        assert audit_kwargs["extra"]["reason"] == "trustchannelbot_no_longer_admin"

        notify_mock.assert_awaited_once()
        notify_kwargs = notify_mock.await_args.kwargs
        assert notify_kwargs["owner_user_id"] == 42
        assert notify_kwargs["channel_id"] == 7

    async def test_manual_evidence_channel_not_rechecked(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MANUAL_EVIDENCE method → verify_trustchannelbot_admin NOT called."""
        monkeypatch.setattr(channel_registry_tasks.settings, "rkn_periodic_check_enabled", True)
        channel = _make_channel(
            verification_method=BloggerRegistryVerificationMethod.MANUAL_EVIDENCE,
        )
        bot = AsyncMock()
        bot.get_chat = AsyncMock(return_value=_make_chat(member_count=15_000))
        _patch_factories(monkeypatch, channels=[channel], bot=bot)
        audit_log, notify_mock = _patch_audit_and_notify(monkeypatch)
        verify_mock = AsyncMock(return_value=False)
        monkeypatch.setattr(channel_registry_tasks, "verify_trustchannelbot_admin", verify_mock)

        result = await channel_registry_tasks._check_channel_registry_status_async()

        assert result["processed"] == 1
        assert result["still_verified"] == 0
        assert result["verification_lost"] == 0
        verify_mock.assert_not_awaited()
        audit_log.assert_not_awaited()
        notify_mock.assert_not_awaited()
        assert channel.is_blogger_registry_verified is True

    async def test_threshold_crossing_increments_counter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """member_count_at_verification < 10k AND current ≥ 10k → counter ++."""
        monkeypatch.setattr(channel_registry_tasks.settings, "rkn_periodic_check_enabled", True)
        channel = _make_channel(
            member_count=15_000,
            member_count_at_verification=8_000,
            is_blogger_registry_verified=True,
        )
        bot = AsyncMock()
        bot.get_chat = AsyncMock(return_value=_make_chat(member_count=15_000))
        _patch_factories(monkeypatch, channels=[channel], bot=bot)
        _patch_audit_and_notify(monkeypatch)
        monkeypatch.setattr(
            channel_registry_tasks, "verify_trustchannelbot_admin", AsyncMock(return_value=True)
        )

        result = await channel_registry_tasks._check_channel_registry_status_async()

        assert result["threshold_crossed"] == 1

    async def test_get_chat_exception_increments_api_failures(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """bot.get_chat raises → api_failures ++, no other side effects."""
        monkeypatch.setattr(channel_registry_tasks.settings, "rkn_periodic_check_enabled", True)
        channel = _make_channel()
        bot = AsyncMock()
        bot.get_chat = AsyncMock(side_effect=RuntimeError("Telegram down"))
        _patch_factories(monkeypatch, channels=[channel], bot=bot)
        audit_log, notify_mock = _patch_audit_and_notify(monkeypatch)

        result = await channel_registry_tasks._check_channel_registry_status_async()

        assert result["processed"] == 1
        assert result["api_failures"] == 1
        assert result["verification_lost"] == 0
        assert channel.is_blogger_registry_verified is True
        audit_log.assert_not_awaited()
        notify_mock.assert_not_awaited()

    async def test_trustchannelbot_resolution_error_no_reset(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """TrustchannelbotResolutionError = transient → api_failures, no reset."""
        monkeypatch.setattr(channel_registry_tasks.settings, "rkn_periodic_check_enabled", True)
        channel = _make_channel()
        bot = AsyncMock()
        bot.get_chat = AsyncMock(return_value=_make_chat(member_count=15_000))
        _patch_factories(monkeypatch, channels=[channel], bot=bot)
        audit_log, notify_mock = _patch_audit_and_notify(monkeypatch)
        monkeypatch.setattr(
            channel_registry_tasks,
            "verify_trustchannelbot_admin",
            AsyncMock(side_effect=TrustchannelbotResolutionError("cache miss + API down")),
        )

        result = await channel_registry_tasks._check_channel_registry_status_async()

        assert result["api_failures"] == 1
        assert result["verification_lost"] == 0
        assert channel.is_blogger_registry_verified is True
        audit_log.assert_not_awaited()
        notify_mock.assert_not_awaited()

    async def test_member_count_refresh_increments_counter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Member count changed → field updated + counter incremented."""
        monkeypatch.setattr(channel_registry_tasks.settings, "rkn_periodic_check_enabled", True)
        channel = _make_channel(member_count=15_000)
        bot = AsyncMock()
        bot.get_chat = AsyncMock(return_value=_make_chat(member_count=17_500))
        _patch_factories(monkeypatch, channels=[channel], bot=bot)
        _patch_audit_and_notify(monkeypatch)
        monkeypatch.setattr(
            channel_registry_tasks, "verify_trustchannelbot_admin", AsyncMock(return_value=True)
        )

        result = await channel_registry_tasks._check_channel_registry_status_async()

        assert result["member_count_refreshed"] == 1
        assert channel.member_count == 17_500

    async def test_multiple_channels_aggregate_counters(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """3 channels с mixed outcomes → counters aggregate correctly."""
        monkeypatch.setattr(channel_registry_tasks.settings, "rkn_periodic_check_enabled", True)
        still_ok = _make_channel(chat_id=1, telegram_id=-1001)
        lost = _make_channel(chat_id=2, telegram_id=-1002)
        manual = _make_channel(
            chat_id=3,
            telegram_id=-1003,
            verification_method=BloggerRegistryVerificationMethod.MANUAL_EVIDENCE,
        )
        bot = AsyncMock()
        bot.get_chat = AsyncMock(return_value=_make_chat(member_count=15_000))
        _patch_factories(monkeypatch, channels=[still_ok, lost, manual], bot=bot)
        _patch_audit_and_notify(monkeypatch)

        async def _verify(_bot, chat_id):  # type: ignore[no-untyped-def]
            return chat_id != lost.telegram_id

        monkeypatch.setattr(
            channel_registry_tasks, "verify_trustchannelbot_admin", AsyncMock(side_effect=_verify)
        )

        result = await channel_registry_tasks._check_channel_registry_status_async()

        assert result["processed"] == 3
        assert result["still_verified"] == 1
        assert result["verification_lost"] == 1

    async def test_session_commit_called_once(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """session.commit() called exactly once at task end, not per-channel."""
        monkeypatch.setattr(channel_registry_tasks.settings, "rkn_periodic_check_enabled", True)
        channels = [_make_channel(chat_id=i) for i in range(1, 4)]
        bot = AsyncMock()
        bot.get_chat = AsyncMock(return_value=_make_chat(member_count=15_000))
        session = _patch_factories(monkeypatch, channels=channels, bot=bot)
        _patch_audit_and_notify(monkeypatch)
        monkeypatch.setattr(
            channel_registry_tasks, "verify_trustchannelbot_admin", AsyncMock(return_value=True)
        )

        await channel_registry_tasks._check_channel_registry_status_async()

        assert session.commit.await_count == 1
