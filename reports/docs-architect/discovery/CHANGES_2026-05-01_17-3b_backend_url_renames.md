# 17.3b — Backend URL renames + comment residues

**Date:** 2026-05-01
**Branch:** `feat/17.3-credits-rename` (off `develop@4008665`)
**Scope:** Backend-only. FE counterparts handled in 17.3c on the same branch.
**Develop:** untouched (still `4008665`).
**Main:** untouched (still `6828cf4`).

---

## Scope summary

Four sub-commits on the feature branch. Шаг 3 was confirmed no-op during
Шаг 0 verification (no backend Pydantic schemas with "Credit" naming
existed) and is documented below for completeness.

| # | Commit | SHA | Type |
|---|---|---|---|
| 1 | Drop dead `POST /credits` handler + orphan `charge_balance_for_plan` service method | `ee31961` | refactor(billing) |
| 2 | Split admin URLs `/admin/credits/*` → `/admin/grants/platform` + `/admin/bonuses/gamification` | `efe2d11` | refactor(admin) |
| 4a | Comment residues in `src/` (2 instances after Шаг 1 auto-removed 2 of the original 4) | `c5aeb96` | chore |
| 4b | Stale doc references in `docs/AAA-02_API_REFERENCE.md` and `docs/AAA-04_SERVICE_REFERENCE.md` | `f8afea3` | docs |

---

## Шаг 0.6 routing audit — chosen direction & rationale

### Initial plan
Rename `POST /api/billing/credits` → `POST /api/billing/plans/charge`
(or similar resource-first action), preserve handler.

### Audit finding (the surprise)

**`POST /credits` is a debit-only ghost endpoint**, not just a misnamed one:

| | `POST /credits` | `POST /plan` (the *real* purchase endpoint) |
|---|---|---|
| Body | `TopupRequest{desired_amount}` | `PlanRequest{plan}` |
| Validates | balance ≥ amount | balance ≥ `PLAN_COSTS[plan]` |
| Deducts | `amount` | `PLAN_COSTS[plan]` |
| Activates plan | **NO** — does not touch `User.plan` / `plan_expires_at` / `ai_uses_count` | **YES** |
| FE consumer (calls hook from a screen) | **none** — `useBuyCredits` defined at `mini_app/src/hooks/queries/useBillingQueries.ts:33`, not imported anywhere | `usePurchasePlan` consumed by `Plans.tsx` in mini_app + web_portal |

Real plan purchases go through `POST /plan` / `change_plan`. The
`/credits` route deducts money but does not grant a plan — calling it
would be silently destructive. The pseudo-consumer hook `useBuyCredits`
is defined but never invoked; the FE call site (`buyCredits` in
`mini_app/src/api/billing.ts:91`) is reachable only through that
unused hook.

`reports/docs-architect/discovery/RESEARCH_17-3_credits_inventory_2026-05-01.md:230`
already flagged the endpoint as a likely dead route under "Decision
blocker". The original 17.3b Шаг 0 verification answered "consumers
exist" by finding the hook *definition*; the hook's *call graph* was
not traced. False positive.

### Decision: DROP, not rename

Rejected alternatives (audit log):

| Option | Reason rejected |
|---|---|
| Rename to `/plans/charge` | Preserves dead code; creates lookalike trio next to existing `GET /plans` and `POST /plan`. Three plan-related verbs across two pluralizations. |
| Rename to `/plans/purchase` | Same dead-code preservation. FE already exports `purchasePlan` mapped to `POST /plan`; new endpoint would alias the consumer namespace. |
| Rename to `/plans/activate` | Endpoint does not activate anything — active misnomer. |
| Resource-style `POST /subscriptions` | Bigger redesign than 17.3b scope; would imply replacing `POST /plan` too. Defer as BL if subscription concept ever lands. |
| Keep + rename anyway, drop later | Adds work, leaves dead code in production state, contradicts "atomic break" posture. |

---

## Diff overview

### Шаг 1 — `ee31961` (`-93 lines`)
- `src/api/routers/billing.py` — `-31 lines`. Removed `@router.post("/credits", ...)` block and `buy_credits` async function (lines 560-588). Imports unaffected (no exclusive imports for the dead handler).
- `src/core/services/billing_service.py` — `-62 lines`. Removed `BillingService.charge_balance_for_plan` method (lines 70-129) and its entry in the class-level `Методы:` docstring (line 61). Imports `UserRepository`, `async_session_factory`, `InsufficientFundsError`, `TransactionType` all remain in use by other methods.

### Шаг 2 — `efe2d11` (`+2 / -2 lines`)
- `src/api/routers/admin.py` — URL strings only.
  - `"/credits/platform-credit"` → `"/grants/platform"` (line 834)
  - `"/credits/gamification-bonus"` → `"/bonuses/gamification"` (line 890)
