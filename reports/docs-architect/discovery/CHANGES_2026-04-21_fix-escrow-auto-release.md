# CHANGES_2026-04-21 — fix: escrow auto-release + post-deletion pipeline (Track A)

## Context

Production dev-stand observation: placement #1 stuck in `published` status with
`scheduled_delete_at` 24 h in the past; escrow never released, post still visible
in the channel. Worker-critical logs showed 18× `InvalidRequestError('A
transaction is already begun on this Session.')` and `RuntimeError('Event loop
is closed')` over multiple Beat cycles. Redis-dedup's 1 h fallback TTL held the
placement in an "already scheduled" state between each failed retry.

Three coupled root causes:

1. `BillingService.release_escrow/refund_escrow/freeze_escrow/process_topup_webhook`
   did `async with session.begin()` on a session already in autobegin transaction
   — guaranteed failure once any prior SELECT ran.
2. Singleton `aiogram.Bot` in `_bot_factory.get_bot()` kept an aiohttp session
   bound to the first `asyncio.run()` loop. The second invocation in the same
   prefork worker exploded on any Bot HTTP call.
3. `release_escrow` idempotency was gated by `MailingLog.status == paid` but
   `MailingLog` is **never** created for placement-scoped events — the guard
   always passed, leaving `release_escrow` non-idempotent and primed for
   double-payout on any successful retry.

Track A is the surgical fix — restore function, close the financial-loss window,
add two recovery lanes. Track B (future) will replace Redis-dedup with a
`PlacementStatus.deleting` status-machine lock and consolidate the two-hop
deletion into a single Beat task (see `/root/.claude/plans/lexical-swinging-pony.md`).

## Affected files

### Code
- `src/core/services/billing_service.py`
  - `release_escrow`, `refund_escrow`, `freeze_escrow`, `process_topup_webhook`:
    removed `async with session.begin()`. Caller owns the transaction.
  - `release_escrow`: replaced MailingLog-based idempotency with
    `Transaction.idempotency_key`. Keys: `escrow_release:placement={id}:owner`,
    `escrow_release:placement={id}:platform`. Wraps flush in `try/except
    IntegrityError` for race-past-exists.
  - `refund_escrow`: keys `refund:placement={id}:scenario={scenario}:{advertiser|owner}`.
  - `freeze_escrow`: key `escrow_freeze:placement={id}`.
  - Every financial `Transaction` now carries `placement_request_id` +
    `idempotency_key`.

- `src/core/services/publication_service.py`
  - `delete_published_post` gained a status guard: `completed` → no-op;
    `!= published` → warning + return. Runs before any Telegram/billing call.

- `src/tasks/_bot_factory.py`
  - Added `ephemeral_bot()` async context manager. Creates and closes a Bot
    inside the caller's event loop. Documented boundary with `get_bot()`:
    singleton only for long-lived loops (`bot/main.py`); `ephemeral_bot()` for
    any `asyncio.run(...)` Celery task body.

- `src/tasks/placement_tasks.py`
  - `_delete_published_post_async`, `_publish_placement_async`,
    `_check_published_posts_health_async`, `_check_escrow_stuck_async`,
    `_notify_user`: switched to `ephemeral_bot()`.
  - `DEDUP_TTL['delete_published_post'] = 180`. Task handler calls
    `_check_dedup_async("delete_published_post", placement_id)` before the
    asyncio.run(…) body to block double-dispatch on two pool workers.
  - `check_scheduled_deletions`: removed 60 s countdown (redundant and
    created the very race it was trying to avoid).
  - `check_escrow_stuck`: added **group C** — `status=published` +
    `scheduled_delete_at < now - 1 h` + `message_id` set → re-dispatch
    `delete_published_post` + admin alert. Closes the recovery loop for any
    future deletion-pipeline failure.
  - `check_published_posts_health`: dropped the `scheduled_delete_at > now`
    filter so the monitor surfaces already-expired placements it was missing.

- `src/db/repositories/platform_account_repo.py`
  - `get_for_update`: switched from `scalar_one()` to
    `scalar_one_or_none()` and creates the singleton row if missing (matching
    `get_singleton`). Surfaced while verifying the release flow on a fresh DB.

- `src/db/models/transaction.py`
  - New column `Transaction.idempotency_key: str | None` with `unique=True,
    index=True`.

- `src/db/migrations/versions/0001_initial_schema.py`
  - Added `idempotency_key String(128)` column + unique `ix_transactions_idempotency_key`
    index to `transactions`. Pre-production schema edit per CLAUDE.md §
    Migration Strategy.

### Tests
- `tests/test_billing_service_idempotency.py` — fully rewritten. 25 tests, all
  green. Covers caller-controlled transaction contract, key-format invariants,
  EXISTS short-circuit behaviour via mocked AsyncSession, IntegrityError catch,
  placement linkage, status guard, `ephemeral_bot` presence, `DEDUP_TTL` entry,
  group C branch.

