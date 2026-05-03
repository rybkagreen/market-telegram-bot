"""Payout compliance service — payout-side gate dispatch (Phase 5 boundary).

5b.7b ships only the skeleton:

* class signature
* empty resolution registries (``_PAYOUT_GATE_CHECKERS``,
  ``_PAYOUT_TRANSITION_GATES``, ``_PAYOUT_CREATE_GATES``)
* dispatcher methods with their full logic — bodies ready, registries empty

Phase 5 fills the registries (no method-body changes for the wired
dispatchers). Until then, ``gates_for_payout_transition`` /
``gates_for_payout_create`` raise ``ValueError`` (empty table) and
``check_gate`` raises ``NotImplementedError`` (no checker registered).
``check_gates_for_payout_create`` raises ``NotImplementedError`` by design
— Phase 5 chooses the dispatch path (signature impedance vs PayoutRequest-
keyed checkers, see investigation O.I).

Architectural sibling to ``LegalComplianceService`` — same pattern, different
domain (payout lifecycle vs placement lifecycle / user-role checks).

Service partition (5b.7b Marina Q6=(а), clean boundaries):
``PayoutComplianceService`` owns ONLY payout-specific gates (G13-G18).
User-role gates (G04+G05+G06) remain ``LegalComplianceService`` territory;
callers invoke BOTH services for full payout-create gate evaluation. G06
is therefore intentionally absent from ``_PAYOUT_GATE_CHECKERS``.

G13/G14 bodies (in ``src/core/services/gates/payout_gates.py``) currently
operate on ``PlacementRequest``; Phase 5 may add ``PayoutRequest`` variants
OR delegate via ``payout.placement_id`` link (deferred FK; skeleton's empty
registry preserves both paths).

S-48: methods do NOT manage transactions. Caller owns lifecycle.
"""

from collections.abc import Awaitable, Callable
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.enums.placement_gate import PlacementGate
from src.core.schemas.gate_result import GateResult
from src.db.models.payout import PayoutRequest, PayoutStatus
from src.db.models.user import User

PayoutGateCheckerFn = Callable[[AsyncSession, PayoutRequest], Awaitable[GateResult]]


# Empty registries — Phase 5 populates. Skeleton ships dispatcher logic
# referencing these dicts; Phase 5 changes are ADDITIVE only (insert
# entries; do not change shape). Phase 5 may add a parallel registry of
# user-keyed checkers if it chooses that dispatch path for create-time
# checks (see check_gates_for_payout_create docstring).
_PAYOUT_GATE_CHECKERS: dict[PlacementGate, PayoutGateCheckerFn] = {}
_PAYOUT_TRANSITION_GATES: dict[tuple[PayoutStatus, PayoutStatus], frozenset[PlacementGate]] = {}
_PAYOUT_CREATE_GATES: dict[str, frozenset[PlacementGate]] = {}


class PayoutComplianceService:
    """Coordinator for payout-side gate evaluation.

    5b.7b SKELETON — empty registries, full dispatcher logic. Phase 5
    populates registries with concrete payout-side gate-checker bodies and
    transition/create resolution tables.

    Architecture: sibling to ``LegalComplianceService``. Naming convention:
    methods named ``*_payout_*`` return ONLY payout-specific gates
    (G13-G18). User-role gates (G04+G05+G06) remain ``LegalComplianceService``
    territory; callers invoke both services for full payout-create gate
    evaluation (see module docstring).

    S-48 contract: methods do NOT manage transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def gates_for_payout_transition(
        self,
        from_status: PayoutStatus,
        to_status: PayoutStatus,
    ) -> list[PlacementGate]:
        """Return the gates required for this payout state transition.

        Resolution table is empty in 5b.7b — Phase 5 fills with
        ``(pending → processing)`` and ``(processing → paid)`` entries
        (and any other transitions Phase 5 introduces).

        Raises:
            ValueError: if ``(from_status, to_status)`` is not in the
                resolution table. Until Phase 5 fills the table, every
                call raises.
        """
        key = (from_status, to_status)
        if key not in _PAYOUT_TRANSITION_GATES:
            raise ValueError(
                f"Payout transition {from_status.value} -> {to_status.value} "
                f"is not in the gates resolution table (Phase 5 will populate)."
            )
        return list(_PAYOUT_TRANSITION_GATES[key])

    def gates_for_payout_create(
        self,
        role: Literal["owner"],
    ) -> list[PlacementGate]:
        """Return the payout-specific gates required for payout creation.

        Phase 5 fills with payout-side gates (e.g. G13/G14 placement-
        completed precondition; G17/G18 conditional on legal_status).

        User-role gates (G04+G05+G06) are NOT included here — caller
        invokes ``LegalComplianceService.check_gates_for_user_role(user,
        "owner")`` in addition (see module docstring partition).

        Raises:
            ValueError: if ``role`` is not in the resolution table. Until
                Phase 5 fills the table, every call raises.
        """
        if role not in _PAYOUT_CREATE_GATES:
            raise ValueError(
                f"Payout-create role {role!r} is not in the gates resolution "
                f"table (Phase 5 will populate)."
            )
        return list(_PAYOUT_CREATE_GATES[role])

    async def check_gate(
        self,
        gate: PlacementGate,
        payout: PayoutRequest,
    ) -> GateResult:
        """Dispatch to the payout-side gate-checker function.

        Phase 5 populates ``_PAYOUT_GATE_CHECKERS``. Until then, every call
        raises ``NotImplementedError``.

        Raises:
            NotImplementedError: if ``gate`` has no entry in
                ``_PAYOUT_GATE_CHECKERS``.
        """
        checker = _PAYOUT_GATE_CHECKERS.get(gate)
        if checker is None:
            raise NotImplementedError(
                f"No payout gate-checker registered for {gate.name} (Phase 5 will register)."
            )
        return await checker(self._session, payout)

    async def check_gates_for_payout_transition(
        self,
        payout: PayoutRequest,
        to_status: PayoutStatus,
    ) -> list[GateResult]:
        """Evaluate all gates required for the proposed payout transition.

        Resolves required gates via ``gates_for_payout_transition``, then
        dispatches each through ``check_gate``. Returns the list in
        evaluation order.
        """
        required = self.gates_for_payout_transition(payout.status, to_status)
        results: list[GateResult] = []
        for gate in required:
            results.append(await self.check_gate(gate, payout))
        return results

    async def check_gates_for_payout_create(
        self,
        user: User,
        role: Literal["owner"],
    ) -> list[GateResult]:
        """Evaluate all payout-specific gates required for payout creation.

        Phase 5 territory. Skeleton commits only to the method signature.
        The dispatch path is intentionally undecided: Phase 5 may either
        construct a draft ``PayoutRequest`` and reuse ``check_gate`` (the
        ``PayoutRequest``-keyed dispatcher), or introduce a parallel
        user-keyed checker registry alongside ``_PAYOUT_GATE_CHECKERS``.

        Raises:
            NotImplementedError: skeleton; Phase 5 fills.
        """
        raise NotImplementedError(
            "PayoutComplianceService.check_gates_for_payout_create lands in Phase 5"
        )
