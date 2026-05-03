"""GateResult — outcome of a single legal-compliance gate check.

Two shapes deliberately:

* ``GateResult`` (dataclass) — service-layer return type. Cheap to
  construct, no Pydantic validation cost on the hot path.

* ``GateResultResponse`` (Pydantic) — API-facing shape, used by the
  Phase 3d ``GET /api/placements/{id}/gates`` endpoint and by the
  exception payload of ``TransitionBlockedError`` when surfaced to the
  client. Field set is identical to the dataclass; the wrapper exists
  only so the contract-drift snapshot (S-47) catches accidental
  shape changes.

Population conventions
----------------------

* ``passed=True`` ⇒ ``blocker`` is irrelevant; checker should still
  emit a stable ``reason_code`` (e.g. ``"ok"``) so the UI can label
  the gate without branching.

* ``blocker=True`` and ``passed=False`` ⇒ Phase 3c transition service
  raises ``TransitionBlockedError``; channel-add hook raises
  ``ChannelAddDeclinedError``.

* Phase-N pending markers (``blocker=True``, ``passed=False``,
  ``reason_code="phaseN_pending"``) advertise that the gate is
  recognised but its evaluator ships in a later phase: G07/G15/G16 →
  ``phase4_pending``; G17/G18 → ``phase5_pending``.

* ``remediation_url`` should resolve to a Mini App / Web Portal screen
  capable of resolving the failure (e.g. legal-profile editor for
  G01). Null when the failure cannot be self-resolved by the user.
"""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.core.enums.placement_gate import PlacementGate


@dataclass
class GateResult:
    gate: PlacementGate
    passed: bool
    blocker: bool
    reason_code: str
    remediation_url: str | None = None
    remediation_data: dict[str, Any] | None = None


class GateResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gate: PlacementGate
    passed: bool
    blocker: bool
    reason_code: str
    remediation_url: str | None = None
    remediation_data: dict[str, Any] | None = None
