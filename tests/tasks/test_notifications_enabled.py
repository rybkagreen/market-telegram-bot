"""Tests for notifications_enabled enforcement across tasks (S-37)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─── helpers ───────────────────────────────────────────────────────────────────


def _make_user(user_id: int = 1, telegram_id: int = 123456789, enabled: bool = True):
    user = MagicMock()
    user.id = user_id
    user.telegram_id = telegram_id
    user.notifications_enabled = enabled
    return user


# ─── _notify_user_checked ──────────────────────────────────────────────────────


class TestNotifyUserChecked:
    """Unit tests for notification_tasks._notify_user_checked."""

    @pytest.fixture(autouse=True)
    def _patch_factory(self):
        """Patch Bot factory to avoid real network calls."""
        with patch("src.tasks._bot_factory.Bot"):
            import src.tasks._bot_factory as fac
            fac._bot = MagicMock()
            yield
            fac._bot = None

    def _run(self, coro):
        return asyncio.run(coro)

    def test_returns_false_when_notifications_disabled(self):
        user = _make_user(enabled=False)
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = user

        with (
            patch(
                "src.tasks.notification_tasks.UserRepository",
                return_value=mock_repo,
            ),
            patch("src.tasks.notification_tasks.async_session_factory") as mock_factory,
        ):
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tasks.notification_tasks import _notify_user_checked

            result = self._run(_notify_user_checked(user.id, "hello"))

        assert result is False

    def test_returns_false_when_user_not_found(self):
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        with (
            patch(
                "src.tasks.notification_tasks.UserRepository",
                return_value=mock_repo,
            ),
            patch("src.tasks.notification_tasks.async_session_factory") as mock_factory,
        ):
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tasks.notification_tasks import _notify_user_checked

            result = self._run(_notify_user_checked(999, "hello"))

        assert result is False

    def test_returns_true_and_sends_when_enabled(self):
        user = _make_user(enabled=True)
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = user

        with (
            patch(
                "src.tasks.notification_tasks.UserRepository",
                return_value=mock_repo,
            ),
            patch("src.tasks.notification_tasks.async_session_factory") as mock_factory,
            patch(
                "src.tasks.notification_tasks._notify_user_async", new_callable=AsyncMock
            ) as mock_send,
        ):
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tasks.notification_tasks import _notify_user_checked

            result = self._run(_notify_user_checked(user.id, "hello"))

        assert result is True
        mock_send.assert_called_once_with(user.telegram_id, "hello", "HTML", None)

    def test_returns_false_on_forbidden(self):
        from aiogram.exceptions import TelegramForbiddenError

        user = _make_user(enabled=True)
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = user

        async def _raise(*a, **kw):
            raise TelegramForbiddenError(method=MagicMock(), message="Forbidden: bot was blocked")

        with (
            patch(
                "src.tasks.notification_tasks.UserRepository",
                return_value=mock_repo,
            ),
            patch("src.tasks.notification_tasks.async_session_factory") as mock_factory,
            patch(
                "src.tasks.notification_tasks._notify_user_async",
                side_effect=_raise,
            ),
        ):
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.tasks.notification_tasks import _notify_user_checked

            result = self._run(_notify_user_checked(user.id, "hello"))

        assert result is False


# ─── mailing:notify_user ──────────────────────────────────────────────────────


class TestMailingNotifyUser:
    """mailing:notify_user must respect notifications_enabled."""

    @pytest.fixture(autouse=True)
    def _patch_factory(self):
        with patch("src.tasks._bot_factory.Bot"):
            import src.tasks._bot_factory as fac
            fac._bot = MagicMock()
            yield
            fac._bot = None

    def test_skips_when_notifications_disabled(self):
        user = _make_user(enabled=False)
        mock_repo = AsyncMock()
        mock_repo.get_by_telegram_id.return_value = user

        with (
            patch(
                "src.tasks.notification_tasks.UserRepository",
                return_value=mock_repo,
            ),
            patch("src.tasks.notification_tasks.async_session_factory") as mock_factory,
            patch("src.tasks.notification_tasks.redis_client") as mock_redis,
            patch(
                "src.tasks.notification_tasks._notify_user_async", new_callable=AsyncMock
            ) as mock_send,
        ):
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_redis.exists = AsyncMock(return_value=0)
            mock_redis.setex = AsyncMock()

            from src.tasks.notification_tasks import notify_user

            result = notify_user(user.telegram_id, "hello")

        assert result is False
        mock_send.assert_not_called()

    def test_sends_when_user_not_found_in_db(self):
        """If user not found, still send (system/auth messages)."""
        mock_repo = AsyncMock()
        mock_repo.get_by_telegram_id.return_value = None

        with (
            patch(
                "src.tasks.notification_tasks.UserRepository",
                return_value=mock_repo,
            ),
            patch("src.tasks.notification_tasks.async_session_factory") as mock_factory,
            patch("src.tasks.notification_tasks.redis_client") as mock_redis,
            patch(
                "src.tasks.notification_tasks._notify_user_async", new_callable=AsyncMock
            ) as mock_send,
        ):
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_redis.exists = AsyncMock(return_value=0)
            mock_redis.setex = AsyncMock()

            from src.tasks.notification_tasks import notify_user

            result = notify_user(12345, "system message")

        assert result is True
        mock_send.assert_called_once()


# ─── notify_payment_success ───────────────────────────────────────────────────


class TestNotifyPaymentSuccess:
    """billing:notify_payment_success respects notifications_enabled."""

    @pytest.fixture(autouse=True)
    def _patch_factory(self):
        with patch("src.tasks._bot_factory.Bot"):
            import src.tasks._bot_factory as fac
            fac._bot = MagicMock()
            yield
            fac._bot = None

    def test_skips_when_notifications_disabled(self):
        from decimal import Decimal

        user = _make_user(enabled=False)
        user.balance_rub = Decimal("100.00")

        with (
            patch("src.tasks.billing_tasks.async_session_factory") as mock_sf,
            patch(
                "src.tasks.notification_tasks._notify_user_async", new_callable=AsyncMock
            ) as mock_send,
            patch(
                "src.tasks.notification_tasks.UserRepository",
            ) as mock_repo_cls,
        ):
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = user
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_sf.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_by_id.return_value = user
            mock_repo_cls.return_value = mock_repo_instance

            # Also patch notification_tasks session factory
            with patch(
                "src.tasks.notification_tasks.async_session_factory"
            ) as mock_notif_sf:
                notif_session = AsyncMock()
                mock_notif_sf.return_value.__aenter__ = AsyncMock(return_value=notif_session)
                mock_notif_sf.return_value.__aexit__ = AsyncMock(return_value=False)

                from src.tasks.billing_tasks import notify_payment_success

                result = notify_payment_success(user.id, 500.0, "pay_abc123")

        assert result is False
        mock_send.assert_not_called()
