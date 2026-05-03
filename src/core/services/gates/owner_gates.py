"""Owner-side gate checkers (G04-G06).

G04: Owner legal profile complete
G05: Owner framework contract signed
G06: Owner payout method valid (Phase 5 pending marker)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import portal_routes
from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest
from src.db.repositories.contract_repo import ContractRepo
from src.db.repositories.user_repo import UserRepository


async def check_g04(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G04_OWNER_LEGAL_PROFILE_COMPLETE.

    Symmetric mirror of G01 (advertiser) using ``placement.owner_id``.
    Reads owner ``User.legal_status_completed`` flag — same column for
    both roles (User-level, not role-scoped). 5b.3 A.5 confirmed the
    flag is in sync with reality (sole writer is
    ``LegalProfileService.check_completeness``).

    Pattern 1 (S-48): receives session, no commit/flush/rollback.
    """
    user = await UserRepository(session).get_with_legal_profile(placement.owner_id)
    if user is None:
        return GateResult(
            gate=PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE,
            passed=False,
            blocker=True,
            reason_code=GateReason.USER_NOT_FOUND.value,
            remediation_url=None,
        )
    if user.legal_profile is None:
        return GateResult(
            gate=PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE,
            passed=False,
            blocker=True,
            reason_code=GateReason.LEGAL_PROFILE_MISSING.value,
            remediation_url=portal_routes.LEGAL_PROFILE,
        )
    if not user.legal_status_completed:
        return GateResult(
            gate=PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE,
            passed=False,
            blocker=True,
            reason_code=GateReason.LEGAL_PROFILE_INCOMPLETE.value,
            remediation_url=portal_routes.LEGAL_PROFILE,
        )
    return GateResult(
        gate=PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE,
        passed=True,
        blocker=True,
        reason_code=GateReason.OK.value,
    )


async def check_g05(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G05_OWNER_FRAMEWORK_CONTRACT_SIGNED.

    Symmetric mirror of G02 (advertiser) with ``role="owner"``.
    ``Contract.role`` discriminator is the source of truth (see
    ``src/db/models/contract.py:45`` — `'owner' | 'advertiser'`).

    Note (L18, deferred to Phase 3 closure): ``contract_type`` is
    hardcoded ``"advertiser_framework"`` for both roles in
    ``ContractRepo.get_framework_contract`` — misleading umbrella name;
    role discriminator on ``Contract.role`` works correctly.

    Note (S1, deferred): ``Contract.expires_at`` is NOT checked. No
    expiry policy in code today; Phase 4+ may add renewal flow.

    Pattern 1 (S-48): receives session, no commit/flush/rollback.
    """
    is_signed = await ContractRepo(session).has_signed_framework(
        user_id=placement.owner_id,
        role="owner",
    )
    if is_signed:
        return GateResult(
            gate=PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED,
            passed=True,
            blocker=True,
            reason_code=GateReason.OK.value,
        )
    return GateResult(
        gate=PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED,
        passed=False,
        blocker=True,
        reason_code=GateReason.FRAMEWORK_CONTRACT_UNSIGNED.value,
        remediation_url=portal_routes.CONTRACTS,
    )


async def check_g06(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G06_OWNER_PAYOUT_METHOD_VALID — Phase 5 pending marker.

    Per Marina M4 (payout method matrix) + M6 (per-method tax receipts):
    real per-method validation is Phase 5 territory. Phase 5 will fill
    this body with:

    - bank_card: YooKassa Payouts recipient-check verification
    - sbp: SBP bank selector + recipient-check
    - bank_transfer: BIK + corresponding-account validation (IE / LE)

    Interim 5b.4 marker semantics: ``blocker=True`` so the channel-add
    hook (5b.7) sees the gate as a decline reason and surfaces the
    ``PHASE5_PENDING`` reason_code to the owner. Channel-add can integrate
    end-to-end now; Phase 5 swaps the body without touching call sites.

    Pattern 1 (S-48): receives session (unused), no commit/flush/rollback.
    """
    return GateResult(
        gate=PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID,
        passed=False,
        blocker=True,
        reason_code=GateReason.PHASE5_PENDING.value,
        remediation_url=None,
    )
