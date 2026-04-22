# CHANGES 2026-04-21 — plan-02 payout concurrent approve safety

## Scope

Follow-up to `FIX_PLAN_06_followups/plan-02-payout-concurrent-approve-safety.md`
(P1). Closes a financial double-spend race in
`PayoutService.approve_request` / `reject_request` and brings both
methods in line with the **Service Transaction Contract (S-48)**.

This plan modifies a financial service. No DB migration; no schema
change; no public-API change.

## Why this matters (root cause)

`approve_request` ran in **three sequential sessions** —
status check → `complete_payout` (financial move) →
`admin_id` stamp. Two parallel admin clicks could both pass the status
check in independent sessions, then both invoke `complete_payout` →
`payout_reserved -= gross` would be applied twice → reserve drifts to
`-gross` and USN expense gets recorded twice.

`reject_request` was symmetric: parallel rejects could double-credit
`User.earned_rub`.

This is the same class of bug as ESCROW-002 (auto-release missing
rollback) — checked-but-unlocked finance state mutating across
sessions.

## What changed

### `src/core/services/payout_service.py`

- **`approve_request`** rewritten as a single session inside
  `async with session.begin():`. The first statement is now
  `select(PayoutRequest).where(id=…).with_for_update()` — Postgres
  row lock for the duration of the transaction. Concurrent admins
  serialize on this lock; whoever lands second sees the already-
  finalized status and raises `ValueError("already finalized")`.
- **`reject_request`** identical pattern; same lock order
  (`PayoutRequest` → `PlatformAccount` via `complete_payout` /
  `add_to_payout_reserved`) so deadlock between approve↔reject is
  impossible.
- **`complete_payout(session, payout_id)`** — internal
  `async with session.begin():` removed. The method now requires the
  caller's transaction (S-48: "outermost caller owns the
  transaction"). Performs `flush` only.
- **`reject_payout(session, payout_id, reason)`** — same: the inner
  `session.begin()` removed.

Audit (`grep -rn "complete_payout\|reject_payout\b" src/`): the only
callers of `PayoutService.complete_payout` and
`PayoutService.reject_payout` are `approve_request` and
`reject_request` themselves — both now own the transaction. Other
hits in the grep are unrelated (`PlatformAccountRepository.complete_payout`
is a different method on a different class; `bot/handlers/admin/users.py`
defines a coincidentally-named handler that does not call the
service method). No external caller change required.

### `tests/integration/test_payout_concurrent.py` (new)

Three concurrency regression tests using `asyncio.gather` over a
real Postgres testcontainer:

| Test | Scenario | Critical assert |
|---|---|---|
| `test_three_concurrent_approves_yield_one_success` | 3 × `approve_request` on the same `payout_id` | `len(successes) == 1`, `len(failures) == 2`, `platform.payout_reserved == 0` (not `-gross` or `-2*gross`) |
| `test_concurrent_approve_then_reject_one_wins` | 1 × `approve` ‖ 1 × `reject` | exactly 1 winner; if `approve` won → `payout=paid`, `earned_rub=0`; if `reject` won → `payout=rejected`, `earned_rub=gross`; reserve is 0 either way |
| `test_three_concurrent_rejects_yield_one_success` | 3 × `reject_request` on the same `payout_id` | `len(successes) == 1`, `owner.earned_rub == gross` (not `2*gross` / `3*gross`) |

These tests would have failed pre-fix: without `FOR UPDATE`, the
`payout_reserved` / `earned_rub` invariants drift on the first race.
Verified by running the suite against the pre-fix code via `git stash`
during development.

## Validation

```bash
# Existing lifecycle tests (regression — service contract still works)
poetry run pytest tests/integration/test_payout_lifecycle.py --no-cov -v
# → 4 passed in 6.01s

# New concurrency tests
poetry run pytest tests/integration/test_payout_concurrent.py --no-cov -v
# → 3 passed in 5.16s

# Full payout slice
poetry run pytest tests/integration/test_payout_lifecycle.py \
    tests/integration/test_payout_concurrent.py \
    tests/unit/api/test_admin_payouts.py --no-cov
# → 16 passed in 9.28s

# Lint
poetry run ruff check src/core/services/payout_service.py
poetry run ruff check tests/integration/
# → All checks passed!

# Grep-guard
bash scripts/check_forbidden_patterns.sh
# → 7/7 ok
```

## Lock order documentation

For future financial services touching both `PayoutRequest` and
`PlatformAccount`, the established order in this module is:

1. `PayoutRequest` (row lock via `select(...).with_for_update()`)
2. `PlatformAccount` (via `PlatformAccountRepository.get_for_update()`,
   reached transitively from `complete_payout` /
   `add_to_payout_reserved` / `add_to_profit`)

Inverting this order in another method would create a classic A→B vs
B→A deadlock pattern. Both `approve_request` and `reject_request`
follow PayoutRequest → PlatformAccount.

## Out of scope (tracked separately)

- Same-class race in `BillingService` if any — separate audit.
- Migration to a queue + idempotency-key model instead of FOR UPDATE
  (a different architectural class of solution; current approach is
  correct for admin-driven flows).
- Typed exceptions (`PayoutAlreadyFinalizedError` etc.) — plan-05.

🔍 Verified against: a50e871 (main) | 📅 Created: 2026-04-21
