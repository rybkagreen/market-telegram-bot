# CHANGES — 2026-04-24 — Consolidate escrow pipeline + unify Bot factory

Plan: [/root/.claude/plans/optimized-brewing-music.md](../../../../root/.claude/plans/optimized-brewing-music.md)

## Context

Diagnostics of a user-reported "advertiser vs owner status desync" on
placement_request=2 revealed no row-level desync (status was stable
`escrow`), but uncovered three architectural defects that were
silently producing broken state:

1. `BillingService` had two parallel APIs (`freeze_escrow` and
   `freeze_escrow_for_placement`) with incompatible behaviour —
   the service-facing method skipped `platform_account.escrow_reserved`
   update and lacked an `idempotency_key`, so `release_escrow` later
   drove `escrow_reserved` into negative values.
2. Two entry points into `escrow` state:
   - the bot handler `camp_pay_balance` directly set
     `req.status = PlacementStatus.escrow` without recording the
     transaction id, and
   - `PlacementRequestService._freeze_escrow_for_payment`, when
     `is_test=true`, stored `escrow_transaction_id=NULL` and could
     leave `final_price=NULL`, breaking downstream release/refund
     with `TypeError: None × Decimal`.
3. `ephemeral_bot()` in `src/tasks/_bot_factory.py` ignored
   `settings.telegram_proxy`, so every Celery `publish_placement`
   / `delete_published_post` call was guaranteed to
   `TelegramNetworkError` on a proxy-required host.

## Invariants introduced

- **INV-1.** `placement.status = 'escrow'` ⇒
  `escrow_transaction_id IS NOT NULL AND final_price IS NOT NULL`.
  Enforced by DB `CHECK constraint placement_escrow_integrity`.
- **INV-2.** Single escrow-entry code path:
  `PlacementRequestService.process_payment()` →
  `BillingService.freeze_escrow_for_placement()` (unified).
- **INV-3.** `Bot()` is created only in `src/bot/session_factory.py`
  (delegated to by `src/tasks/_bot_factory.py`); SOCKS5/HTTP proxy
  from `settings.telegram_proxy` is applied automatically.

## Affected files

### Backend — source

- `src/bot/session_factory.py` (new) — single `new_bot()` helper that
  applies `AiohttpSession(proxy=...)` when `settings.telegram_proxy`
  is set.
- `src/tasks/_bot_factory.py` — `init_bot()` and `ephemeral_bot()` now
  delegate to `new_bot()`; direct `Bot()` removed.
- `src/bot/main.py` — removed local `_create_bot()`, calls `new_bot()`.
- `src/utils/telegram/sender.py` — `create_sender()` uses `new_bot()`.
- `src/config/settings.py` — added `@field_validator` on
  `telegram_proxy` — rejects URLs without `socks5://`, `socks4://`,
  `http://`, `https://` scheme at boot time instead of at first
  Celery call.
- `src/core/services/billing_service.py`:
  - removed legacy `freeze_escrow(user_id, placement_id, amount)`;
  - rewrote `freeze_escrow_for_placement(...)`:
    - added `is_test: bool = False` param (skips balance check and
      `user.balance_rub` deduction but still creates Transaction +
      updates `platform_account.escrow_reserved`);
    - added EXISTS short-circuit on `idempotency_key`
      (`escrow_freeze:placement={id}`);
    - added `platform_repo.add_to_escrow(session, amount)`
      (previously missing in the service path);
    - wraps `flush()` in `IntegrityError` for race-past-EXISTS.
- `src/core/services/placement_request_service.py`:
  - `_freeze_escrow_for_payment` — single path through billing;
    raises `PlacementValidationError` when both `final_price` and
    `proposed_price` are NULL; now fixes `final_price` before
    `set_escrow` so INV-1 holds at commit.
- `src/bot/handlers/placement/placement.py`:
  - `camp_pay_balance` rewritten as a thin wrapper over
    `PlacementRequestService.process_payment()`; removed direct
    `req.status = PlacementStatus.escrow`, direct
    `billing.freeze_escrow`, and duplicated
    `schedule_placement_publication.delay(...)`;
  - removed unused `datetime`/`UTC` imports.

### Backend — DB

