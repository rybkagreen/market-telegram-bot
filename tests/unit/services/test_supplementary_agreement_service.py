"""Unit tests for SupplementaryAgreementService (PROMPT 28 Step 10.1).

Coverage:
* Idempotency — second `generate_for_placement` returns existing pair.
* Framework prerequisites — missing advertiser_framework / owner_service raise.
* Missing legal_profile — raises.
* Missing final_price — raises.
* Race-safe — IntegrityError on flush triggers re-SELECT and returns existing.
* ContractEvent — `supplementary_generated` row recorded on first generation.

S-48 Pattern 1 boundary: service uses caller's session; tests assert no commit
is invoked by the service path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from src.core.services.supplementary_agreement_service import (
    SupplementaryAgreementService,
)
from src.db.models.contract import Contract
from src.db.models.placement_request import PublicationFormat

pytestmark = pytest.mark.asyncio


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────


def _placement(*, placement_id: int = 7, advertiser_id: int = 100, owner_id: int = 200):
    return SimpleNamespace(
        id=placement_id,
        advertiser_id=advertiser_id,
        owner_id=owner_id,
        final_price=Decimal("1000.00"),
        final_schedule=datetime(2026, 5, 14, 12, 0, tzinfo=UTC),
        publication_format=PublicationFormat.post_24h,
        ad_text="stub text",
        channel=SimpleNamespace(id=1, title="Stub", username="stub"),
    )


def _existing_contract(*, role: str, contract_id: int = 1, placement_id: int = 7) -> Contract:
    c = Contract()
    c.id = contract_id
    c.user_id = 100 if role == "advertiser" else 200
    c.contract_type = "supplementary_agreement"
    c.contract_status = "draft"
    c.placement_id = placement_id
    c.role = role
    return c


def _framework(*, role: str, contract_id: int = 50) -> Contract:
    c = Contract()
    c.id = contract_id
    c.contract_type = "advertiser_framework" if role == "advertiser" else "owner_service"
    c.role = role
    c.contract_status = "signed"
    c.signed_at = datetime(2026, 5, 1, tzinfo=UTC)
    return c


def _legal_profile(*, legal_status: str = "individual") -> SimpleNamespace:
    return SimpleNamespace(
        user_id=100,
        legal_status=legal_status,
        inn="1234567890",
        kpp=None,
        ogrn=None,
        ogrnip=None,
        legal_name="Stub Party",
        address="Stub address",
        tax_regime=None,
        bank_name=None,
        bank_bik=None,
        is_verified=True,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _make_integrity_error() -> IntegrityError:
    """Build a properly-constructed IntegrityError instance for race tests."""
    return IntegrityError("INSERT into contracts", {}, Exception("uq violated"))


def _build_service_with_mocks(
    *,
    existing_adv: Contract | None = None,
    existing_own: Contract | None = None,
    adv_framework: Contract | None = None,
    own_framework: Contract | None = None,
    profile=None,
    flush_side_effects: list | None = None,
    record_event_mock: AsyncMock | None = None,
) -> tuple[SupplementaryAgreementService, MagicMock]:
    """Builds a service with all repos mocked and returns (service, session_mock).

    Default-supplied stubs cover the happy path; pass overrides for negative
    cases. `flush_side_effects` simulates `session.flush()` raising or returning
    in sequence (used for race tests).
    """
    session = MagicMock()
    session.add = MagicMock()
    session.rollback = AsyncMock()
    if flush_side_effects is not None:
        session.flush = AsyncMock(side_effect=flush_side_effects)
    else:
        session.flush = AsyncMock()

    service = SupplementaryAgreementService(session)

    # Stub repo methods
    service._contract_repo = MagicMock()
    service._contract_repo.get_by_placement_and_role = AsyncMock(
        side_effect=[existing_adv, existing_own]
    )
    service._contract_repo.get_framework_contract = AsyncMock(
        side_effect=[adv_framework, own_framework]
    )
    service._contract_repo.record_event = record_event_mock or AsyncMock()

    service._legal_repo = MagicMock()
    service._legal_repo.get_by_user_id = AsyncMock(return_value=profile or _legal_profile())

    service._contract_service = MagicMock()
    service._contract_service._get_platform_ctx = AsyncMock(
        return_value={
            "platform_legal_name": "Platform",
            "platform_inn": "9999999999",
            "platform_kpp": "999901001",
            "platform_ogrn": "1234567890123",
            "platform_address": "stub",
            "platform_bank_name": "stub",
            "platform_bank_account": "40702810999999999999",
            "platform_bank_bik": "044525000",
            "platform_bank_corr_account": "30101810000000000000",
        }
    )
    return service, session


# ────────────────────────────────────────────────────────────────────────
# Idempotency
# ────────────────────────────────────────────────────────────────────────


async def test_generate_returns_existing_pair_when_both_already_present() -> None:
    """If both sides already exist, no new INSERTs happen — returns existing pair as-is."""
    placement = _placement()
    existing_adv = _existing_contract(role="advertiser", contract_id=11)
    existing_own = _existing_contract(role="owner", contract_id=12)

    service, session = _build_service_with_mocks(
        existing_adv=existing_adv,
        existing_own=existing_own,
    )

    adv, own = await service.generate_for_placement(placement)

    assert adv is existing_adv
    assert own is existing_own
    # No new INSERTs (session.add never called)
    session.add.assert_not_called()
    # No event records (existing rows don't re-emit generated events)
    assert service._contract_repo.record_event.await_count == 0


# ────────────────────────────────────────────────────────────────────────
# Validation — missing prerequisites
# ────────────────────────────────────────────────────────────────────────


async def test_generate_raises_when_placement_has_no_final_price() -> None:
    placement = _placement()
    placement.final_price = None
    service, _ = _build_service_with_mocks()

    with pytest.raises(ValueError, match="no final_price"):
        await service.generate_for_placement(placement)


async def test_generate_raises_when_advertiser_lacks_framework() -> None:
    placement = _placement()
    service, _ = _build_service_with_mocks(
        existing_adv=None,
        existing_own=None,
        adv_framework=None,  # missing!
        own_framework=_framework(role="owner"),
    )

    with pytest.raises(ValueError, match="advertiser .* no signed framework"):
        await service.generate_for_placement(placement)


async def test_generate_raises_when_owner_lacks_framework() -> None:
    placement = _placement()
    service, _ = _build_service_with_mocks(
        existing_adv=None,
        existing_own=None,
        adv_framework=_framework(role="advertiser"),
        own_framework=None,  # missing!
    )

    with pytest.raises(ValueError, match="owner .* no signed framework"):
        await service.generate_for_placement(placement)


async def test_generate_raises_when_user_lacks_legal_profile() -> None:
    """No legal_profile → cannot snapshot реквизиты → fail-fast on _generate_side."""
    placement = _placement()
    service, _ = _build_service_with_mocks(
        existing_adv=None,
        existing_own=None,
        adv_framework=_framework(role="advertiser"),
        own_framework=_framework(role="owner"),
    )
    # Override legal_repo to return None on first call
    service._legal_repo.get_by_user_id = AsyncMock(return_value=None)

    with pytest.raises(ValueError, match="no legal_profile"):
        await service.generate_for_placement(placement)


# ────────────────────────────────────────────────────────────────────────
# Race-safe — IntegrityError during flush
# ────────────────────────────────────────────────────────────────────────


async def test_generate_race_recovers_via_re_select_when_unique_index_fires() -> None:
    """Concurrent generation triggers UNIQUE constraint → flush raises
    IntegrityError → service rolls back and re-fetches the row that won the race."""
    placement = _placement()
    race_winner = _existing_contract(role="advertiser", contract_id=999)

    service, session = _build_service_with_mocks(
        existing_adv=None,  # didn't exist at EXISTS-check time
        existing_own=None,
        adv_framework=_framework(role="advertiser"),
        own_framework=_framework(role="owner"),
        # advertiser-side flush raises (race), owner-side flush succeeds (multiple calls)
        flush_side_effects=[_make_integrity_error(), None, None, None],
    )
    # Initial EXISTS check returns None for both sides; after race, re-SELECT
    # for advertiser-side returns race_winner; owner-side returns existing row.
    service._contract_repo.get_by_placement_and_role = AsyncMock(
        side_effect=[None, None, race_winner, _existing_contract(role="owner")]
    )
    # Patch the snapshot builder (it walks SQLAlchemy __table__) and render/PDF.
    with (
        patch(
            "src.core.services.supplementary_agreement_service._build_pii_safe_snapshot",
            return_value={"legal_status": "individual"},
        ),
        patch(
            "src.core.services.supplementary_agreement_service."
            "SupplementaryAgreementService._render_template",
            return_value="<html/>",
        ),
        patch(
            "src.core.services.supplementary_agreement_service."
            "SupplementaryAgreementService._html_to_pdf",
            return_value=None,
        ),
    ):
        adv, _ = await service.generate_for_placement(placement)

    assert adv is race_winner
    session.rollback.assert_awaited()


# ────────────────────────────────────────────────────────────────────────
# ContractEvent emission on first generation
# ────────────────────────────────────────────────────────────────────────


async def test_generate_records_supplementary_generated_event_per_side() -> None:
    """Each freshly-created ДС row produces one `supplementary_generated`
    ContractEvent. Both sides → 2 generated events."""
    placement = _placement()
    record_event = AsyncMock()
    service, _ = _build_service_with_mocks(
        existing_adv=None,
        existing_own=None,
        adv_framework=_framework(role="advertiser", contract_id=50),
        own_framework=_framework(role="owner", contract_id=51),
        record_event_mock=record_event,
    )

    # Patch snapshot builder, render, and PDF to no-ops to focus on event emission.
    with (
        patch(
            "src.core.services.supplementary_agreement_service._build_pii_safe_snapshot",
            return_value={"legal_status": "individual"},
        ),
        patch(
            "src.core.services.supplementary_agreement_service."
            "SupplementaryAgreementService._render_template",
            return_value="<html/>",
        ),
        patch(
            "src.core.services.supplementary_agreement_service."
            "SupplementaryAgreementService._html_to_pdf",
            return_value=None,
        ),
    ):
        await service.generate_for_placement(placement)

    # At least one `supplementary_generated` per side. Notification events may
    # also fire (telegram queue) — we count the typed ones only.
    generated_calls = [
        c
        for c in record_event.await_args_list
        if c.kwargs.get("event_type") == "supplementary_generated"
    ]
    assert len(generated_calls) == 2
    roles_recorded = {c.kwargs["event_metadata"]["role"] for c in generated_calls}
    assert roles_recorded == {"advertiser", "owner"}
