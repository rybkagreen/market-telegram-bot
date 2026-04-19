# S-40 Tech Debt Cleanup — Changes Report

## Affected Files

### `src/tasks/placement_tasks.py` (D-10 — P0 async Redis fix)
- Removed `from redis import Redis as RedisSync` import (line 19)
- Removed `redis_sync_client` module-level variable
- Renamed `_check_dedup` → `_check_dedup_async`, changed to `async def`
- Replaced `redis_sync_client.exists(...)` → `await redis_client.exists(...)`
- Replaced `redis_sync_client.setex(...)` → `await redis_client.setex(...)`
- Updated all 6 call sites: `_check_dedup(...)` → `await _check_dedup_async(...)`
  - Lines (approx): `_check_owner_response_sla_async`, `_check_payment_sla_async`,
    `_check_counter_offer_sla_async`, `_publish_placement_async`,
    `_check_escrow_sla_async`, `_check_scheduled_deletions_async`

### `src/tasks/billing_tasks.py` (D-06 — dead task removal)
- Removed `@celery_app.task(name="billing:check_pending_invoices", ...)` + function body
- Removed `async def _check_pending_invoices()` helper
- Trailing newline fixed by ruff

### `reports/monitoring/payloads/.gitkeep` (D-20 — empty dir)
- New empty file to track `payloads/` directory in git

### `CLAUDE.md` (pre-launch documentation)
- Added `## Pre-Launch Blockers` section documenting:
  - ORD integration as legal blocker (ФЗ-38 compliance)
  - FNS validation as optional hardening

### `CHANGELOG.md`
- Added S-40 entry under `[Unreleased]`

## Business Logic Impact

**D-10 (P0)**: Each placement SLA periodic task (runs every 5 min via Beat) previously
called sync Redis inside an `asyncio.run()` context. Sync Redis blocks the thread/event
loop. With concurrency=2, this could stall the worker on every beat tick. Fix eliminates
the blocking entirely — all Redis I/O is now non-blocking async.

**D-06**: Removed dead no-op task that was still registered with Celery. No functional
change; reduces worker memory footprint and registered-task noise.

## New/Changed API/FSM/DB Contracts

None — these are internal task infrastructure changes only.

## Verification

- `grep 'redis_sync_client\|RedisSync' src/tasks/placement_tasks.py` → 0 results
- `grep 'check_pending_invoices' src/tasks/billing_tasks.py` → 0 results
- `inspect.iscoroutinefunction(_check_dedup_async)` → `True`
- `worker_critical` starts without ImportError or AttributeError
- `celery inspect registered -d critical@...` → `billing:check_pending_invoices` not found in critical worker

🔍 Verified against: 4d4ab78 | 📅 Updated: 2026-04-19T10:10:00Z