- Function names (`create_admin_grant`, `create_gamification_bonus`), body schemas (`AdminGrantRequest`, `GamificationBonusRequest`), service methods all unchanged — internal naming was already correct, only the URL surface needed alignment.

### Шаг 4a — `c5aeb96` (`+2 / -2 lines`)
- `src/tasks/billing_tasks.py:115` — `«Недостаточно кредитов»` → `«Недостаточно средств»`.
- `src/core/services/billing_service.py:101` — `«зачисляем кредиты»` → `«зачисляем средства»` (line shifted from 163 to 101 after Шаг 1 method deletion).
- The other two original residues (`billing.py:568` docstring, `billing_service.py:78` docstring) auto-disappeared with Шаг 1 deletions.

### Шаг 4b — `f8afea3` (`-10 lines`)
- `docs/AAA-02_API_REFERENCE.md` — removed the `POST /api/billing/credits` table row (the endpoint is gone).
- `docs/AAA-04_SERVICE_REFERENCE.md` — removed the `buy_credits_for_plan` method block (also referenced a non-existent `user.credits` column under the v4.3 single-currency model — already-stale before 17.3b) and its row in Section 8.2 transaction-scope table.

---

## Шаг 3 — no-op (documented for completeness)

The plan called for renaming Pydantic schemas: `BuyCreditsResponse`,
`PlatformCreditResponse`, `GamificationBonusResponse`. None of these
exist as backend Pydantic schemas:

- `BuyCreditsResponse` — exists only as a TypeScript interface in
  `mini_app/src/api/billing.ts:87`. Backend returned a raw `dict` literal
  (now removed in Шаг 1). FE-side rename handled in 17.3c.
- `PlatformCreditResponse`, `GamificationBonusResponse` — do not exist
  anywhere in the codebase. The corresponding endpoints return raw
  `dict`. The request schemas that *do* exist (`AdminGrantRequest`,
  `GamificationBonusRequest`) are already named correctly.

---

## Impact

### Production impact (after eventual merge)

- **FE break expected.** Anything calling `useBuyCredits` (currently no
  screen does) would fail. Anything calling the admin URLs would 404.
  All FE callers fixed in 17.3c on the same feature branch — no
  intermediate state lands on `develop`.
- **No deprecation alias / dual-route.** Atomic break, isolated on the
  feature branch until FE catches up.
- **No data loss / no migration.** No DB schema changes. The
  `TransactionType.plan_purchase` enum value is preserved (still in use
  elsewhere — bot handler, analytics, billing list filter).

### Migration impact

None. No Alembic changes. `alembic check` clean.

### Test impact

`pytest tests/ --ignore=tests/e2e_api --ignore=tests/unit/test_main_menu.py --no-cov`
on the feature branch tip:

- **76 failed, 780 passed, 6 skipped, 17 errors** — identical to baseline.

No tests reference `/api/billing/credits`, `buy_credits`,
`charge_balance_for_plan`, or the renamed admin paths
(`grep tests/` returned zero matches). No new failures introduced.

`ruff check src/ tests/`: 20 errors (= baseline).
`alembic check`: clean.

---

## Lesson — Шаг 0 verification false positive

The original 17.3b plan's Шаг 0 verification asked "are there consumers
of `POST /billing/credits`?" and answered "yes" upon finding the hook
definition. The right question was "is the hook *invoked* from any
screen?" — for which the answer is no.

**Generalization for future verifications in this codebase:**
1. Trace data flow to actual call sites; do not stop at definition
   existence. A defined-but-uncalled hook is not a consumer.
2. Re-read prior research notes targeting the same surface before
   running greps. `RESEARCH_17-3_credits_inventory_2026-05-01.md` had
   already flagged this endpoint as a "decision blocker — may be a
   dead endpoint" but the note was not revisited during Шаг 0.

This is added to the project's collective verification discipline; not
a backlog entry, but worth reflecting on at the next plan-validation
gate review.

---

## Verification trail

- Branch HEAD after Шаг 6 (this commit): see git log on
  `feat/17.3-credits-rename`.
- All four prior commits (`ee31961`, `efe2d11`, `c5aeb96`, `f8afea3`)
  are linear on the feature branch — no rebases / squashes / force
  pushes. History preserved per workflow rule.
- `develop` HEAD `4008665` — unchanged (verify: `git log develop -1`).
- `main` HEAD `6828cf4` — unchanged.

🔍 Verified against: `feat/17.3-credits-rename` HEAD post-Шаг 6 | 📅 Updated: 2026-05-01
