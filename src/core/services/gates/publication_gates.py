"""Pre-publication gate checkers (G08-G10).

G08: ERID registered with ОРД
G09: ORD contract reported
G10: Placement text marked as advertising (`Реклама. erid: ...`)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest
from src.db.repositories.ord_registration_repo import OrdRegistrationRepo


async def check_g08(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G08_ERID_REGISTERED.

    Reads OrdRegistration row for placement. Pass iff row exists AND
    `erid` is set. Phase 6.B.3 deterministic alignment: when the active
    provider is "stub", the gate short-circuits to pass — stub mode
    intentionally publishes без erid (the same conditional that
    publication_service._build_marked_text follows).

    Pattern 1 (S-48): receives session, no commit/flush/rollback.
    """
    if settings.ord_provider == "stub":
        return GateResult(
            gate=PlacementGate.G08_ERID_REGISTERED,
            passed=True,
            blocker=True,
            reason_code=GateReason.OK.value,
        )
    registration = await OrdRegistrationRepo(session).get_by_placement(placement.id)
    if registration is None or not registration.erid:
        return GateResult(
            gate=PlacementGate.G08_ERID_REGISTERED,
            passed=False,
            blocker=True,
            reason_code=GateReason.ERID_NOT_REGISTERED.value,
            remediation_url=None,
        )
    return GateResult(
        gate=PlacementGate.G08_ERID_REGISTERED,
        passed=True,
        blocker=True,
        reason_code=GateReason.OK.value,
    )


async def check_g09(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G09_ORD_CONTRACT_REPORTED.

    Reads OrdRegistration.contract_ord_id (the ORD-provider-side contract
    ID, NOT the local Contract FK). Pass iff row exists AND
    contract_ord_id is set.

    Pattern 1 (S-48): receives session, no commit/flush/rollback.
    """
    registration = await OrdRegistrationRepo(session).get_by_placement(placement.id)
    if registration is None or not registration.contract_ord_id:
        return GateResult(
            gate=PlacementGate.G09_ORD_CONTRACT_REPORTED,
            passed=False,
            blocker=True,
            reason_code=GateReason.ORD_CONTRACT_NOT_REPORTED.value,
            remediation_url=None,
        )
    return GateResult(
        gate=PlacementGate.G09_ORD_CONTRACT_REPORTED,
        passed=True,
        blocker=True,
        reason_code=GateReason.OK.value,
    )


async def check_g10(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G10_PLACEMENT_TEXT_MARKED.

    Verifies the precondition for ERID marker rendering: ``placement.erid``
    is set. Marker is computed JIT at publish time by
    ``publication_service._build_marked_text`` — gate does not invoke the
    helper, just checks the input that drives marker presence.

    ``placement.ad_text`` NOT NULL by schema; gate skips empty-string check
    (defensive only; would never trigger in production flow).

    Pattern 1 (S-48): receives session (unused), no commit/flush/rollback.
    """
    if not placement.erid:
        return GateResult(
            gate=PlacementGate.G10_PLACEMENT_TEXT_MARKED,
            passed=False,
            blocker=True,
            reason_code=GateReason.PLACEMENT_TEXT_NOT_MARKED.value,
            remediation_url=None,
        )
    return GateResult(
        gate=PlacementGate.G10_PLACEMENT_TEXT_MARKED,
        passed=True,
        blocker=True,
        reason_code=GateReason.OK.value,
    )
