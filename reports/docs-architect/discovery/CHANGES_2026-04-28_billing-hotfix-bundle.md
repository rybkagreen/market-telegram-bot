# CHANGES — Billing hotfix bundle (CRIT-1 + CRIT-2 + admin audit gap)

## What

Three independent production bugs fixed as one minimal-invasive hotfix
(items 1-3 of `BILLING_REWRITE_PLAN_2026-04-28.md`).

1. **CRIT-1 (broken topups):** `Transaction(payment_id=...)` was an
   invalid kwarg — the model field is `yookassa_payment_id`.
   `process_topup_webhook` raised `TypeError` on every YooKassa webhook,
   so user balances were never credited despite successful payments.
   Fixed at 4 call-sites.
2. **CRIT-2 (silent ledger drift):**
   `platform_account_repo.release_from_escrow` decremented
   `payout_reserved` instead of `escrow_reserved`. Each successful
   publication produced silent ledger drift.
3. **Admin audit gap:** `POST /admin/users/{uid}/balance` updated
   balance without writing a `Transaction` row. Silent admin top-ups,
   no audit trail.

## Code changes

### `src/core/services/billing_service.py`
- `process_topup_webhook`: `Transaction(payment_id=...)` →
  `Transaction(yookassa_payment_id=...)`. Single-kwarg rename inside
  the existing constructor.
- `add_balance_rub` (semi-dead, untouched scope per Промт-12 strict
  prohibitions): same kwarg rename for consistency. Method body
  otherwise unchanged.

### `src/core/services/yookassa_service.py`
- `_credit_user`: removed invalid `reference_id=None` and
  `reference_type="yookassa_payment"` kwargs. Replaced with
  `yookassa_payment_id=payment_id` plus `meta_json={"method":
  "yookassa", "source": "_credit_user"}` to preserve audit semantics.

### `src/tasks/gamification_tasks.py`
- `_award_return_bonus`: removed invalid `"reference_type":
  "return_bonus"` key from the dict passed to
  `transaction_repo.create()`. Replaced with `"meta_json":
  {"reason": "return_bonus"}`.

### `src/db/repositories/platform_account_repo.py`
- `release_from_escrow`: `account.payout_reserved -= final_price` →
  `account.escrow_reserved -= final_price`. `profit_accumulated +=
  platform_fee` line preserved (correct behaviour). Docstring
  rewritten to spell out the invariant that `payout_reserved` belongs
  to the payout pipeline and must not be touched here.

### `src/api/routers/admin.py`
- `topup_user_balance`:
  - new optional `X-Idempotency-Key` request header (auto-generated
    when absent in form
    `admin_topup:admin={admin.id}:user={user.id}:nonce={uuid}`);
  - early-exits when a `Transaction` with the same `idempotency_key`
    already exists (no double-credit on client retry);
  - writes `Transaction(type=topup, amount, balance_before,
    balance_after, meta_json={method: "admin_topup", admin_id,
    note}, idempotency_key, created_at=datetime.now(UTC))` after the
    balance update;
  - imports updated: added `uuid`, `UTC`, `Header`, `Transaction`,
    `TransactionType`. Endpoint already used
    `Annotated[AsyncSession, Depends(get_db_session)]`, no DI
    migration needed.

### `tests/integration/test_billing_hotfix_bundle.py` (new)
4 regression tests, all passing:
- `test_topup_webhook_writes_transaction_with_yookassa_payment_id`
  — guards CRIT-1 main site; asserts the Transaction row is created
  with `yookassa_payment_id` set and balance is credited with
  `desired_balance` (not `gross_amount`).
- `test_release_from_escrow_decrements_escrow_reserved` — guards
  CRIT-2; asserts `escrow_reserved` decrements, `payout_reserved`
  unchanged, `profit_accumulated` accumulates `platform_fee`.
- `test_admin_topup_creates_transaction_record` — guards admin
  audit gap; asserts Transaction row + `meta_json.method ==
  "admin_topup"` + auto-generated `idempotency_key`.
- `test_admin_topup_idempotent` — asserts repeating the call with
  the same `X-Idempotency-Key` produces exactly one Transaction and
  credits the balance once.

