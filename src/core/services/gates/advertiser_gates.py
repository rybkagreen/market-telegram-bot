"""Advertiser-side gate checkers (G01-G03).

G01: Advertiser legal profile complete
G02: Advertiser framework contract signed
G03: Advertiser legal_status compliant (per legal_status type)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import portal_routes
from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest
from src.db.repositories.contract_repo import ContractRepo
from src.db.repositories.user_repo import UserRepository


async def check_g01(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G01_ADVERTISER_LEGAL_PROFILE_COMPLETE.

    Reads User.legal_status_completed flag (cached projection of
    LegalProfileService.check_completeness). Phase A.5 confirmed the
    flag is in sync — sole writer is LegalProfileService, called after
    every LegalProfile mutation.

    Pattern 1 (S-48): receives session, no commit/flush/rollback.
    """
    user = await UserRepository(session).get_with_legal_profile(placement.advertiser_id)
    if user is None:
        return GateResult(
            gate=PlacementGate.G01_ADVERTISER_LEGAL_PROFILE_COMPLETE,
            passed=False,
            blocker=True,
            reason_code=GateReason.USER_NOT_FOUND.value,
            remediation_url=None,
        )
    if user.legal_profile is None:
        return GateResult(
            gate=PlacementGate.G01_ADVERTISER_LEGAL_PROFILE_COMPLETE,
            passed=False,
            blocker=True,
            reason_code=GateReason.LEGAL_PROFILE_MISSING.value,
            remediation_url=portal_routes.LEGAL_PROFILE,
        )
    if not user.legal_status_completed:
        return GateResult(
            gate=PlacementGate.G01_ADVERTISER_LEGAL_PROFILE_COMPLETE,
            passed=False,
            blocker=True,
            reason_code=GateReason.LEGAL_PROFILE_INCOMPLETE.value,
            remediation_url=portal_routes.LEGAL_PROFILE,
        )
    return GateResult(
        gate=PlacementGate.G01_ADVERTISER_LEGAL_PROFILE_COMPLETE,
        passed=True,
        blocker=True,
        reason_code=GateReason.OK.value,
    )


async def check_g02(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED.

    Calls ContractRepo.has_signed_framework — checks Contract row exists
    with contract_status='signed', role='advertiser', signed_at IS NOT NULL.

    Note (L18 candidate): contract_type is hardcoded "advertiser_framework"
    even for owner-side framework contracts in this codebase. Functional;
    naming cleanup deferred to Phase 3 closure batch.

    Note (S1 / Q5 deferred): expires_at is NOT checked. No expiry policy
    in code today; Phase 4+ may add renewal flow + expiry semantics.

    Pattern 1 (S-48): receives session, no commit/flush/rollback.
    """
    is_signed = await ContractRepo(session).has_signed_framework(
        user_id=placement.advertiser_id,
        role="advertiser",
    )
    if is_signed:
        return GateResult(
            gate=PlacementGate.G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED,
            passed=True,
            blocker=True,
            reason_code=GateReason.OK.value,
        )
    return GateResult(
        gate=PlacementGate.G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED,
        passed=False,
        blocker=True,
        reason_code=GateReason.FRAMEWORK_CONTRACT_UNSIGNED.value,
        remediation_url=portal_routes.CONTRACTS,
    )


async def check_g03(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G03_ADVERTISER_LEGAL_STATUS_COMPLIANT — Phase 3b stub."""
    raise NotImplementedError(
        f"Phase 3b: {PlacementGate.G03_ADVERTISER_LEGAL_STATUS_COMPLIANT.name}"
    )
