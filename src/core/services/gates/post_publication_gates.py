"""Post-publication gate checkers (G11-G12).

G11: Publication verified (post is live in the channel and matches sent text)
G12: Publication reported to ОРД (per ФЗ-38 ст. 18.1 + ПП-1427)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.gate_reason import GateReason
from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.placement_request import PlacementRequest
from src.db.repositories.ord_registration_repo import OrdRegistrationRepo


async def check_g11(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G11_PUBLICATION_VERIFIED.

    Reads ``placement.message_id`` as authoritative signal that the post
    was accepted by Telegram (durably committed via S-48 external-
    boundary commit in ``publication_service.publish_placement``).

    Phase 6 (per plan §6.B.3 / G11 hardening) may add an active
    round-trip verification (e.g., ``bot.get_chat`` / ``getMessage``)
    and a writer for ``placement.publication_verified``. At that point
    this body switches to ``if placement.publication_verified``. The
    ``placement.publication_verified`` column added in Block 1 is the
    Phase 6 hook.

    Pattern 1 (S-48): receives session (unused), no commit/flush/rollback.
    """
    if placement.message_id is None:
        return GateResult(
            gate=PlacementGate.G11_PUBLICATION_VERIFIED,
            passed=False,
            blocker=True,
            reason_code=GateReason.PUBLICATION_NOT_VERIFIED.value,
            remediation_url=None,
        )
    return GateResult(
        gate=PlacementGate.G11_PUBLICATION_VERIFIED,
        passed=True,
        blocker=True,
        reason_code=GateReason.OK.value,
    )


async def check_g12(session: AsyncSession, placement: PlacementRequest) -> GateResult:
    """G12_PUBLICATION_REPORTED_TO_ORD.

    Reads ``OrdRegistration.status``. Pass iff status == ``"reported"``
    (set by ``OrdService.report_publication`` after provider call).

    Block 1 fields ``OrdRegistration.published_at`` and ``deadline_at``
    exist for ФЗ-38 deadline tracking but have no writer today;
    Phase 6 hardening (or beyond) is the planned source. Gate body
    today reads only ``status`` — sufficient for Phase 3b interim.

    Pattern 1 (S-48): receives session, no commit/flush/rollback.
    """
    registration = await OrdRegistrationRepo(session).get_by_placement(placement.id)
    if registration is None or registration.status != "reported":
        return GateResult(
            gate=PlacementGate.G12_PUBLICATION_REPORTED_TO_ORD,
            passed=False,
            blocker=True,
            reason_code=GateReason.PUBLICATION_NOT_REPORTED_TO_ORD.value,
            remediation_url=None,
        )
    return GateResult(
        gate=PlacementGate.G12_PUBLICATION_REPORTED_TO_ORD,
        passed=True,
        blocker=True,
        reason_code=GateReason.OK.value,
    )
