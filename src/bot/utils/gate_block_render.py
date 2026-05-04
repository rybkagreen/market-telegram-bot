"""Bot-side rendering for TransitionBlockedError payloads.

Phase 3c (2026-05-04): caller-side classification of gate-block reasons.
PHASE_N_PENDING markers (reason_code in {"phase4_pending", "phase5_pending"})
are expected until the corresponding phase ships the real gate body —
render as "временно недоступно" with no remediation list. Real-fail
blockers (other reason_codes) carry actionable remediation and render the
full list.

Used by bot/handlers/owner/arbitration.py and
bot/handlers/advertiser/campaigns.py at the G07-affected sites.
"""

from typing import Any

PHASE_N_PENDING_CODES: frozenset[str] = frozenset({"phase4_pending", "phase5_pending"})


def is_marker_only(blockers: list[dict[str, Any]]) -> bool:
    """Return True iff every blocker is a PHASE_N_PENDING marker."""
    if not blockers:
        return False
    return all(b.get("reason_code") in PHASE_N_PENDING_CODES for b in blockers)


def render_owner_message(blockers: list[dict[str, Any]]) -> str:
    """Render TransitionBlockedError payload for owner-side accept handler."""
    if is_marker_only(blockers):
        return (
            "⏳ Подтверждение временно недоступно — идёт настройка системы.\n"
            "Попробуйте позже или обратитесь к администратору."
        )
    lines = ["❌ Подтверждение размещения недоступно — требуется:"]
    remediation_url: str | None = None
    for b in blockers:
        lines.append(f"• {b.get('gate', '?')}")
        if remediation_url is None and b.get("remediation_url"):
            remediation_url = b["remediation_url"]
    if remediation_url:
        lines.append("")
        lines.append(remediation_url)
    return "\n".join(lines)


def render_advertiser_message(blockers: list[dict[str, Any]]) -> str:
    """Render TransitionBlockedError payload for advertiser-side pay-now handler."""
    if is_marker_only(blockers):
        return (
            "⏳ Принятие условий временно недоступно — идёт настройка системы.\n"
            "Попробуйте позже или обратитесь к администратору."
        )
    lines = ["❌ Принять условия нельзя — требуется:"]
    remediation_url: str | None = None
    for b in blockers:
        lines.append(f"• {b.get('gate', '?')}")
        if remediation_url is None and b.get("remediation_url"):
            remediation_url = b["remediation_url"]
    if remediation_url:
        lines.append("")
        lines.append(remediation_url)
    return "\n".join(lines)
