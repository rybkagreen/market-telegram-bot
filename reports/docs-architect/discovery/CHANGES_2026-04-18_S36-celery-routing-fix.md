# CHANGES — S-36 Celery Task Routing Implementation

**Date:** 2026-04-18 | **Sprint:** S-36 | **Mode:** implementation

## Affected files

| File | Action | Notes |
|------|--------|-------|
| `src/tasks/celery_app.py` | Modified | Queue constants, full task_routes, 7 new Beat entries, 3 new includes |
| `src/tasks/celery_config.py` | **Deleted** | Dead module; BEAT_SCHEDULE/TASK_ROUTES were never imported |
| `src/tasks/placement_tasks.py` | Modified | Import QUEUE_WORKER_CRITICAL from celery_app instead of celery_config |
| `src/tasks/dispute_tasks.py` | Modified | Added `queue='worker_critical'` to decorator |
| `src/tasks/gamification_tasks.py` | Modified | Added `queue='gamification'` to 4 decorators |
| `src/tasks/badge_tasks.py` | Modified | Added `queue='badges'` to 7 decorators |
| `src/tasks/integrity_tasks.py` | Modified | Added `queue='cleanup'` to decorator |
| `src/tasks/billing_tasks.py` | Modified | Removed ignored `notification_type` kwarg from 2 `notify_user.delay()` calls |
| `tests/tasks/test_celery_routing.py` | Created | 20 regression tests for routing, beat schedule, queue discipline |
| `CLAUDE.md` | Modified | Added Celery Infrastructure Map section |
| `QWEN.md` | Modified | Replaced stale Celery task docs with current infrastructure map |

## Business logic impact

### Fixed: 6 placement SLA tasks now run automatically
Beat schedule previously had 11 entries. After S-36: 18 entries. Added:
- `placement:check_owner_response_sla` — every 5 min → owner acceptance SLA enforcement
- `placement:check_payment_sla` — every 5 min → payment timeout enforcement
- `placement:check_counter_offer_sla` — every 5 min → counter-offer SLA enforcement
- `placement:check_escrow_sla` — every 5 min → escrow timeout detection
- `placement:check_escrow_stuck` — every 30 min → stuck escrow funds detection
- `placement:check_published_posts_health` — every 6h:30m → published post health check

### Fixed: integrity check now runs automatically
- `integrity:check_data_integrity` — every 6h → DB invariant checks, admin alerts

### Fixed: 13 tasks now reach correct workers
Previously routing to default `celery` queue (no listener):
- `dispute:resolve_financial` → now `worker_critical`
- `gamification:update_streaks_daily`, `send_weekly_digest`, `check_seasonal_events`, `award_daily_login_bonus` → now `gamification` (worker_game)
- `badges:check_user_achievements`, `daily_badge_check`, `monthly_top_advertisers`, `notify_badge_earned`, `trigger_after_campaign_launch`, `trigger_after_campaign_complete`, `trigger_after_streak_update` → now `badges` (worker_game)
- `integrity:check_data_integrity` → now `cleanup` (worker_background)

### Fixed: badges route to correct queue
Previously `badges:*` was routed to `gamification` queue (incorrect). Now routes to `badges` queue. Both are consumed by `worker_game` but this aligns with the dedicated queue architecture.

### Fixed: dead `publication.*` task_routes entry removed
Route to non-existent `critical` queue (note: queue is named `worker_critical`, not `critical`) removed.

### Fixed: billing_tasks no longer sends unknown kwargs
Two `notify_user.delay()` calls in `billing_tasks.py` were passing `notification_type=` kwarg that `notify_user` silently ignores. Removed.

## New/changed API / FSM / DB contracts

None — Celery infrastructure changes only, no API/FSM/DB contract changes.

## Known issues tracked for S-37

- `mailing:check_low_balance` and `mailing:notify_user` in `notification_tasks.py` use colon-prefix names (`mailing:*`) but task_routes only has `mailing.*` (dot-prefix) pattern. These two tasks still land on default queue. Fix deferred to S-37 (notification_tasks.py refactor scope).

## Verification

- `pytest tests/tasks/test_celery_routing.py` — 20/20 passed
- `ruff check src/tasks/` — 0 errors
- Beat entries: 18 (was 11)
- Task routes: 13 complete prefixes (was 4, with dead route)
- `celery_config` imports: 0

---

🔍 Verified against: HEAD | 📅 Updated: 2026-04-18T00:00:00Z
