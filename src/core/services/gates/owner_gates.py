"""Owner-side gate checkers (G04-G06, G19).

G04: Owner legal profile complete
G05: Owner framework contract signed
G06: Owner payout method valid (real-now lookup; Phase 5 swaps for provider-validated body)
G19: Channel ФЗ-303 blogger registry verification (BL-107)

G04-G06 ship two entry points sharing a common body via ``_check_gXX_for_user_id``:

* ``check_gXX(session, placement)`` — placement-side variant (used by
  ``LegalComplianceService.check_gates_for_transition``); resolves owner_id
  from ``placement.owner_id``.
* ``check_gXX_user(session, user)`` — user-side variant (used by
  ``LegalComplianceService.check_gates_for_user_role``, called from
  channel-add hook); accepts the user directly. Added in 5b.7a.

G19 ships two entry points sharing ``_check_g19_core``:

* ``check_g19(session, placement)`` — placement-side variant (defense-in-
  depth для channels created до G19 enforcement или threshold-crossed).
* ``check_g19_channel_add(session, user, channel_data)`` — channel-context
  variant invoked from channel-add hook (Phase B.4 wires).
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.constants import portal_routes
from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.channel_add_context import ChannelAddContext
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest
from src.db.models.user import User
from src.db.repositories.contract_repo import ContractRepo
from src.db.repositories.payout_repo import PayoutRepository
from src.db.repositories.user_repo import UserRepository

# Phase B.2 temporary state — Phase B.3 заменит на settings.rkn_threshold_subscribers.
# 10_000 = ФЗ-303 threshold (channels с monthly audience ≥10k must register
# в Roskomnadzor blogger registry).
_DEFAULT_RKN_THRESHOLD = 10_000


async def _check_g04_for_user_id(session: AsyncSession, user_id: int) -> GateResult:
    """Shared body for G04 (placement-side and user-side variants)."""
    user = await UserRepository(session).get_with_legal_profile(user_id)
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


async def check_g04(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G04_OWNER_LEGAL_PROFILE_COMPLETE — placement-side variant.

    Symmetric mirror of G01 (advertiser) using ``placement.owner_id``.
    Reads owner ``User.legal_status_completed`` flag — same column for
    both roles (User-level, not role-scoped). 5b.3 A.5 confirmed the
    flag is in sync with reality (sole writer is
    ``LegalProfileService.check_completeness``).

    Pattern 1 (S-48): receives session, no commit/flush/rollback.
    """
    return await _check_g04_for_user_id(session, placement.owner_id)


async def check_g04_user(session: AsyncSession, user: User) -> GateResult:
    """G04 user-side variant (5b.7a) for channel-add hook.

    Same semantics as ``check_g04`` but takes the User directly. Both
    variants share ``_check_g04_for_user_id``.
    """
    return await _check_g04_for_user_id(session, user.id)