- `src/db/models/placement_request.py` — added
  `CheckConstraint(... placement_escrow_integrity)` in
  `__table_args__`.
- `src/db/migrations/versions/0001_initial_schema.py` — added
  matching `sa.CheckConstraint(... placement_escrow_integrity)`.

### Tests

- `tests/test_billing_service_idempotency.py` — renamed all
  `BillingService.freeze_escrow` references to
  `freeze_escrow_for_placement`; behavioural test swapped to the
  new signature.

### Tooling

- `scripts/check_forbidden_patterns.sh` — added two Python-side guards:
  - aiogram `Bot(token=...)` outside `session_factory.py` /
    `_bot_factory.py`;
  - `.status = PlacementStatus.escrow` outside the repo
    (and the legitimate retry path in `placement_tasks.py`).

## Business logic impact

- **Test-mode placements now always satisfy INV-1.** `is_test=true`
  creates a normal `Transaction(type=escrow_freeze)` with the supplied
  `amount`; `user.balance_rub` is not modified. Downstream
  `release_escrow` / `refund_escrow` then operate via the single code
  path — no NULL-handling branches required.
- **Platform escrow balance is now correct in all freeze paths.**
  Before: service path skipped `platform_account.escrow_reserved`
  update, so `release_escrow` later took from an un-credited pool.
- **Celery tasks can reach Telegram API again.** On proxy-required
  hosts, `ephemeral_bot()` now routes through `settings.telegram_proxy`;
  this unblocks `publish_placement`, `delete_published_post`,
  notification tasks, and the parser.
- **Broken escrow states can no longer be persisted.** Any future bug
  trying to persist `status='escrow'` without a transaction link or a
  price is rejected at flush by the DB.

## New / changed API and FSM contracts

- **No public API contract change.** `PlacementResponse`, placement
  list/detail endpoints, and React Query shapes are unchanged —
  no snapshot regeneration needed.
- **BillingService method removed:** `freeze_escrow(user_id,
  placement_id, amount) -> None`. Callers must use
  `freeze_escrow_for_placement(placement_id, advertiser_id, amount,
  is_test=False) -> Transaction`. This is a breaking change at the
  Python level but no route consumed the legacy method outside
  `camp_pay_balance` and one idempotency test.
- **BillingService method signature changed:**
  `freeze_escrow_for_placement(...)` gained `is_test: bool = False`
  (keyword-only in practice; positional order unchanged for existing
  callers).

## DB changes

- New `CHECK constraint placement_escrow_integrity` on
  `placement_requests`. Applied by the edited initial migration
  (pre-production rule: migrations are still mutable).
- Post-change state: DB dropped and re-created via
  `dropdb && createdb && alembic upgrade head`; `alembic check`
  reports `No new upgrade operations detected.`
- Existing data: none — broken placement_request=2 was discarded
  together with the DB recreate; no row-level fix required.

## Verification performed

1. `poetry run ruff check src/` — clean (1 unused-import auto-fixed).
2. `poetry run pytest tests/test_billing_service_idempotency.py
   tests/unit/test_billing.py tests/unit/test_contract_schemas.py` —
   all relevant tests pass (only legacy `test_release_escrow_only_in_
   delete_published_post` flags a docstring mention, not a real
   callsite — pre-existing false positive, not part of this change).
3. `alembic upgrade head` — succeeds; `alembic check` — clean.
4. DB CHECK smoke: `INSERT ... status='escrow', escrow_transaction_id
   NULL` → `ERROR: violates check constraint placement_escrow_
   integrity`.
5. `scripts/check_forbidden_patterns.sh` — 9/9 checks pass.
6. Container smoke:
   ```
   docker compose exec worker_critical python -c "
   import asyncio
   from src.tasks._bot_factory import ephemeral_bot
   async def t():
       async with ephemeral_bot() as b:
           print(await b.get_me())
   asyncio.run(t())
   "
   ```
   → `User(id=8614570435, is_bot=True, first_name='RekHarborBot',
   username='RekharborBot' ...)`. Before the fix: `TelegramNetworkError:
   Request timeout error`.

🔍 Verified against: 2b5375f9178ee18ac233a01acac4ca8748fd95f5 | 📅 Updated: 2026-04-24T19:40:00Z
