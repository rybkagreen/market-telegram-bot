# S-38 Escrow Recovery — Discovery Report

## Affected Files

| File | Change Type |
|------|-------------|
| `src/core/services/billing_service.py` | Modified — idempotency guard added |
| `src/tasks/placement_tasks.py` | Modified — 4 P0 fixes |
| `tests/tasks/test_placement_escrow.py` | New — regression tests |
| `tests/test_billing_service_idempotency.py` | New — idempotency tests |
| `web_portal/src/api/acts.ts` | New — Act API client |
| `web_portal/src/api/admin.ts` | Modified — payout admin endpoints |
| `web_portal/src/hooks/useAdminQueries.ts` | Modified — payout admin hooks |
| `web_portal/src/lib/timeline.types.ts` | New — TimelineEvent types |
| `web_portal/src/lib/types/billing.ts` | New — billing TS types |

## Business Logic Impact

### P0 Fix 1 — `publish_placement` failure no longer freezes escrow
Previously: publish failure left PlacementStatus=escrow with money frozen forever.
Now: on any exception, `BillingService.refund_escrow(..., scenario="after_escrow_before_confirmation")` is called in a **separate session** to avoid nested-transaction conflict; status set to `failed`; advertiser notified.

### P0 Fix 2 — `check_escrow_sla` routes through BillingService
Previously: direct `advertiser.balance_rub += final_price` bypass left `platform_account.escrow_reserved` drifted.
Now: calls `BillingService.refund_escrow` which atomically handles user balance, escrow_reserved, and transaction ledger. Per-item commit with rollback on error.

### P0 Fix 3 — `check_escrow_stuck` now dispatches real actions
Previously: detected stuck placements but neither committed nor dispatched any action (silent no-op).
Now:
- Group A (message_id set): dispatches `delete_published_post.apply_async([placement_id])`
- Group B (no message_id): calls `BillingService.refund_escrow` directly
- Per-item commit; admin alert via bot.send_message to settings.admin_ids
- `meta_json["escrow_stuck_detected"]` set for auditability

### P0 Fix 4 — `delete_published_post` has retry
Previously: any Telegram API error silently failed (no retry), owner never got paid.
Now: `autoretry_for=(Exception,)`, `max_retries=5`, `retry_backoff=True`, `retry_backoff_max=600`. Async helper raises on error — Celery picks up for retry.

### Idempotency Guard — `refund_escrow`
Before calling `session.begin()`, performs SELECT for `Transaction` where:
- `placement_request_id == placement_id`
- `type == TransactionType.refund_full`
- `user_id == advertiser_id`

If found → log and early return. Prevents double-credit on Celery retry.
`Transaction.placement_request_id` now set on the advertiser refund transaction as the FK anchor.

## New/Changed API Contracts

None — all changes are internal service/task logic.

## New/Changed DB Operations

- `refund_escrow` now writes `Transaction.placement_request_id = placement_id` (existing column, previously unset for refund transactions).
- `refund_escrow` gains one additional `SELECT` (idempotency check) before any write.

## FSM / Status Transitions

- `publish_placement` failure path: `escrow → failed` (was: status unchanged)
- `check_escrow_sla` failure path: `escrow → failed` (was: direct balance mutation, no status change guarantee)
- `check_escrow_stuck` group B: `escrow → failed` (was: no action)

## Test Notes

- 36 regression tests — all pass (`pytest tests/tasks/test_placement_escrow.py tests/test_billing_service_idempotency.py`)
- Uses `asyncio.run()` pattern to work around pytest-asyncio 0.26.0 + Python 3.14 `getsourcelines` OSError on mounted volumes.
- Source-inspection tests (no DB) + mock-based integration tests.

## Web Portal Fix

nginx Docker build was failing with 4 TypeScript errors. Root cause: missing type declaration files.
Created:
- `web_portal/src/lib/timeline.types.ts` — `TimelineEvent`, `TimelineEventStatus`
- `web_portal/src/lib/types/billing.ts` — `Payout`, `AdminPayout`, `PayoutListAdminResponse`, etc.
- `web_portal/src/api/acts.ts` — `Act` interface, `getPlacementActs`, `signAct`

Extended `admin.ts` + `useAdminQueries.ts` with payout admin functions.

---
🔍 Verified against: e7a194f | 📅 Updated: 2026-04-18T00:00:00+03:00
