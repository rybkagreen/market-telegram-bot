"""
Regression tests: BillingService idempotency via Transaction.idempotency_key (S-48 A.3).

Covers:
 - source-level invariants (key format, no session.begin in public methods)
 - behavioural guards via in-memory mocks (EXISTS short-circuit)
"""

import inspect


# =============================================================================
# Source-inspection: caller-controlled transaction contract (A.1)
# =============================================================================


class TestCallerControlledTransactionContract:
    """Methods that accept `session: AsyncSession` must NOT open their own transaction."""

    def _assert_no_session_begin(self, method) -> None:
        source = inspect.getsource(method)
        assert "async with session.begin()" not in source, (
            f"{method.__qualname__} must not call `session.begin()` — "
            "caller owns the transaction (see CLAUDE.md § Service Transaction Contract)."
        )

    def test_release_escrow_has_no_session_begin(self):
        from src.core.services.billing_service import BillingService
        self._assert_no_session_begin(BillingService.release_escrow)

    def test_refund_escrow_has_no_session_begin(self):
        from src.core.services.billing_service import BillingService
        self._assert_no_session_begin(BillingService.refund_escrow)

    def test_freeze_escrow_has_no_session_begin(self):
        from src.core.services.billing_service import BillingService
        self._assert_no_session_begin(BillingService.freeze_escrow)

    def test_process_topup_webhook_has_no_session_begin(self):
        from src.core.services.billing_service import BillingService
        self._assert_no_session_begin(BillingService.process_topup_webhook)


# =============================================================================
# Source-inspection: idempotency_key format (A.3)
# =============================================================================


class TestIdempotencyKeyFormat:
    """Each financial event carries a stable business-level idempotency key."""

    def test_release_escrow_uses_owner_and_platform_keys(self):
        from src.core.services.billing_service import BillingService
        source = inspect.getsource(BillingService.release_escrow)
        assert "escrow_release:placement=" in source
        assert ":owner" in source
        assert ":platform" in source

    def test_freeze_escrow_uses_freeze_key(self):
        from src.core.services.billing_service import BillingService
        source = inspect.getsource(BillingService.freeze_escrow)
        assert "escrow_freeze:placement=" in source

    def test_refund_escrow_uses_scenario_specific_keys(self):
        from src.core.services.billing_service import BillingService
        source = inspect.getsource(BillingService.refund_escrow)
        assert "refund:placement=" in source
        assert ":scenario=" in source
        assert ":advertiser" in source
        assert ":owner" in source


# =============================================================================
# Source-inspection: early-exit on idempotency hit
# =============================================================================


class TestIdempotencyShortCircuit:
    def test_release_escrow_early_exits_on_exists(self):
        from src.core.services.billing_service import BillingService
        source = inspect.getsource(BillingService.release_escrow)
        assert "exists" in source.lower()
        assert "idempotency hit" in source.lower()

    def test_refund_escrow_early_exits_on_exists(self):
        from src.core.services.billing_service import BillingService
        source = inspect.getsource(BillingService.refund_escrow)
        assert "exists" in source.lower()
        assert "idempotency hit" in source.lower()

    def test_freeze_escrow_early_exits_on_exists(self):
        from src.core.services.billing_service import BillingService
        source = inspect.getsource(BillingService.freeze_escrow)
        assert "exists" in source.lower()
        assert "idempotency hit" in source.lower()


# =============================================================================
# Source-inspection: IntegrityError handling around flush
# =============================================================================


class TestIntegrityErrorHandling:
    """On race past EXISTS check, UNIQUE index catches the loser at flush."""

    def test_release_escrow_catches_integrity_error(self):
        from src.core.services.billing_service import BillingService
        source = inspect.getsource(BillingService.release_escrow)
        assert "IntegrityError" in source
        assert "idempotency race" in source

    def test_refund_escrow_catches_integrity_error(self):
        from src.core.services.billing_service import BillingService
        source = inspect.getsource(BillingService.refund_escrow)
        assert "IntegrityError" in source

    def test_freeze_escrow_catches_integrity_error(self):
        from src.core.services.billing_service import BillingService
        source = inspect.getsource(BillingService.freeze_escrow)
        assert "IntegrityError" in source


# =============================================================================
# Source-inspection: placement_request_id set on every financial Transaction
# =============================================================================


