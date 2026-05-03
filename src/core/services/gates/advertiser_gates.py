"""Advertiser-side gate checkers (G01-G03).

G01: Advertiser legal profile complete
G02: Advertiser framework contract signed
G03: Advertiser legal_status compliant (per legal_status type)

Each gate ships two entry points sharing a common body via ``_check_gXX_for_user_id``:

* ``check_gXX(session, placement)`` — placement-side variant; resolves
  advertiser_id from ``placement.advertiser_id``.
* ``check_gXX_user(session, user)`` — user-side variant (5b.7a) for
  non-transition contexts (placement-creation precondition, future
  advertiser-side preconditions); accepts the user directly.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import portal_routes
from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.core.services.fns_validation_service import (
    validate_inn_checksum,
    validate_ogrn_checksum,
)
from src.db.models.placement_request import PlacementRequest
from src.db.models.user import User
from src.db.repositories.contract_repo import ContractRepo
from src.db.repositories.user_repo import UserRepository


async def _check_g01_for_user_id(session: AsyncSession, user_id: int) -> GateResult:
    """Shared body for G01 (placement-side and user-side variants)."""
    user = await UserRepository(session).get_with_legal_profile(user_id)
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


async def check_g01(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G01_ADVERTISER_LEGAL_PROFILE_COMPLETE — placement-side variant.

    Reads User.legal_status_completed flag (cached projection of
    LegalProfileService.check_completeness). Phase A.5 confirmed the
    flag is in sync — sole writer is LegalProfileService, called after
    every LegalProfile mutation.

    Pattern 1 (S-48): receives session, no commit/flush/rollback.
    """
    return await _check_g01_for_user_id(session, placement.advertiser_id)


async def check_g01_user(session: AsyncSession, user: User) -> GateResult:
    """G01 user-side variant (5b.7a). Same semantics as ``check_g01``."""
    return await _check_g01_for_user_id(session, user.id)


async def _check_g02_for_user_id(session: AsyncSession, user_id: int) -> GateResult:
    """Shared body for G02 (placement-side and user-side variants)."""
    is_signed = await ContractRepo(session).has_signed_framework(
        user_id=user_id,
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


async def check_g02(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED — placement-side variant.

    Calls ContractRepo.has_signed_framework — checks Contract row exists
    with contract_status='signed', role='advertiser', signed_at IS NOT NULL.

    Note (L18 candidate): contract_type is hardcoded "advertiser_framework"
    even for owner-side framework contracts in this codebase. Functional;
    naming cleanup deferred to Phase 3 closure batch.

    Note (S1 / Q5 deferred): expires_at is NOT checked. No expiry policy
    in code today; Phase 4+ may add renewal flow + expiry semantics.

    Pattern 1 (S-48): receives session, no commit/flush/rollback.
    """
    return await _check_g02_for_user_id(session, placement.advertiser_id)


async def check_g02_user(session: AsyncSession, user: User) -> GateResult:
    """G02 user-side variant (5b.7a). Same semantics as ``check_g02``."""
    return await _check_g02_for_user_id(session, user.id)


def _g03_pass() -> GateResult:
    return GateResult(
        gate=PlacementGate.G03_ADVERTISER_LEGAL_STATUS_COMPLIANT,
        passed=True,
        blocker=True,
        reason_code=GateReason.OK.value,
    )


def _g03_fail_blocker(reason: GateReason) -> GateResult:
    return GateResult(
        gate=PlacementGate.G03_ADVERTISER_LEGAL_STATUS_COMPLIANT,
        passed=False,
        blocker=True,
        reason_code=reason.value,
        remediation_url=portal_routes.LEGAL_PROFILE,
    )


def _g03_fail_informational(reason: GateReason) -> GateResult:
    """Informational: G01 fires as actual blocker for missing-data root cause.

    Avoids two redundant blocker signals on the same condition.
    """
    return GateResult(
        gate=PlacementGate.G03_ADVERTISER_LEGAL_STATUS_COMPLIANT,
        passed=False,
        blocker=False,
        reason_code=reason.value,
        remediation_url=portal_routes.LEGAL_PROFILE,
    )


async def _check_g03_for_user_id(session: AsyncSession, user_id: int) -> GateResult:
    """Shared body for G03 (placement-side and user-side variants)."""
    user = await UserRepository(session).get_with_legal_profile(user_id)
    if user is None or user.legal_profile is None:
        return _g03_fail_informational(GateReason.LEGAL_PROFILE_MISSING)

    profile = user.legal_profile
    status = profile.legal_status

    # individual — passport-based; INN optional
    if status == "individual":
        if profile.inn and not validate_inn_checksum(profile.inn):
            return _g03_fail_blocker(GateReason.INN_CHECKSUM_INVALID)
        return _g03_pass()

    # All other statuses require INN
    if not profile.inn:
        return _g03_fail_informational(GateReason.INN_MISSING)
    if not validate_inn_checksum(profile.inn):
        return _g03_fail_blocker(GateReason.INN_CHECKSUM_INVALID)

    if status == "self_employed":
        # 5b.8 will add: FNS NPD active status check
        return _g03_pass()

    if status == "individual_entrepreneur":
        if not profile.ogrnip:
            return _g03_fail_informational(GateReason.OGRNIP_MISSING)
        if not validate_ogrn_checksum(profile.ogrnip):
            return _g03_fail_blocker(GateReason.OGRNIP_CHECKSUM_INVALID)
        # Phase 5 will add: EGRIP snapshot freshness check
        return _g03_pass()

    if status == "legal_entity":
        if not profile.ogrn:
            return _g03_fail_informational(GateReason.OGRN_MISSING)
        if not validate_ogrn_checksum(profile.ogrn):
            return _g03_fail_blocker(GateReason.OGRN_CHECKSUM_INVALID)
        # Phase 5 will add: EGRUL snapshot freshness check
        return _g03_pass()

    # Defensive — column is String(30), no DB enum constraint
    return _g03_fail_blocker(GateReason.UNKNOWN_LEGAL_STATUS)


async def check_g03(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G03_ADVERTISER_LEGAL_STATUS_COMPLIANT — placement-side variant.

    Interim (5b.3 / pre-5b.8). Per Marina decision Q1=(a): checksum-only
    validation. Full FNS path deferred to:
    - 5b.8 — FNS provider real (writes fns_verification_status, adds
      check inside this same gate body for self_employed)
    - Phase 5 — EGRUL provider real (writes egrul_egrip_snapshot, adds
      freshness check inside this same gate body for IE/LE)

    The 5b.3 body is NOT a stub — ships a real validator (rejects junk
    INNs/OGRNs/OGRNIPs). 5b.8 / Phase 5 work is *additional* layered
    on top, not a replacement.

    Per-status logic (synthesized from plan §3.B.3 + LegalProfileService
    _REQUIRED_FIELDS_MAP):
    - individual: passport-only; INN optional
    - self_employed: INN + 12-digit checksum
    - individual_entrepreneur: INN + OGRNIP both required + checksums
    - legal_entity: INN + OGRN both required + checksums

    Pattern 1 (S-48): receives session, no commit/flush/rollback.
    """
    return await _check_g03_for_user_id(session, placement.advertiser_id)


async def check_g03_user(session: AsyncSession, user: User) -> GateResult:
    """G03 user-side variant (5b.7a). Same semantics as ``check_g03``."""
    return await _check_g03_for_user_id(session, user.id)
