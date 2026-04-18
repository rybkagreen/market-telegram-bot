"""
Regression tests for S-38 P0 fixes: escrow recovery in placement_tasks.

Tests:
- check_escrow_sla routes through BillingService (not direct mutation)
- check_escrow_stuck dispatches actions and commits
- delete_published_post retries on error (autoretry present)
- publish_placement failure refunds escrow
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# =============================================================================
# check_escrow_sla — source inspection (sync)
# =============================================================================


class TestCheckEscrowSlaSrc:
    def test_calls_billing_service_refund_escrow(self):
        import inspect
        from src.tasks.placement_tasks import _check_escrow_sla_async

        source = inspect.getsource(_check_escrow_sla_async)
        assert "billing_svc.refund_escrow" in source
        assert "balance_rub +=" not in source, "must NOT directly mutate balance_rub"

    def test_no_direct_transaction_creation(self):
        import inspect
        from src.tasks.placement_tasks import _check_escrow_sla_async

        source = inspect.getsource(_check_escrow_sla_async)
        assert "Transaction(" not in source, "must not create Transaction directly"

    def test_per_item_commit(self):
        import inspect
        from src.tasks.placement_tasks import _check_escrow_sla_async

        source = inspect.getsource(_check_escrow_sla_async)
        assert "await session.commit()" in source

    def test_uses_after_escrow_before_confirmation_scenario(self):
        import inspect
        from src.tasks.placement_tasks import _check_escrow_sla_async

        source = inspect.getsource(_check_escrow_sla_async)
        assert "after_escrow_before_confirmation" in source

    def test_has_session_rollback_on_error(self):
        import inspect
        from src.tasks.placement_tasks import _check_escrow_sla_async

        source = inspect.getsource(_check_escrow_sla_async)
        assert "await session.rollback()" in source


# =============================================================================
# check_escrow_stuck — source inspection (sync)
# =============================================================================


class TestCheckEscrowStuckSrc:
    def test_group_a_dispatches_delete(self):
        import inspect
        from src.tasks.placement_tasks import _check_escrow_stuck_async

        source = inspect.getsource(_check_escrow_stuck_async)
        assert "delete_published_post.apply_async" in source

    def test_group_b_calls_refund(self):
        import inspect
        from src.tasks.placement_tasks import _check_escrow_stuck_async

        source = inspect.getsource(_check_escrow_stuck_async)
        assert "billing_svc.refund_escrow" in source

    def test_commits_per_item(self):
        import inspect
        from src.tasks.placement_tasks import _check_escrow_stuck_async

        source = inspect.getsource(_check_escrow_stuck_async)
        assert "await session.commit()" in source

    def test_sends_admin_alert(self):
        import inspect
        from src.tasks.placement_tasks import _check_escrow_stuck_async

        source = inspect.getsource(_check_escrow_stuck_async)
        assert "send_message" in source
        assert "admin_ids" in source

    def test_meta_json_records_stuck_detected(self):
        import inspect
        from src.tasks.placement_tasks import _check_escrow_stuck_async

        source = inspect.getsource(_check_escrow_stuck_async)
        assert "escrow_stuck_detected" in source

    def test_has_session_rollback_on_error(self):
        import inspect
        from src.tasks.placement_tasks import _check_escrow_stuck_async

        source = inspect.getsource(_check_escrow_stuck_async)
        assert "await session.rollback()" in source


# =============================================================================
# delete_published_post — source inspection + attribute checks (sync)
# =============================================================================


class TestDeletePublishedPostSrc:
    def test_has_autoretry(self):
        from src.tasks.placement_tasks import delete_published_post

        assert hasattr(delete_published_post, "autoretry_for")
        assert Exception in delete_published_post.autoretry_for

    def test_max_retries_is_5(self):
        from src.tasks.placement_tasks import delete_published_post

        assert delete_published_post.max_retries == 5

    def test_no_bare_except_in_async(self):
        import inspect
        from src.tasks.placement_tasks import _delete_published_post_async

        source = inspect.getsource(_delete_published_post_async)
        assert "except Exception" not in source, "must not catch exceptions — bubble for autoretry"

    def test_no_error_return_dict(self):
        import inspect
        from src.tasks.placement_tasks import _delete_published_post_async

        source = inspect.getsource(_delete_published_post_async)
        assert '"error"' not in source, "must not return error dict; raise instead"


# =============================================================================
# publish_placement failure path — source inspection (sync)
# =============================================================================


class TestPublishPlacementFailureSrc:
    def test_calls_refund_escrow_on_failure(self):
        import inspect
        from src.tasks.placement_tasks import _publish_placement_async

        source = inspect.getsource(_publish_placement_async)
        assert "billing_svc.refund_escrow" in source

    def test_no_hardcoded_pct_promise(self):
        import inspect
        from src.tasks.placement_tasks import _publish_placement_async

        source = inspect.getsource(_publish_placement_async)
        assert "Возврат {REFUND_AFTER_ESCROW_PCT}%" not in source

    def test_uses_after_escrow_before_confirmation(self):
        import inspect
        from src.tasks.placement_tasks import _publish_placement_async

        source = inspect.getsource(_publish_placement_async)
        assert "after_escrow_before_confirmation" in source


# =============================================================================
# Structural: no direct balance mutations + autoretry present
# =============================================================================


class TestNoDirectMutations:
    def test_no_direct_balance_mutation(self):
        import inspect
        import src.tasks.placement_tasks as module

        source = inspect.getsource(module)
        bad_lines = [
            line for line in source.splitlines()
            if "balance_rub +=" in line and not line.strip().startswith("#")
        ]
        assert len(bad_lines) == 0, (
            "Direct balance_rub += found:\n" + "\n".join(bad_lines)
        )

    def test_autoretry_present_in_module(self):
        import inspect
        import src.tasks.placement_tasks as module

        source = inspect.getsource(module)
        assert "autoretry_for" in source


# =============================================================================
# Async integration tests — module level (pytest-asyncio works here)
# =============================================================================


def test_delete_published_post_async_raises_on_commit_error():
    """_delete_published_post_async поднимает исключение при ошибке — Celery сделает retry."""
    from src.tasks.placement_tasks import _delete_published_post_async

    async def _run():
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session.commit = AsyncMock(side_effect=RuntimeError("DB down"))

        mock_pub = AsyncMock()

        with (
            patch("src.tasks.placement_tasks.async_session_factory", return_value=mock_session),
            patch("src.tasks._bot_factory.get_bot", return_value=AsyncMock()),
            patch(
                "src.core.services.publication_service.PublicationService.delete_published_post",
                new=mock_pub,
            ),
        ):
            await _delete_published_post_async(99)

    with pytest.raises(RuntimeError, match="DB down"):
        asyncio.run(_run())


def test_check_escrow_stuck_group_a_dispatches_delete_not_refund():
    """Group A (message_id set) → delete_published_post dispatch, no direct refund."""
    from src.tasks.placement_tasks import _check_escrow_stuck_async

    async def _run():
        stuck = MagicMock()
        stuck.id = 42
        stuck.message_id = 12345
        stuck.advertiser_id = 10
        stuck.owner_id = 20
        stuck.final_price = Decimal("500")
        stuck.proposed_price = Decimal("500")
        stuck.channel = MagicMock()
        stuck.channel.username = "testch"
        stuck.meta_json = {}
        stuck.scheduled_delete_at = MagicMock()

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [stuck]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_refund = AsyncMock()
        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock()

        with (
            patch("src.tasks.placement_tasks.async_session_factory", return_value=mock_session),
            patch("src.tasks.placement_tasks.delete_published_post") as mock_task,
            patch("src.core.services.billing_service.BillingService.refund_escrow", new=mock_refund),
            patch("src.tasks._bot_factory.get_bot", return_value=mock_bot),
            patch("src.tasks.placement_tasks.settings") as mock_settings,
        ):
            mock_settings.admin_ids = [999]
            mock_task.apply_async = MagicMock()
            stats = await _check_escrow_stuck_async()

        mock_task.apply_async.assert_called_once_with(args=[42])
        mock_refund.assert_not_called()
        assert stats["group_a_dispatched"] == 1

    asyncio.run(_run())


def test_publish_placement_failure_calls_refund_escrow():
    """При ошибке публикации refund_escrow вызывается с scenario=after_escrow_before_confirmation."""
    from src.tasks.placement_tasks import _publish_placement_async
    from src.db.models.placement_request import PlacementStatus as PS

    async def _run():
        placement = MagicMock()
        placement.id = 77
        placement.status = PS.escrow
        placement.advertiser_id = 5
        placement.owner_id = 6
        placement.message_id = None
        placement.final_price = Decimal("800")
        placement.proposed_price = Decimal("800")
        placement.channel_id = 1

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(return_value=placement)
        mock_repo.update_status = AsyncMock()

        mock_session = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_refund_session = AsyncMock()
        mock_refund_session.__aenter__ = AsyncMock(return_value=mock_refund_session)
        mock_refund_session.__aexit__ = AsyncMock(return_value=None)

        mock_refund = AsyncMock()

        with (
            patch(
                "src.tasks.placement_tasks.async_session_factory",
                side_effect=[mock_session, mock_refund_session],
            ),
            patch("src.tasks.placement_tasks.PlacementRequestRepository", return_value=mock_repo),
            patch("src.tasks._bot_factory.get_bot", return_value=AsyncMock()),
            patch("src.tasks.placement_tasks._check_dedup", return_value=False),
            patch("src.core.services.publication_service.PublicationService") as mock_pub_cls,
            patch("src.core.services.billing_service.BillingService.refund_escrow", new=mock_refund),
            patch("src.tasks.placement_tasks._notify_user", new=AsyncMock()),
        ):
            mock_pub_cls.return_value.publish_placement = AsyncMock(
                side_effect=RuntimeError("Telegram error")
            )
            await _publish_placement_async(77)

        mock_refund.assert_called_once()
        call_kwargs = mock_refund.call_args
        scenario = call_kwargs.kwargs.get("scenario") or call_kwargs.args[5]
        assert scenario == "after_escrow_before_confirmation"

    asyncio.run(_run())


def test_publish_placement_success_does_not_refund():
    """Happy path не вызывает refund_escrow."""
    from src.tasks.placement_tasks import _publish_placement_async
    from src.db.models.placement_request import PlacementStatus as PS

    async def _run():
        placement = MagicMock()
        placement.id = 78
        placement.status = PS.escrow
        placement.advertiser_id = 5
        placement.owner_id = 6
        placement.message_id = None
        placement.final_price = Decimal("800")
        placement.proposed_price = Decimal("800")
        placement.channel_id = 1

        updated = MagicMock()
        updated.channel_id = 1

        mock_repo = AsyncMock()
        mock_repo.get_by_id = AsyncMock(side_effect=[placement, updated])

        mock_channel = MagicMock()
        mock_channel.username = "testch"
        mock_channel.owner_id = 6

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_channel)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_refund = AsyncMock()
        mock_rep = AsyncMock()
        mock_rep.on_publication = AsyncMock()

        with (
            patch("src.tasks.placement_tasks.async_session_factory", return_value=mock_session),
            patch("src.tasks.placement_tasks.PlacementRequestRepository", return_value=mock_repo),
            patch("src.tasks._bot_factory.get_bot", return_value=AsyncMock()),
            patch("src.tasks.placement_tasks._check_dedup", return_value=False),
            patch("src.core.services.publication_service.PublicationService") as mock_pub_cls,
            patch("src.tasks.placement_tasks.ReputationService", return_value=mock_rep),
            patch("src.core.services.billing_service.BillingService.refund_escrow", new=mock_refund),
            patch("src.tasks.placement_tasks._notify_user", new=AsyncMock()),
        ):
            mock_pub_cls.return_value.publish_placement = AsyncMock()
            await _publish_placement_async(78)

        mock_refund.assert_not_called()

    asyncio.run(_run())