class TestPlacementLinkage:
    def test_release_escrow_links_owner_txn_to_placement(self):
        from src.core.services.billing_service import BillingService
        source = inspect.getsource(BillingService.release_escrow)
        assert "placement_request_id=placement_id" in source

    def test_refund_escrow_links_advertiser_txn_to_placement(self):
        from src.core.services.billing_service import BillingService
        source = inspect.getsource(BillingService.refund_escrow)
        assert "placement_request_id=placement_id" in source

    def test_freeze_escrow_links_txn_to_placement(self):
        from src.core.services.billing_service import BillingService
        source = inspect.getsource(BillingService.freeze_escrow)
        assert "placement_request_id=placement_id" in source


# =============================================================================
# Behavioural: EXISTS short-circuits before any writes
# =============================================================================


def _make_session_with_existing_key():
    """Build an AsyncSession mock where the EXISTS check returns True."""
    from unittest.mock import AsyncMock, MagicMock

    session = AsyncMock()
    session.scalar = AsyncMock(return_value=True)  # EXISTS hits
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


def test_release_escrow_noop_when_key_exists():
    """Second call is a no-op: no flush, no add, no user lookup."""
    import asyncio
    from decimal import Decimal

    from src.core.services.billing_service import BillingService

    async def _run():
        session = _make_session_with_existing_key()
        await BillingService().release_escrow(
            session,
            placement_id=42,
            final_price=Decimal("500"),
            advertiser_id=10,
            owner_id=20,
        )
        session.flush.assert_not_called()
        session.add.assert_not_called()

    asyncio.run(_run())


def test_refund_escrow_noop_when_key_exists():
    import asyncio
    from decimal import Decimal

    from src.core.services.billing_service import BillingService

    async def _run():
        session = _make_session_with_existing_key()
        await BillingService().refund_escrow(
            session,
            placement_id=42,
            final_price=Decimal("500"),
            advertiser_id=10,
            owner_id=20,
            scenario="after_escrow_before_confirmation",
        )
        session.flush.assert_not_called()
        session.add.assert_not_called()

    asyncio.run(_run())


def test_freeze_escrow_noop_when_key_exists():
    import asyncio
    from decimal import Decimal

    from src.core.services.billing_service import BillingService

    async def _run():
        session = _make_session_with_existing_key()
        # Сумма ≥ MIN_CAMPAIGN_BUDGET, чтобы дойти до EXISTS-проверки.
        await BillingService().freeze_escrow(
            session,
            user_id=10,
            placement_id=42,
            amount=Decimal("2500"),
        )
        session.flush.assert_not_called()
        session.add.assert_not_called()

    asyncio.run(_run())


# =============================================================================
# publication_service.delete_published_post — status guard (A.4)
# =============================================================================


class TestDeletePublishedPostStatusGuard:
    def test_guards_on_completed_status(self):
        from src.core.services.publication_service import PublicationService

        source = inspect.getsource(PublicationService.delete_published_post)
        assert "PlacementStatus.completed" in source
        assert "skipping deletion" in source.lower() or "already completed" in source.lower()

    def test_guards_on_unexpected_status(self):
        from src.core.services.publication_service import PublicationService

        source = inspect.getsource(PublicationService.delete_published_post)
        assert "PlacementStatus.published" in source
        assert "unexpected status" in source.lower() or "aborted" in source.lower()


# =============================================================================
# tasks/_bot_factory — ephemeral_bot
# =============================================================================


class TestEphemeralBot:
    def test_factory_exports_ephemeral_bot(self):
        from src.tasks import _bot_factory

        assert hasattr(_bot_factory, "ephemeral_bot")

    def test_delete_task_uses_ephemeral_bot(self):
        import src.tasks.placement_tasks as pt

        source = inspect.getsource(pt._delete_published_post_async)
        assert "ephemeral_bot" in source
        assert "get_bot" not in source

    def test_dedup_ttl_has_delete_published_post(self):
        from src.tasks.placement_tasks import DEDUP_TTL

        assert "delete_published_post" in DEDUP_TTL
        assert DEDUP_TTL["delete_published_post"] <= 300  # короткий TTL, не 3600


# =============================================================================
# check_escrow_stuck — group C branch
# =============================================================================


class TestCheckEscrowStuckGroupC:
    def test_group_c_branch_present(self):
        from src.tasks.placement_tasks import _check_escrow_stuck_async

        source = inspect.getsource(_check_escrow_stuck_async)
        assert 'group_c_dispatched' in source
        assert 'STUCK PUBLISHED' in source
        assert 'PlacementStatus.published' in source
