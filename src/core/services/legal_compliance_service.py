"""Legal compliance service — placement gate dispatch.

Phase 3a Block 2 ships only the dispatch skeleton. Gate-checker logic
lives in src/core/services/gates/ (Phase 3b stubs). The declarative
transition→gates table is Phase 3b territory.

S-48: methods do NOT open or commit transactions. Caller owns lifecycle.
"""

from collections.abc import Awaitable, Callable
from typing import Literal

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


# Resolution table: which gates apply to each placement state transition.
# Keys mirror placement_transition_service._ALLOW_LIST exactly — every
# allow-listed (from, to) pair has an entry here. Empty frozenset means
# the transition has no compliance preconditions.
#
# G13-G18 are payout-side gates and intentionally absent — they belong to
# PayoutRequest lifecycle, not placement transitions (Phase 5 territory).
# G07/G15/G16 (Phase 4) ARE included; their bodies raise NotImplementedError
# until those phases land.
_TRANSITION_GATES: dict[
    tuple[PlacementStatus, PlacementStatus], frozenset[PlacementGate]
] = {
    (PlacementStatus.pending_owner, PlacementStatus.counter_offer): frozenset(),
    (PlacementStatus.pending_owner, PlacementStatus.pending_payment): frozenset(
        {PlacementGate.G07_SUPPLEMENTARY_AGREEMENT_SIGNED}
    ),
    (PlacementStatus.pending_owner, PlacementStatus.cancelled): frozenset(),
    (PlacementStatus.counter_offer, PlacementStatus.pending_owner): frozenset(),
    (PlacementStatus.counter_offer, PlacementStatus.pending_payment): frozenset(
        {PlacementGate.G07_SUPPLEMENTARY_AGREEMENT_SIGNED}
    ),
    (PlacementStatus.counter_offer, PlacementStatus.cancelled): frozenset(),
    (PlacementStatus.pending_payment, PlacementStatus.escrow): frozenset(),
    (PlacementStatus.pending_payment, PlacementStatus.cancelled): frozenset(),
    (PlacementStatus.escrow, PlacementStatus.published): frozenset(
        {
            PlacementGate.G08_ERID_REGISTERED,
            PlacementGate.G09_ORD_CONTRACT_REPORTED,
            PlacementGate.G10_PLACEMENT_TEXT_MARKED,
        }
    ),
    (PlacementStatus.escrow, PlacementStatus.failed): frozenset(),
    (PlacementStatus.escrow, PlacementStatus.failed_permissions): frozenset(),
    (PlacementStatus.escrow, PlacementStatus.refunded): frozenset(),
    (PlacementStatus.escrow, PlacementStatus.cancelled): frozenset(),
    (PlacementStatus.published, PlacementStatus.completed): frozenset(
        {
            PlacementGate.G11_PUBLICATION_VERIFIED,
            PlacementGate.G12_PUBLICATION_REPORTED_TO_ORD,
        }
    ),
    (PlacementStatus.published, PlacementStatus.failed): frozenset(),
    (PlacementStatus.published, PlacementStatus.refunded): frozenset(),
    (PlacementStatus.published, PlacementStatus.cancelled): frozenset(),
    (PlacementStatus.failed, PlacementStatus.refunded): frozenset(),
    (PlacementStatus.failed_permissions, PlacementStatus.refunded): frozenset(),
}


# Resolution table: which gates apply to a user acting in a given role,
# in non-transition contexts (channel-add for owner, placement-creation
# for advertiser).
#
# G06 included for "owner" per plan §3.B.6 verbatim (Marina decision Q2 lean).
# All gate bodies remain NotImplementedError until 5b.3+ ships logic.
_USER_ROLE_GATES: dict[str, frozenset[PlacementGate]] = {
    "owner": frozenset(
        {
            PlacementGate.G04_OWNER_LEGAL_PROFILE_COMPLETE,
            PlacementGate.G05_OWNER_FRAMEWORK_CONTRACT_SIGNED,
            PlacementGate.G06_OWNER_PAYOUT_METHOD_VALID,
        }
    ),
    "advertiser": frozenset(
        {
            PlacementGate.G01_ADVERTISER_LEGAL_PROFILE_COMPLETE,
            PlacementGate.G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED,
            PlacementGate.G03_ADVERTISER_LEGAL_STATUS_COMPLIANT,
        }
    ),
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
        """Return the compliance gates required for this placement state transition.

        The resolution table mirrors PlacementTransitionService._ALLOW_LIST —
        every allow-listed (from, to) pair has an entry. Empty list means
        the transition has no compliance preconditions.

        G13-G18 (payout-side) intentionally absent — those gates belong to
        PayoutRequest lifecycle and will be resolved by a separate (Phase 5)
        payout-compliance service.

        Raises:
            ValueError: if (from_status, to_status) is not in the resolution
                table. Indicates either an unknown transition (caller bug)
                or drift between this table and the placement allow-list
                (covered by test_table_keys_match_allow_list).
        """
        key = (from_status, to_status)
        if key not in _TRANSITION_GATES:
            raise ValueError(
                f"Transition {from_status.value} -> {to_status.value} "
                f"is not in the gates resolution table. "
                f"Either it is not in the placement allow-list, or the table is incomplete."
            )
        return list(_TRANSITION_GATES[key])

    def gates_for_user_role(
        self,
        role: Literal["owner", "advertiser"],
    ) -> list[PlacementGate]:
        """Return the compliance gates required for a user acting in `role`.

        Used by non-transition contexts (channel-add for owner, placement
        creation for advertiser) where the precondition is determined by
        the user's role alone, not by a placement state transition.

        The `user` parameter is intentionally absent — resolution is pure
        role lookup. The downstream check_gates_for_user_role (future)
        will take session+user+role for dispatch into check_gate. This
        mirrors the gates_for_transition / check_gates_for_transition
        resolution-vs-check split.

        Raises:
            ValueError: if `role` is not "owner" or "advertiser". The
                Literal annotation already prevents this at type-check
                time; the runtime check is defence-in-depth.
        """
        if role not in _USER_ROLE_GATES:
            raise ValueError(
                f"Unknown role: {role!r}. Expected one of: 'owner', 'advertiser'."
            )
        return list(_USER_ROLE_GATES[role])

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
