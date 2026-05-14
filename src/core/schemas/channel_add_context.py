"""Channel-add gate context для BL-107 channel-context gate framework.

Used by ``LegalComplianceService.check_gates_for_channel_add()`` для
evaluating per-channel gates (currently only G19) at channel-add time.
Phase B.4 channel-add helper populates от ``bot.get_chat()`` +
``bot.get_chat_administrators()`` results. В Phase B.2 (gate framework
setup) verification fields default False/None — Phase B.4 wires actual
values после Trustchannelbot admin check.

Frozen dataclass deliberately:

* Pass-by-value semantics — context carries snapshot of channel state
  at gate-evaluation time; mutation post-evaluation would race against
  parallel gate dispatches.
* Cheap construction — channel-add hot path, no Pydantic validation cost.
* Mirror ``GateResult`` (sibling) — same package, same dataclass shape.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelAddContext:
    """Per-channel context payload для channel-add gate framework (BL-107)."""

    telegram_id: int
    username: str
    member_count: int
    is_test: bool = False
    description: str | None = None
    # Verification state — populated by Phase B.4 channel-add helper
    # после Trustchannelbot admin check + DB lookup для re-adds.
    is_blogger_registry_verified: bool = False
    blogger_registry_application_number: str | None = None
