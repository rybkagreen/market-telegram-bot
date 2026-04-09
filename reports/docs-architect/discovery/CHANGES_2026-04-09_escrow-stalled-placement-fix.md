# CHANGES_2026-04-09_escrow-stalled-placement-fix

**Date:** 2026-04-09T18:00:00Z
**Author:** Backend Core Agent
**Type:** Bug Fix + Infrastructure Consolidation

## Summary

Fixed the root cause of stalled ESCROW placements: `camp_pay_balance` handler did NOT schedule the Celery publication task after payment. Placements sat in `escrow` status indefinitely without ever being published.

## Root Cause Analysis

The `camp_pay_balance` handler in `src/bot/handlers/placement/placement.py` called `billing.freeze_escrow()` and set `req.status = PlacementStatus.escrow`, then committed — but never called `schedule_placement_publication.delay()`. The `PlacementRequestService._schedule_publication_task()` method existed and was correct, but the direct `camp_pay_balance` handler bypassed it entirely.

## Changes Made

### Fix 1 (CRITICAL): Schedule publication after payment in `camp_pay_balance`

**File:** `src/bot/handlers/placement/placement.py` (lines ~448-456)

- Added `schedule_placement_publication.delay(req.id, scheduled_at.isoformat())` after `await session.commit()`
- Uses `req.final_schedule` if set, otherwise defaults to `now + 5 minutes`
- Updated confirmation message to show scheduled publication time
- Added `datetime` import at module level

**Business Impact:** Placements now actually get published after payment. This is the primary fix for the stalled escrow issue.

### Fix 2 (HIGH): Add `check_escrow_sla` Celery Beat task

**File:** `src/tasks/placement_tasks.py` (new section T5b, lines ~760-870)

- New task `placement:check_escrow_sla` scans for placements in `escrow` status where:
  - `message_id IS NULL` (not yet published)
  - `final_schedule IS NOT NULL` and `final_schedule <= now` (scheduled time has passed)
- For each stalled placement:
  - Sets status to `failed` with error in `meta_json`
  - Refunds advertiser's `balance_rub`
  - Creates `Transaction(type=refund)` record
  - Notifies both advertiser and channel owner
- Added to Celery Beat schedule in `src/tasks/celery_config.py` (runs every 5 minutes)

**Business Impact:** Safety net — if publication scheduling ever fails again, stalled placements are automatically detected and refunded within 5 minutes.

### Fix 3 (MEDIUM): Consolidate `publication_tasks.py` into `placement_tasks.py`

**Files:**
- `src/tasks/placement_tasks.py` — added T7 (delete_published_post) and T8 (check_scheduled_deletions)
- `src/tasks/publication_tasks.py` — **DELETED**
- `src/tasks/celery_config.py` — updated Beat schedule to use `placement:` prefix
- `src/tasks/celery_app.py` — updated legacy Beat registration

- Moved `delete_published_post`, `check_scheduled_deletions` from `publication_tasks.py` to `placement_tasks.py`
- Renamed task prefix from `publication:` to `placement:` for consistency
- `publish_placement` was already in `placement_tasks.py` (more sophisticated version with dedup)
- No external imports of `publication_tasks.py` existed in the codebase (only docs referenced it)

**Business Impact:** Single source of truth for all placement-related Celery tasks. No functional change.

### Fix 4 (MEDIUM): Handle NULL `final_schedule` in `schedule_placement_publication`

**File:** `src/tasks/placement_tasks.py` (T6 section)

- Changed `scheduled_at: str` parameter to `scheduled_iso: str | None = None`
- If `None`, defaults to `now + 5 minutes` instead of crashing
- Updated docstring to reflect new behavior

**Business Impact:** Prevents crashes when placement has no scheduled time set.

### Fix 5 (HIGH): Deletion countdown from ACTUAL publication time

**Status:** Already correctly implemented. No changes needed.

The `publication_service.py:publish_placement()` already sets `scheduled_delete_at = datetime.now(UTC) + timedelta(seconds=duration_seconds)` at the moment of publication (line ~279). The timer counts from actual publication, not campaign creation or payment.

### Fix 6 (HIGH): Add notifications for both parties

**File:** `src/bot/handlers/placement/placement.py` (lines ~486-530)

- After payment confirmation, channel owner now receives a notification with:
  - Payment amount in escrow
  - Scheduled publication time
  - Publication format
  - Channel name
  - Placement ID
  - Link to view placement details
- Advertiser already receives confirmation via the edited callback message
- Publication success/failure notifications already exist in `_publish_placement_async`
- SLA violation notifications added in `_check_escrow_sla_async`

**Business Impact:** Both parties are informed at every stage of the placement lifecycle.

## Files Modified

| File | Lines Changed | Type |
|------|--------------|------|
| `src/bot/handlers/placement/placement.py` | +50, -10 | Handler fix + notifications |
| `src/tasks/placement_tasks.py` | +200, -5 | New tasks + consolidation |
| `src/tasks/celery_config.py` | +10 | Beat schedule updates |
| `src/tasks/celery_app.py` | +4, -4 | Beat registration update |

## Files Deleted

| File | Reason |
|------|--------|
| `src/tasks/publication_tasks.py` | Consolidated into `placement_tasks.py` |

## API/FSM/DB Contract Changes

- **No DB schema changes** — all logic uses existing fields
- **No FSM state changes** — existing `PlacementStates` unchanged
- **No API endpoint changes** — internal handler fix only
- **Celery task name changes:** `publication:delete_published_post` → `placement:delete_published_post`, `publication:check_scheduled_deletions` → `placement:check_scheduled_deletions`

## Celery Beat Schedule Additions

```python
"placement-check-escrow-sla": {
    "task": "placement:check_escrow_sla",
    "schedule": crontab(minute="*/5"),
    "options": {"queue": QUEUE_WORKER_CRITICAL, "expires": 60},
},
"placement-check-scheduled-deletions": {
    "task": "placement:check_scheduled_deletions",
    "schedule": crontab(minute="*/5"),
    "options": {"queue": QUEUE_WORKER_CRITICAL, "expires": 60},
},
```

## Rollback Instructions

1. Revert all 4 modified files to previous commit
2. Restore `src/tasks/publication_tasks.py` from previous commit
3. Restart Celery workers to unregister `placement:check_escrow_sla` task

## Testing Notes

- Ruff: 0 errors on all modified files
- MyPy: 0 new errors in modified files (pre-existing errors in badge_service.py, legal_profile.py unchanged)
- No existing tests reference `publication_tasks.py` (confirmed via grep)

🔍 Verified against: HEAD | 📅 Updated: 2026-04-09T18:00:00Z
