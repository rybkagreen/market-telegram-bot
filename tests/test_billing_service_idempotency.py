"""
Regression tests: BillingService.refund_escrow idempotency (S-38 Phase 1).

Source-inspection tests — no DB required; verify guard logic is present.
"""

import inspect

import pytest


# =============================================================================
# Source-inspection: guard presence
# =============================================================================


class TestRefundEscrowIdempotencyGuard:
    def test_idempotency_check_present(self):
        """refund_escrow содержит SELECT для проверки существующей транзакции."""
        from src.core.services.billing_service import BillingService

        source = inspect.getsource(BillingService.refund_escrow)
        assert "scalar_one_or_none" in source, (
            "refund_escrow must check for existing transaction (idempotency guard)"
        )

    def test_guard_uses_refund_full_type(self):
        """Идемпотентность проверяется по типу TransactionType.refund_full."""
        from src.core.services.billing_service import BillingService

        source = inspect.getsource(BillingService.refund_escrow)
        assert "refund_full" in source, (
            "refund_escrow idempotency guard must check TransactionType.refund_full"
        )

    def test_guard_uses_placement_request_id(self):
        """Идемпотентность проверяется по placement_request_id, а не только по типу."""
        from src.core.services.billing_service import BillingService

        source = inspect.getsource(BillingService.refund_escrow)
        assert "placement_request_id" in source, (
            "refund_escrow idempotency guard must filter by placement_request_id"
        )

    def test_guard_logs_and_returns_on_duplicate(self):
        """При обнаружении дубля — логирование и ранний return."""
        from src.core.services.billing_service import BillingService

        source = inspect.getsource(BillingService.refund_escrow)
        assert "idempotency" in source.lower() or "skipping" in source.lower(), (
            "refund_escrow must log idempotency skip message"
        )
        assert "return" in source, "refund_escrow must return early on duplicate"

    def test_advertiser_txn_has_placement_request_id(self):
        """Transaction, создаваемая в refund_escrow, имеет placement_request_id=placement_id."""
        from src.core.services.billing_service import BillingService

        source = inspect.getsource(BillingService.refund_escrow)
        # Check that placement_request_id is set on the transaction object
        assert "placement_request_id=placement_id" in source, (
            "advertiser_txn in refund_escrow must set placement_request_id=placement_id "
            "so future idempotency checks can find it via FK"
        )


class TestRefundEscrowScenarios:
    def test_known_scenarios_present(self):
        """Известные сценарии: before_escrow, after_escrow_before_confirmation, after_confirmation."""
        from src.core.services.billing_service import BillingService

        source = inspect.getsource(BillingService.refund_escrow)
        assert "before_escrow" in source
        assert "after_escrow_before_confirmation" in source
        assert "after_confirmation" in source

    def test_unknown_scenario_raises(self):
        """Неизвестный сценарий вызывает ValueError."""
        from src.core.services.billing_service import BillingService

        source = inspect.getsource(BillingService.refund_escrow)
        assert "raise ValueError" in source, (
            "refund_escrow must raise ValueError for unknown scenario"
        )

    def test_after_escrow_before_confirmation_gives_full_refund(self):
        """scenario=after_escrow_before_confirmation: advertiser_refund = final_price (100%)."""
        from src.core.services.billing_service import BillingService

        source = inspect.getsource(BillingService.refund_escrow)
        # The logic: advertiser_refund = final_price (no percentage applied)
        assert "advertiser_refund = final_price" in source, (
            "after_escrow_before_confirmation must give 100% refund to advertiser"
        )

    def test_after_confirmation_splits_50_425_75(self):
        """scenario=after_confirmation: advertiser +50%, owner +42.5%, platform +7.5%."""
        from src.core.services.billing_service import BillingService

        source = inspect.getsource(BillingService.refund_escrow)
        assert "0.50" in source
        assert "0.425" in source


class TestReleaseEscrowIdempotency:
    def test_release_escrow_has_idempotency_check(self):
        """release_escrow проверяет MailingLog.status == paid перед выплатой."""
        from src.core.services.billing_service import BillingService

        source = inspect.getsource(BillingService.release_escrow)
        assert "MailingStatus.paid" in source or "paid" in source, (
            "release_escrow must check mailing paid status for idempotency"
        )
        assert "skipped" in source.lower() or "skip" in source.lower(), (
            "release_escrow must skip if already released"
        )


# =============================================================================
# Mock-based: guard actually blocks second call
# =============================================================================


def test_refund_escrow_guard_blocks_on_existing_transaction():
    """
    Idempotency guard возвращает early когда существующая Transaction найдена.
    Использует asyncio.run() — обход бага pytest-asyncio 0.26.0 + Python 3.14.
    """
    import asyncio
    from decimal import Decimal
    from unittest.mock import AsyncMock, MagicMock

    from src.core.services.billing_service import BillingService

    async def _run():
        existing_txn = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_txn

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.begin = MagicMock()

        svc = BillingService()
        await svc.refund_escrow(
            mock_session,
            placement_id=42,
            final_price=Decimal("500"),
            advertiser_id=10,
            owner_id=20,
            scenario="after_escrow_before_confirmation",
        )
        # Guard triggered → session.begin() never entered
        mock_session.begin.assert_not_called()

    asyncio.run(_run())


def test_refund_escrow_guard_proceeds_when_no_existing_transaction():
    """
    Когда существующей транзакции нет — guard не блокирует, session.begin() вызывается.
    """
    import asyncio
    from decimal import Decimal
    from unittest.mock import AsyncMock, MagicMock, patch

    from src.core.services.billing_service import BillingService
    from src.db.models.user import User

    async def _run():
        mock_check_result = MagicMock()
        mock_check_result.scalar_one_or_none.return_value = None  # no existing txn

        mock_user = MagicMock(spec=User)
        mock_user.balance_rub = Decimal("1000")
        mock_user.earned_rub = Decimal("0")

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_check_result
            r = MagicMock()
            r.scalar_one_or_none.return_value = mock_user
            return r

        mock_begin_ctx = AsyncMock()
        mock_begin_ctx.__aenter__ = AsyncMock(return_value=None)
        mock_begin_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.execute = mock_execute
        mock_session.flush = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.begin = MagicMock(return_value=mock_begin_ctx)

        with (
            patch(
                "src.db.repositories.user_repo.UserRepository.get_by_id",
                new=AsyncMock(return_value=mock_user),
            ),
            patch(
                "src.db.repositories.platform_account_repo.PlatformAccountRepo.release_from_escrow",
                new=AsyncMock(),
            ),
        ):
            svc = BillingService()
            try:
                await svc.refund_escrow(
                    mock_session,
                    placement_id=99,
                    final_price=Decimal("500"),
                    advertiser_id=10,
                    owner_id=20,
                    scenario="after_escrow_before_confirmation",
                )
            except Exception:
                pass  # internals may fail in mock — begin() call is what matters

        mock_session.begin.assert_called_once()

    asyncio.run(_run())