async def _check_g05_for_user_id(session: AsyncSession, user_id: int) -> GateResult:
    """Shared body for G05 (placement-side and user-side variants)."""
    is_signed = await ContractRepo(session).has_signed_framework(
        user_id=user_id,
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


async def check_g05(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G05_OWNER_FRAMEWORK_CONTRACT_SIGNED — placement-side variant.

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
    return await _check_g05_for_user_id(session, placement.owner_id)


async def check_g05_user(session: AsyncSession, user: User) -> GateResult:
    """G05 user-side variant (5b.7a) for channel-add hook.

    Same semantics as ``check_g05`` but takes the User directly.
    """
    return await _check_g05_for_user_id(session, user.id)


async def _check_g06_for_user_id(session: AsyncSession, user_id: int) -> GateResult:
    """Shared body for G06 (placement-side and user-side variants).

    5b.7a real-now semantics (разморожен из PHASE5_PENDING marker, 5b.4):
    channel-add hook (§3.B.6) requires gate evaluation today, not Phase 5.

    Decision logic:

    * Owner has at least one PayoutRequest with ``payout_method_type IS NOT
      NULL`` and status NOT IN (rejected, cancelled) → PASS (valid method).
    * Owner has zero PayoutRequest records → PASS (pre-payout-setup state;
      channel-add valid before owner attempts payout setup).
    * Owner has PayoutRequest records but none qualify as valid → FAIL
      with ``payout_method_invalid`` reason code (setup attempted but all
      records have payout_method_type=NULL OR status in rejected/cancelled).

    Phase 5 swap: replaces this body with provider-validated state
    (YooKassa recipient-check, SBP registration, YooMoney OAuth, bank
    BIK + correspondent account validation per Marina M4/M6). Body
    tightens "valid" from "DB record exists" to "provider-confirmed";
    semantics complementary, not contract-changing.
    """
    repo = PayoutRepository(session)
    valid = await repo.get_valid_for_owner(user_id)
    if valid is not None:
        return GateResult(
            gate=PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID,
            passed=True,
            blocker=True,
            reason_code=GateReason.OK.value,
        )
    all_payouts = await repo.get_by_owner(user_id)
    if not all_payouts:
        return GateResult(
            gate=PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID,
            passed=True,
            blocker=True,
            reason_code=GateReason.OK.value,
        )
    return GateResult(
        gate=PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID,
        passed=False,
        blocker=True,
        reason_code=GateReason.PAYOUT_METHOD_INVALID.value,
        remediation_url=None,
    )


async def check_g06(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G06_OWNER_PAYOUT_METHOD_VALID — placement-side variant.

    5b.7a: разморожен из PHASE5_PENDING marker (5b.4) per channel-add
    hook requirement (§3.B.6). Body delegates to ``_check_g06_for_user_id``
    which performs real-now lookup via ``payout_repo.get_valid_for_owner``
    + ``get_by_owner``.

    Phase 5 swap = real provider validation (recipient-check, SBP
    registration, BIK validation per Marina M4/M6). Today's body checks
    "valid record exists in DB"; Phase 5 will tighten "valid" to
    "provider-confirmed valid".

    Pattern 1 (S-48): receives session, no commit/flush/rollback.
    """
    return await _check_g06_for_user_id(session, placement.owner_id)


async def check_g06_user(session: AsyncSession, user: User) -> GateResult:
    """G06 user-side variant (5b.7a) for channel-add hook.

    Same semantics as ``check_g06`` but takes the User directly.
    """
    return await _check_g06_for_user_id(session, user.id)


def _check_g19_core(
    member_count: int,
    is_test: bool,
    is_blogger_registry_verified: bool,
    blogger_registry_application_number: str | None,
) -> GateResult:
    """Pure G19 evaluation logic — no I/O, no DB lookup (BL-107).

    ФЗ-303 requires Telegram channels с monthly audience ≥10k to register
    в Roskomnadzor blogger registry. Gate body reads pre-populated channel
    state и applies short-circuit precedence:

    1. ``is_test=True`` — exempt (admin test-mode carve-out, parity с G02 test bypass)
    2. ``member_count < threshold`` — regulation not applicable
    3. ``is_blogger_registry_verified=True`` — verified, pass
    4. ``application_number is not None`` — manual evidence pending review (block)
    5. otherwise — not verified (block, default fail)

    Phase B.2 hardcodes threshold = ``_DEFAULT_RKN_THRESHOLD`` (10_000); Phase B.3
    swaps к ``settings.rkn_threshold_subscribers``. ``remediation_url=None`` для
    fail cases; Phase B.5 populates после admin review UI ships.

    Pure function — no async, no session. Testable как pure-logic table.
    """
    if is_test:
        return GateResult(
            gate=PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED,
            passed=True,
            blocker=False,
            reason_code=GateReason.OK.value,
        )
    if member_count < _DEFAULT_RKN_THRESHOLD:
        return GateResult(
            gate=PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED,
            passed=True,
            blocker=False,
            reason_code=GateReason.OK.value,
        )
    if is_blogger_registry_verified:
        return GateResult(
            gate=PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED,
            passed=True,
            blocker=False,
            reason_code=GateReason.OK.value,
        )
    if blogger_registry_application_number is not None:
        return GateResult(
            gate=PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED,
            passed=False,
            blocker=True,
            reason_code=GateReason.BLOGGER_REGISTRY_PENDING_REVIEW.value,
            remediation_url=None,
        )
    return GateResult(
        gate=PlacementGate.G19_BLOGGER_REGISTRY_VERIFIED,
        passed=False,
        blocker=True,
        reason_code=GateReason.BLOGGER_REGISTRY_NOT_VERIFIED.value,
        remediation_url=None,
    )


async def check_g19(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G19_BLOGGER_REGISTRY_VERIFIED — placement-side variant (BL-107).

    Defense-in-depth для channels created до G19 enforcement existed
    или channels чей ``member_count`` пересёк ФЗ-303 threshold после
    channel-add. Reads ``placement.channel`` TelegramChat state.

    Phase B.2 wired в _TRANSITION_GATES at (pending_owner, pending_payment)
    + (counter_offer, pending_payment) — same transitions как G07 supplementary
    agreement gate. Fires BEFORE money moves to escrow.

    Pattern 1 (S-48): receives session (unused в pure-logic body — kept для
    signature parity с _GATE_CHECKERS contract), no commit/flush/rollback.
    """
    channel = placement.channel
    return _check_g19_core(
        member_count=channel.member_count,
        is_test=channel.is_test,
        is_blogger_registry_verified=channel.is_blogger_registry_verified,
        blogger_registry_application_number=channel.blogger_registry_application_number,
    )


async def check_g19_channel_add(
    session: AsyncSession,
    user: User,
    channel_data: ChannelAddContext,
) -> GateResult:
    """G19_BLOGGER_REGISTRY_VERIFIED — channel-context variant (BL-107).

    Primary G19 gate, fires at channel-add time из API router + bot
    handler (Phase B.4 wires invocations). Reads pre-populated
    ``ChannelAddContext`` snapshot — Phase B.4 channel-add helper sets
    ``is_blogger_registry_verified`` based on Trustchannelbot admin check
    + DB lookup для re-adds.

    Pattern 1 (S-48): receives session (unused в pure-logic body — kept
    для _CHANNEL_CONTEXT_GATE_CHECKERS signature parity), no transaction
    management.

    The ``user`` parameter is unused в G19 body (gate evaluates channel
    state, not owner state) — kept для registry signature uniformity
    с future per-channel gates that may consult owner attributes.
    """
    return _check_g19_core(
        member_count=channel_data.member_count,
        is_test=channel_data.is_test,
        is_blogger_registry_verified=channel_data.is_blogger_registry_verified,
        blogger_registry_application_number=channel_data.blogger_registry_application_number,
    )