## Business logic impact

**Before fix.** Each successful placement reaching `published` was financially
frozen until manual intervention. `advertiser.balance_rub` debited; `owner.earned_rub`
never credited; platform commission never recorded; `PlatformAccount.escrow_reserved`
never decremented. ФЗ-38 exposure from un-removed posts.

**After fix.**
1. Beat → `check_scheduled_deletions` finds expired placements, dispatches
   `delete_published_post` inline (no countdown).
2. Dedup Redis key (TTL 180 s) prevents double dispatch on two pool workers.
3. Task opens an ephemeral Bot, status guard short-circuits if already
   completed, otherwise unpins/deletes the Telegram message, calls
   `release_escrow` (idempotent via `idempotency_key` UNIQUE + EXISTS early
   exit), flips status to `completed`, auto-generates Act.
4. If anything fails, Celery retries up to 5× with exponential backoff. If
   that still fails, `check_escrow_stuck` group C picks it up within the next
   30 min and re-dispatches + alerts admins.

## New / changed contracts

### API/DB contract changes

- `Transaction.idempotency_key` — new `String(128)` nullable+UNIQUE column.
  Callers that construct `Transaction` for escrow_freeze / escrow_release /
  refund / commission **must** supply the key. Other `Transaction` inserts
  may leave it NULL (Postgres UNIQUE ignores NULLs).
- `BillingService` public methods (`release_escrow`, `refund_escrow`,
  `freeze_escrow`, `process_topup_webhook`) **no longer** open their own
  transaction. Callers that used to rely on internal auto-commit must now
  either receive session from FastAPI/bot middleware with auto-commit, or
  call `await session.commit()` themselves. Affected callers (verified):
  * `publication_service.delete_published_post` — commits via
    `_delete_published_post_async`.
  * `placement_request_service.{advertiser_cancel,auto_expire,…}` — session
    from FastAPI `get_db_session` auto-commits.
  * `bot/handlers/{admin,placement}/…` — already call `await session.commit()`.
  * `api/routers/{disputes,billing}.py` — already commit.
  * `tasks/dispute_tasks.py` — already commits.
  * `tasks/placement_tasks.py` — three `async_session_factory() as refund_session`
    blocks gained explicit `await refund_session.commit()`.

### FSM / Celery

- `DEDUP_TTL['delete_published_post'] = 180`. Short TTL on purpose — covers
  the Celery `max_retries=5, retry_backoff_max=600` window without locking a
  placement for an hour on a mid-run crash.
- `check_escrow_stuck.stats['group_c_dispatched']` — new field.

## Verification on dev

Reproducer (worked end-to-end after A.6):

```
# Placement #1 was at status=published, scheduled_delete_at=2026-04-20 11:00
docker compose exec redis redis-cli DEL \
  "placement_task:check_scheduled_deletions:1" \
  "placement_task:delete_published_post:1"
docker compose exec worker_critical celery -A src.tasks.celery_app call \
  placement:check_scheduled_deletions
```

Observed in worker_critical logs (no retries, no errors):
```
Scheduled deletions check completed: {'total_found': 1, 'scheduled': 1, 'errors': 0}
Deleting placement post 1
Escrow released: 4250.00 ₽ to owner 1 (earned_rub), 750.00 ₽ commission for placement 1
Placement 1 deleted successfully and escrow released
```

DB state:
```
placement_requests.id=1: status='completed', deleted_at=2026-04-21 13:59:20
transactions where idempotency_key like 'escrow_release:placement=1%':
  escrow_release:placement=1:owner    — 4250.00 ₽ (85 % to owner)
  escrow_release:placement=1:platform —  750.00 ₽ (15 % commission)
users.id=1 earned_rub: 0.00 → 4250.00
platform_account.profit_accumulated: 0.00 → 750.00
```

Idempotency verified by a second dispatch of `delete_published_post` on the
same placement — handler logged `Placement 1 already completed, skipping
deletion`; transactions count unchanged (2), `earned_rub` unchanged (4250.00).

## Follow-up (Track B, separate sprint)

Planned in `/root/.claude/plans/lexical-swinging-pony.md` § Track B. Not in
this commit stack.

- `PlacementStatus.deleting` intermediate status as a BD-level lock, replacing
  `_check_dedup_async` for the deletion path.
- Inline `check_scheduled_deletions` processing — remove the two-hop
  `apply_async` dispatch.
- Unify transactional contract across all services (not just billing).
- Prometheus/Grafana metrics: `placement_stuck_seconds`,
  `placement_deletion_failure_total{reason}`.

🔍 Verified against: 36710a6 (fix(repo): auto-create PlatformAccount singleton in get_for_update)
📅 Updated: 2026-04-21T14:05:00Z
