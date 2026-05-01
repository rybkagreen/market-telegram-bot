# CHANGES — BL-064: align `charge_balance_for_plan` к canonical `plan_purchase` enum + fix expense analytics

**Date:** 2026-05-01
**Branch:** `chore/bl-064-align-plan-purchase-canonical`
**Base:** `develop @ 69dbc79` (post-BL-067 merge)
**Scope:** internal data shape + analytics filter — NOT a public contract change.

---

## Rationale

Investigation BL-064 (read-only, 2026-05-01) surfaced two parallel implementations of "user pays for plan from balance":

- **Canonical (bot path):** `src/bot/handlers/billing/billing.py:275` writes
  `Transaction.type=TransactionType.plan_purchase` with no `meta_json["type"]`
  discriminator.
- **Misfit (API path):** `BillingService.charge_balance_for_plan` wrote
  `Transaction.type=TransactionType.spend` plus an orphan
  `meta_json["type"]="plan_payment"` discriminator with zero functional
  consumers anywhere in the codebase.

This divergence created two latent issues:

1. The `meta_json["type"]="plan_payment"` discriminator was a dead write —
   no analytics filter, no display logic, no test, and no code branch read
   it. `_VISIBLE_TX_TYPES` and `_INCOME/EXPENSE_TX_TYPES` operate on
   `Transaction.type` (the enum column), not on `meta_json`.
2. `_EXPENSE_TX_TYPES` (`src/api/routers/analytics.py`) included `"spend"`
   but **not** `"plan_purchase"`. Bot-originated plan purchases (the
   canonical path) were therefore invisible to cashflow expense
   reporting — a latent analytics blind spot.

Pre-prod state confirmed in 17.2 step 0: `transactions` row count = 0.
No data migration needed; this is a clean change.

---

## Scope

**Touched (3 files):**

1. `src/core/services/billing_service.py` — `charge_balance_for_plan`:
   - `Transaction.type`: `TransactionType.spend` → `TransactionType.plan_purchase`.
   - Removed orphan `meta_json["type"]="plan_payment"` line. Remaining
     `meta_json={"currency": "rub"}` preserved.
2. `src/api/routers/analytics.py` — `_EXPENSE_TX_TYPES`:
   - Added `"plan_purchase"` to the set. Now includes plan purchases
     (both bot-originated and API-originated) in cashflow expense
     classification.
3. `reports/docs-architect/discovery/CHANGES_2026-05-01_BL-064-align-plan-purchase-canonical.md`
   — this file.

**Intentionally NOT touched:**

- `src/core/services/billing_service.py:191-284` (`activate_plan`): dead
  code with 0 callers. Per `BACKLOG.md:925` it is slated for deletion in
  Промт-15 with `PlanChangeService` introduction. Editing dead code in
  BL-064 would expand scope artificially. The misfit pattern at
  lines 265 (`Transaction.type=spend`) and 268 (`meta_json["type"]="plan_purchase"`)
  remains as-is until that refactor.
- `src/bot/handlers/billing/billing.py:275`: already canonical
  (`TransactionType.plan_purchase`, no meta discriminator).
- `_VISIBLE_TX_TYPES` (`src/api/routers/billing.py:484-493`): already
  contains `"plan_purchase"`. No edit needed.
- `_INCOME_TX_TYPES`: verified — does NOT contain `"plan_purchase"`
  (correct — plan purchase is an expense, not income).

---

## Behaviour change

**Pre-existing rows:** none (transactions=0 in pre-prod). No backfill.

**Post-change semantics for `charge_balance_for_plan` (the live API path
via `/api/billing/credits` route):**

- Transactions are tagged `Transaction.type=plan_purchase` instead of
  `spend`.
- They are visible in `/api/billing/history` (still — `_VISIBLE_TX_TYPES`
  already included `plan_purchase`).
- They are now included in cashflow expense aggregation (`/api/analytics/cashflow`).
- The `meta_json` payload has one fewer redundant key. The `"currency"`
  field is preserved for any downstream consumer.

**Convergence with bot path:** API path and bot path now both produce
identical `Transaction` shape for plan purchases:
`type=plan_purchase`, no `meta_json["type"]` discriminator.

---

## Verify gate

- Empirical grep confirms: `"plan_payment"` → 0 hits in `src/` and `tests/`.
- `TransactionType.spend` remaining hit in `billing_service.py`: 1, at
  line 265 inside dead `activate_plan` (untouched per scope).
- `"plan_purchase"` in `_EXPENSE_TX_TYPES`: 1 hit at `analytics.py:269`.
- `ruff check src/core/services/billing_service.py src/api/routers/analytics.py`: clean.
- `ruff format --check`: 2 files already formatted.
- `pytest tests/unit/test_billing.py tests/integration/test_billing_hotfix_bundle.py tests/unit/test_no_dead_methods.py`:
  26 passed, 1 pre-existing fail (`TestEscrowReleaseLocation::test_release_escrow_only_in_delete_published_post`,
  fails identically on develop, unrelated to this commit — fails on a
  string match against `disputes.py:595`).

No new test additions required: investigation confirmed zero test
coverage of the `meta_json["type"]="plan_payment"` discriminator and
zero test coverage of `charge_balance_for_plan`'s exact enum value.

---

## Rollback

Single atomic commit. `git revert <SHA>` is safe. No DB schema changes,
no migration, no produced data depending on the new shape (transactions=0).

---

## Sub-fix surfaced

`_EXPENSE_TX_TYPES` analytics blind spot for `plan_purchase` (originally
suspected as a separate BL-062-class bug during investigation). Closed
opportunistically here because it is the same conceptual fix as the
enum-alignment work — plan purchases should consistently appear as
expense regardless of write path.

---

## Pending Marina manual actions

- BACKLOG.md: BL-064 closeable via this commit (subject to merge).
- `activate_plan` dead code: still pending Промт-15 (BACKLOG:925) — not
  touched here.

---

🔍 Verified against: `develop @ 69dbc79`
📅 Updated: 2026-05-01T13:50+03:00
