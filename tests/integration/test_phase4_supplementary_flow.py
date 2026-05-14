"""End-to-end integration test for Phase 4 ДС lifecycle (PROMPT 28 Step 10.2).

Validates the supplementary-agreement happy path:
  1. Seed advertiser + owner with framework contracts already signed.
  2. SupplementaryAgreementService.generate_for_placement creates 2 ДС rows.
  3. G07 gate fails before signing (real body, not PHASE4_PENDING marker).
  4. Advertiser signs their ДС → G07 still fails (only one side).
  5. Owner signs their ДС → G07 passes (both sides signed).
  6. ContractEvent timeline: 2× generated + 2× signed + 1× activated minimum.

Narrow scope — does NOT exercise PlacementTransitionService end-to-end (that
service has its own integration coverage); we verify the gate-result signal
which is the actual handshake between ДС layer and transition layer.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.services.contract_service import ContractService
from src.core.services.gates.agreement_gates import check_g07
from src.core.services.legal_profile_service import LegalProfileService
from src.core.services.supplementary_agreement_service import (
    SupplementaryAgreementService,
)
from src.db.models.contract import Contract
from src.db.models.contract_event import ContractEvent
from src.db.models.placement_request import (
    PlacementRequest,
    PlacementStatus,
    PublicationFormat,
)
from src.db.models.telegram_chat import TelegramChat
from src.db.models.user import User
from src.db.repositories.contract_repo import ContractRepo

pytestmark = pytest.mark.asyncio


async def _seed_phase4_setup(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> tuple[User, User, PlacementRequest, Contract, Contract]:
    """Build advertiser + owner with signed framework contracts + placement.

    Returns: (advertiser, owner, placement, advertiser_framework, owner_framework).
    """
    advertiser = User(telegram_id=992_000_001, username="adv_p4", first_name="A4")
    owner = User(telegram_id=992_000_002, username="own_p4", first_name="O4")
    db_session.add_all([advertiser, owner])
    await db_session.flush()
    await db_session.refresh(advertiser)
    await db_session.refresh(owner)

    await LegalProfileService(db_session).create_profile(
        advertiser.id, legal_profile_data("legal_entity")
    )
    await LegalProfileService(db_session).create_profile(
        owner.id, legal_profile_data("individual_entrepreneur")
    )
    await db_session.flush()

    channel = TelegramChat(
        telegram_id=-1001_777_888_999,
        title="Phase 4 Channel",
        username="phase4_ch",
        owner_user_id=owner.id,
    )
    db_session.add(channel)
    await db_session.flush()
    await db_session.refresh(channel)

    placement = PlacementRequest(
        advertiser_id=advertiser.id,
        owner_id=owner.id,
        channel_id=channel.id,
        status=PlacementStatus.pending_owner,
        publication_format=PublicationFormat.post_24h,
        ad_text="Phase 4 integration ad text",
        proposed_price=Decimal("2000"),
        final_price=Decimal("2000"),
        final_schedule=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
    )
    db_session.add(placement)
    await db_session.flush()
    await db_session.refresh(placement)
    # Need channel relationship preloaded for ДС context (placement.channel.title etc.)
    await db_session.refresh(placement, attribute_names=["channel"])

    # Framework contracts — must be 'signed' for SupplementaryAgreementService
    adv_framework = Contract(
        user_id=advertiser.id,
        contract_type="advertiser_framework",
        contract_status="signed",
        signed_at=datetime(2026, 4, 1, tzinfo=UTC),
        role="advertiser",
        template_version="1.2",
    )
    # ContractRepo.get_framework_contract filters by contract_type='advertiser_framework'
    # for BOTH roles (single repo body, role param narrows the row). Seed owner-side
    # with the same contract_type so the existing query finds it.
    own_framework = Contract(
        user_id=owner.id,
        contract_type="advertiser_framework",
        contract_status="signed",
        signed_at=datetime(2026, 4, 1, tzinfo=UTC),
        role="owner",
        template_version="1.2",
    )
    db_session.add_all([adv_framework, own_framework])
    await db_session.flush()
    await db_session.refresh(adv_framework)
    await db_session.refresh(own_framework)

    return advertiser, owner, placement, adv_framework, own_framework


async def test_full_supplementary_flow_advertiser_owner_signing_unblocks_g07(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    """End-to-end Phase 4 happy path:

    pending_owner placement → ДС generated → G07 fails → advertiser signs →
    G07 still fails (only one side) → owner signs → G07 passes (both sides).
    """
    advertiser, owner, placement, _adv_framework, _own_framework = await _seed_phase4_setup(
        db_session, legal_profile_data
    )

    # Step 1 — generate ДС pair (idempotent service call).
    sup_service = SupplementaryAgreementService(db_session)
    repo = ContractRepo(db_session)
    adv_contract, own_contract = await sup_service.generate_for_placement(placement)

    assert adv_contract.role == "advertiser"
    assert adv_contract.contract_type == "supplementary_agreement"
    assert adv_contract.contract_status == "draft"
    assert adv_contract.placement_id == placement.id
    assert own_contract.role == "owner"
    assert own_contract.contract_status == "draft"

    contracts = await repo.list_supplementary_for_placement(placement.id)
    assert len(contracts) == 2
    assert {c.role for c in contracts} == {"advertiser", "owner"}

    # Step 2 — G07 fails before any signature (real body, not PHASE4_PENDING).
    g07_pre = await check_g07(db_session, placement)
    assert g07_pre.passed is False
    assert g07_pre.reason_code == "supplementary_not_signed"

    # Step 3 — advertiser signs their ДС.
    adv_contract.contract_status = "pending"  # transition draft → pending via state machine surface
    await db_session.flush()
    await ContractService(db_session).sign_contract(
        contract_id=adv_contract.id,
        user_id=advertiser.id,
        method="button_accept",
    )

    # G07 still fails — only one of two signed.
    g07_mid = await check_g07(db_session, placement)
    assert g07_mid.passed is False
    assert g07_mid.reason_code == "supplementary_not_signed"

    # Step 4 — owner signs.
    own_contract.contract_status = "pending"
    await db_session.flush()
    await ContractService(db_session).sign_contract(
        contract_id=own_contract.id,
        user_id=owner.id,
        method="button_accept",
    )

    # G07 now passes — both sides signed.
    g07_final = await check_g07(db_session, placement)
    assert g07_final.passed is True
    assert g07_final.blocker is False
    assert g07_final.reason_code == "ok"

    # Step 5 — ContractEvent timeline: ≥ 2× generated + 2× signed + 1× activated.
    events_result = await db_session.execute(
        select(ContractEvent).where(
            ContractEvent.contract_id.in_([adv_contract.id, own_contract.id])
        )
    )
    events = list(events_result.scalars().all())
    event_types = [e.event_type for e in events]

    assert event_types.count("supplementary_generated") == 2
    assert event_types.count("supplementary_signed") == 2
    # supplementary_activated fires on the final sign (when both reach signed
    # status). One emission per second-signing actor; we accept ≥1.
    assert event_types.count("supplementary_activated") >= 1


async def test_supplementary_generation_is_idempotent_end_to_end(
    db_session: AsyncSession,
    legal_profile_data: Callable[[str], dict[str, Any]],
) -> None:
    """Calling generate_for_placement twice returns the same Contract rows
    (no duplicate INSERTs, no new ContractEvent rows on second call)."""
    _adv, _own, placement, _adv_framework, _own_framework = await _seed_phase4_setup(
        db_session, legal_profile_data
    )

    repo = ContractRepo(db_session)
    sup_service = SupplementaryAgreementService(db_session)
    adv1, own1 = await sup_service.generate_for_placement(placement)
    adv2, own2 = await sup_service.generate_for_placement(placement)

    assert adv1.id == adv2.id
    assert own1.id == own2.id

    contracts = await repo.list_supplementary_for_placement(placement.id)
    assert len(contracts) == 2

    # Generated events: exactly 2 (one per side), not 4.
    gen_events_result = await db_session.execute(
        select(ContractEvent).where(
            ContractEvent.contract_id.in_([adv1.id, own1.id]),
            ContractEvent.event_type == "supplementary_generated",
        )
    )
    assert len(list(gen_events_result.scalars().all())) == 2
