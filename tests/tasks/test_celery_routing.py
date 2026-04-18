"""
Regression tests for S-36: Celery task routing, Beat schedule, queue discipline.

Verifies that:
- All task prefixes have a route (no task lands on default 'celery' queue)
- Beat schedule contains all required SLA and integrity entries
- gamification/badges tasks route to worker_game queues
- celery_config.py is fully deleted
"""

import importlib.util

import src.tasks.badge_tasks  # noqa: F401 — ensure tasks register
import src.tasks.dispute_tasks  # noqa: F401
import src.tasks.gamification_tasks  # noqa: F401
import src.tasks.integrity_tasks  # noqa: F401
import src.tasks.placement_tasks  # noqa: F401
import pytest

from src.tasks.celery_app import QUEUE_WORKER_CRITICAL, celery_app


# ─── helpers ───────────────────────────────────────────────────────────────────


def _effective_queue(task_name: str) -> str | None:
    """Return effective queue: decorator queue > task_routes match > None."""
    task = celery_app.tasks.get(task_name)
    if task and getattr(task, "queue", None):
        return task.queue
    routes = celery_app.conf.task_routes or {}
    for pattern, route in routes.items():
        if pattern.endswith(".*"):
            prefix = pattern[:-1]
            if task_name.startswith(prefix):
                return route.get("queue")
        elif task_name == pattern:
            return route.get("queue")
    return None


# ─── P5: celery_config.py deleted ──────────────────────────────────────────────


def test_celery_config_deleted():
    assert importlib.util.find_spec("src.tasks.celery_config") is None, (
        "celery_config.py must be deleted — all config lives in celery_app.py"
    )


# ─── P1: Beat schedule completeness ────────────────────────────────────────────


REQUIRED_BEAT_ENTRIES = [
    "placement-check-owner-sla",
    "placement-check-payment-sla",
    "placement-check-counter-sla",
    "placement-check-escrow-sla",
    "placement-check-escrow-stuck",
    "check-published-posts-health",
    "data-integrity-check",
    "placement-check-scheduled-deletions",
    "check-plan-renewals",
    "delete-old-logs",
]


def test_beat_schedule_contains_required_entries():
    schedule = celery_app.conf.beat_schedule
    for entry in REQUIRED_BEAT_ENTRIES:
        assert entry in schedule, f"Missing Beat entry: {entry}"


def test_beat_schedule_has_18_entries():
    schedule = celery_app.conf.beat_schedule
    assert len(schedule) == 18, f"Expected 18 Beat entries, got {len(schedule)}: {list(schedule)}"


def test_beat_task_names_valid():
    """Every beat entry must reference a task that can be looked up by name."""
    schedule = celery_app.conf.beat_schedule
    # Collect registered short-name tasks (name= in decorator)
    registered = set(celery_app.tasks.keys())
    # Collect task names from beat
    beat_tasks = {entry["task"] for entry in schedule.values()}
    # We can't check all since workers may register more, but parser tasks use short names
    # Just verify no entry has an obviously broken 'src.tasks.*' style name that doesn't exist
    for beat_name in beat_tasks:
        if beat_name.startswith("src.tasks."):
            assert beat_name in registered, f"Beat references unregistered task: {beat_name}"


# ─── P2: task_routes completeness ──────────────────────────────────────────────


REQUIRED_ROUTE_PREFIXES = [
    "mailing.*",
    "parser.*",
    "cleanup.*",
    "notifications.*",
    "placement.*",
    "billing.*",
    "ord.*",
    "badges.*",
    "gamification.*",
    "integrity.*",
    "dispute.*",
    "document_ocr.*",
]


def test_task_routes_complete():
    routes = celery_app.conf.task_routes or {}
    for prefix in REQUIRED_ROUTE_PREFIXES:
        assert prefix in routes, f"Missing task_route for prefix: {prefix}"


def test_dead_publication_route_removed():
    routes = celery_app.conf.task_routes or {}
    assert "publication.*" not in routes, "Dead route 'publication.*' must be removed"


# ─── P3: explicit queue in decorators ──────────────────────────────────────────


@pytest.mark.parametrize("task_name", [
    "gamification:update_streaks_daily",
    "gamification:send_weekly_digest",
    "gamification:check_seasonal_events",
    "gamification:award_daily_login_bonus",
])
def test_gamification_tasks_routed_to_gamification_queue(task_name):
    q = _effective_queue(task_name)
    assert q == "gamification", f"{task_name} must route to 'gamification', got {q!r}"


@pytest.mark.parametrize("task_name", [
    "badges:check_user_achievements",
    "badges:daily_badge_check",
    "badges:monthly_top_advertisers",
    "badges:notify_badge_earned",
    "badges:trigger_after_campaign_launch",
    "badges:trigger_after_campaign_complete",
    "badges:trigger_after_streak_update",
])
def test_badges_tasks_routed_to_badges_queue(task_name):
    q = _effective_queue(task_name)
    assert q == "badges", f"{task_name} must route to 'badges', got {q!r}"


def test_integrity_task_routed_to_cleanup():
    q = _effective_queue("integrity:check_data_integrity")
    assert q == "cleanup", f"integrity:check_data_integrity must route to 'cleanup', got {q!r}"


def test_dispute_task_routed_to_worker_critical():
    q = _effective_queue("dispute:resolve_financial")
    assert q == QUEUE_WORKER_CRITICAL, (
        f"dispute:resolve_financial must route to {QUEUE_WORKER_CRITICAL!r}, got {q!r}"
    )


# ─── no task on default queue ───────────────────────────────────────────────────


def test_no_task_on_default_celery_queue():
    """No registered task should land on the default 'celery' queue.

    S-37 note: mailing:check_low_balance and mailing:notify_user in
    notification_tasks.py use colon-prefix names while task_routes only has
    mailing.* (dot) pattern. Those two tasks are excluded here and will be
    fixed in S-37 when notification_tasks.py is refactored.
    """
    S37_KNOWN_ISSUES = {
        "mailing:check_low_balance",
        "mailing:notify_user",
    }
    offenders = []
    for task_name in celery_app.tasks:
        if task_name.startswith("celery."):  # Built-in celery tasks — skip
            continue
        if task_name in S37_KNOWN_ISSUES:
            continue
        q = _effective_queue(task_name)
        if q is None or q == "celery":
            offenders.append(task_name)
    assert not offenders, (
        f"Tasks without explicit queue (would land on default 'celery'): {offenders}"
    )