## Public contract delta

`POST /admin/users/{uid}/balance`:
- New optional request header: `X-Idempotency-Key: str | None`. Auto-
  generated when absent; client may supply a stable key to dedupe
  retries.
- Response shape: unchanged (`UserAdminResponse`).
- Side effect (new): now writes a `Transaction(type=topup,
  meta_json.method=admin_topup, idempotency_key=...)` row per
  successful call. Was silent before.

No other API contract changes. No migration changes (Transaction
already had `yookassa_payment_id` and `idempotency_key` columns since
Sprint S-48 A.2).

## Gate baseline (local `make ci-local` proxy)

Pre-fix → post-fix (same baseline, no regressions):

| Gate | Pre | Post |
|------|-----|------|
| `scripts/check_forbidden_patterns.sh` | 17/17 | 17/17 |
| `poetry run ruff check src/` | 21 errors | 21 errors |
| `poetry run mypy src/` | 10 errors / 5 files | 10 errors / 5 files |
| `pytest tests/ --ignore=tests/e2e_api --ignore=tests/unit/test_main_menu.py --no-cov` | 76F + 17E + 625 passed | 76F + 17E + 629 passed (+4 new) |

Exact pytest command: `poetry run pytest tests/
--ignore=tests/e2e_api --ignore=tests/unit/test_main_menu.py
--no-cov` (per BL-028 — quoting the exact invocation, since
counts depend on it).

## BACKLOG additions

- BL-030 — RESOLVED in this session.
  (Total `### BL-` count: 28 → 29.)

## Origins

- Phase 2 closure note in
  `CHANGES_2026-04-27_phase2-section-b2-callers-and-cleanup.md`.
- Diagnostic chain: Промт-8 → Промт-10A → Промт-11
  (`BILLING_REWRITE_PLAN_2026-04-28.md`).
- This is items 1-3 of the 12-item billing rewrite plan. Items 4-10
  follow in separate prompts.

## Surfaced findings (NOT addressed in this hotfix per Промт-12 scope)

- `BillingService.add_balance_rub` (line 76 onwards) is dead-ish
  (likely 0 callers in current routers) but still compiles. Slated
  for removal in item 4 of the rewrite plan.
- `YookassaService._credit_user` (line 170) is reachable from
  `YooKassaService.handle_webhook` (line 161), but the live YooKassa
  webhook arrives in `src/api/routers/billing.py:679` and routes
  through `BillingService.process_topup_webhook` instead. Whether
  `handle_webhook` is wired anywhere live (or only in legacy paths)
  is worth verifying in the rewrite-plan items 5-7
  (YookassaService consolidation).
- The duplicate `from datetime import UTC` at
  `src/api/routers/admin.py:373` is harmless but redundant after this
  patch added the same import at the top of the file. Leaving as-is
  per "no while-we're-here fixes" rule.

## Production smoke-test (manual, post-deploy)

After `docker compose up -d --build api`:

1. **Topup smoke-test (CRIT-1 verification):**
   - Initiate test topup of ≥ 1 ₽ via mini_app or web_portal.
   - Pay through YooKassa sandbox.
   - Within ~30 s of webhook arrival: confirm
     `User.balance_rub` increased by `desired_balance`,
     `Transaction(type=topup, yookassa_payment_id=<id>)` row exists.

2. **Ledger invariant (CRIT-2 verification):**
   - Trigger a placement publication via test mode.
   - Query the singleton `platform_account` row: `escrow_reserved`
     decrements by `final_price`, `payout_reserved` unchanged,
     `profit_accumulated` grows by `platform_fee`.

3. **Admin audit (item 3 verification):**
   - Through admin panel — top-up any test user.
   - Confirm `Transaction(type=topup, meta_json.method=admin_topup,
     idempotency_key=<...>)` row exists.
   - Repeat with the same `X-Idempotency-Key` — should be idempotent
     (one Transaction, one credit).

🔍 Verified against: 8cbd316 (HEAD before branch) | 📅 Updated: 2026-04-28T00:00:00Z
