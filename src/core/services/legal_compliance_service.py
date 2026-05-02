"""Legal compliance service — placement gate dispatch.

Phase 3a Block 2 ships only the dispatch skeleton. Gate-checker logic
lives in src/core/services/gates/ (Phase 3b stubs). The declarative
transition→gates table is Phase 3b territory.

S-48: methods do NOT open or commit transactions. Caller owns lifecycle.
"""

from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.core.services.gates import (
    advertiser_gates,
    agreement_gates,
    owner_gates,
    payout_gates,
    post_publication_gates,
    publication_gates,
)
from src.db.models.placement_request import PlacementRequest, PlacementStatus

GateCheckerFn = Callable[[AsyncSession, PlacementRequest], Awaitable[GateResult]]


_GATE_CHECKERS: dict[PlacementGate, GateCheckerFn] = {
    PlacementGate.G01_ADVERTISER_LEGAL_PROFILE_COMPLETE: advertiser_gates.check_g01,
    PlacementGate.G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED: advertiser_gates.check_g02,
    PlacementGate.G03_ADVERTISER_LEGAL_STATUS_COMPLIANT: advertiser_gates.check_g03,
    PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE: owner_gates.check_g04,
    PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED: owner_gates.check_g05,
    PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID: owner_gates.check_g06,
    PlacementGate.G07_SUPPLEMENTARY_AGREEMENT_SIGNED: agreement_gates.check_g07,
    PlacementGate.G08_ERID_REGISTERED: publication_gates.check_g08,
    PlacementGate.G09_ORD_CONTRACT_REPORTED: publication_gates.check_g09,
    PlacementGate.G10_PLACEMENT_TEXT_MARKED: publication_gates.check_g10,
    PlacementGate.G11_PUBLICATION_VERIFIED: post_publication_gates.check_g11,
    PlacementGate.G12_PUBLICATION_REPORTED_TO_ORD: post_publication_gates.check_g12,
    PlacementGate.G13_PUBLICATION_PERIOD_ELAPSED: payout_gates.check_g13,
    PlacementGate.G14_ACT_GENERATED: payout_gates.check_g14,
    PlacementGate.G15_ACT_SIGNED_BOTH_SIDES: payout_gates.check_g15,
    PlacementGate.G16_TAX_RECEIPT_ISSUED: payout_gates.check_g16,
    PlacementGate.G17_VAT_OBLIGATION_HANDLED: payout_gates.check_g17,
    PlacementGate.G18_PAYOUT_REPORTED_TO_ORD: payout_gates.check_g18,
}


class LegalComplianceService:
    """Coordinator for placement gate evaluation.

    S-48 contract: methods do NOT manage transactions. The caller (router
    or orchestrating service) owns the session lifecycle.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def gates_for_transition(
        self,
        from_status: PlacementStatus,
        to_status: PlacementStatus,
    ) -> list[PlacementGate]:
        """Return the list of gates required to move from `from_status` to `to_status`.

        Phase 3b: declarative transition→gates table goes here.
        """
        raise NotImplementedError(
            "Phase 3b: declarative transition→gates table not yet populated"
        )

    async def check_gate(
        self,
        gate: PlacementGate,
        placement: PlacementRequest,
    ) -> GateResult:
        """Dispatch to the appropriate gate-checker function.

        The dispatch logic itself is real (Block 2). The checker bodies
        all raise NotImplementedError until Phase 3b fills them.
        """
        checker = _GATE_CHECKERS.get(gate)
        if checker is None:
            raise NotImplementedError(f"No gate-checker registered for {gate.name}")
        return await checker(self._session, placement)

    async def check_gates_for_transition(
        self,
        placement: PlacementRequest,
        to_status: PlacementStatus,
    ) -> list[GateResult]:
        """Evaluate all gates required for the proposed transition.

        Resolves required gates via `gates_for_transition`, then dispatches
        each through `check_gate`. Returns the list in evaluation order.
        """
        required = self.gates_for_transition(placement.status, to_status)
        results: list[GateResult] = []
        for gate in required:
            results.append(await self.check_gate(gate, placement))
        return results
