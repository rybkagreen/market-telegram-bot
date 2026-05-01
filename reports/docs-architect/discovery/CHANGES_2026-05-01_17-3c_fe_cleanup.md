# 17.3c — FE cleanup + sprint closure

**Date:** 2026-05-01
**Branch:** `feat/17.3-credits-rename` (continuation, not a new branch)
**Develop after FF merge:** `c30d2d6` (was `4008665`)
**Main:** untouched (`6828cf4`)

---

## Scope summary

Three sub-commits on the feature branch + sprint-closure CHANGELOG +
FF merge into develop + CHANGES file (this document).

| # | Commit | SHA | Type |
|---|---|---|---|
| 1 | Remove dead `buyCredits` / `useBuyCredits` / `BuyCreditsResponse` from mini_app | `0ea5042` | refactor(mini_app) |
| 2 | Update web_portal admin URLs to `/admin/grants/*` + `/admin/bonuses/*` | `9f9bd33` | refactor(web_portal) |
| 3 | CHANGELOG sprint-closure entry covering 17.3a + 17.3b + 17.3c | `c30d2d6` | docs(changelog) |

---

## Шаг 0 — FE consumer audit (read-only)

Empirical grep audit of FE codebase for credits-related residues.
Findings categorized in `tmp/step_0_fe_audit.md` (now removed at
session end). Key results:

### Category A — Dead code (deleted in Шаг 1)

`POST /api/billing/credits` was removed in 17.3b. FE had:

- `mini_app/src/api/billing.ts` lines 87-93 — `BuyCreditsResponse`
  interface + `buyCredits` function.
- `mini_app/src/hooks/queries/useBillingQueries.ts` line 2 (import) +
  lines 33-52 — `useBuyCredits` hook.

**No imports from any screen.** Hook was defined but never wired into
the UI. Pure dead-code removal.

### Category B — Live consumers (renamed in Шаг 2)

Admin panel actively uses both endpoints.

- `web_portal/src/api/admin.ts` — `PlatformCreditResponse` interface,
  `createPlatformCredit` / `createGamificationBonus` functions, two URL
  literals.
- `web_portal/src/hooks/useAdminQueries.ts` — `useCreatePlatformCredit`
  + `useCreateGamificationBonus`.
- `web_portal/src/screens/admin/AdminUserDetail.tsx` — imports +
  `platformCredit` local var + `handlePlatformCredit` handler +
  `gamificationBonus` local var + `handleGamificationBonus` handler.

### Category C — Historical docs (no touch)

CHANGELOG.md, BACKLOG.md, prior CHANGES_*.md and CREDITS/RESEARCH
discovery files reference old URLs as historical record. Append-only.

### Surprises

**None.** Audit findings matched plan expectations exactly:
- mini_app FE had dead `useBuyCredits`.
- web_portal had live admin callsites in 1 screen + 1 hook + 1 api module.
- TS interfaces existed for both admin endpoints.

---

## Шаг 1 — `0ea5042` Dead consumer removal (mini_app)

**Files:**
- `mini_app/src/api/billing.ts` — removed lines 87-93 (interface +
  function).
- `mini_app/src/hooks/queries/useBillingQueries.ts` — removed `buyCredits`
  from import statement, removed `useBuyCredits` hook (20 LOC).

**Verify:** `grep -rn "useBuyCredits\|buyCredits\|BuyCreditsResponse"
mini_app/` → 0 matches. `npx tsc -b --noEmit` → exit 0.

---

## Шаг 2 — `9f9bd33` Admin URL + identifier rename (web_portal)

**URL changes (atomic FE→BE alignment):**
- `admin/credits/platform-credit` → `admin/grants/platform`
- `admin/credits/gamification-bonus` → `admin/bonuses/gamification`

**Identifier renames (FE consistency, per plan §5):**
- `PlatformCreditResponse` → `PlatformGrantResponse` (interface)
- `createPlatformCredit` → `createPlatformGrant` (api function)
- `useCreatePlatformCredit` → `useCreatePlatformGrant` (hook)
- `platformCredit` → `platformGrant` (screen local var)
- `handlePlatformCredit` → `handlePlatformGrant` (screen handler)

**Kept (semantic split preserved):**
- `GamificationBonusResponse`, `createGamificationBonus`,
  `useCreateGamificationBonus`, `gamificationBonus`,
  `handleGamificationBonus` — all unchanged. Only the URL string was
  updated.

**Kept (UI form state, internal):**
- `creditAmount`, `creditComment`, `creditFeedback` — local form-input
  state in `AdminUserDetail.tsx`, no public surface.

**Verify:** `grep -rn "admin/credits/platform-credit\|admin/credits/
gamification-bonus\|PlatformCreditResponse\|createPlatformCredit\|
useCreatePlatformCredit\|handlePlatformCredit" web_portal/src/` → 0
matches. `npx tsc -b --noEmit` → exit 0.

---

## Шаг 3 — Final verify gates

| Gate | Result | Baseline | Status |
|---|---|---|---|
| `make ci-local` pytest | 76 failed / 780 passed / 6 skipped / 17 errors | 76 / 780 / 6 / 17 | ✓ preserved |
| `poetry run ruff check src/ tests/` | 20 errors | 20 | ✓ preserved |
| `alembic check` | "No new upgrade operations detected" | clean | ✓ |
| `npx tsc -b --noEmit` (mini_app) | exit 0 | clean | ✓ |
| `npx tsc -b --noEmit` (web_portal) | exit 0 | clean | ✓ |

No regressions. Test counts identical to post-17.3b baseline.

---

## Шаг 4 — `c30d2d6` CHANGELOG sprint-closure entry

Single comprehensive entry under `[Unreleased]` covering 17.3a + 17.3b +
17.3c. Sections: Removed / Changed / Fixed / Internal / Migration notes /
Verify gates / Detail. End-state described from user-observable public
surface (URL + schema + FE).

---

## Шаг 5 — FF merge `feat/17.3-credits-rename` → `develop`

Pre-verify: `develop` HEAD = `4008665` (matched expected baseline).

Merge command: `git merge --ff-only feat/17.3-credits-rename`.
Result: develop fast-forwarded `4008665..c30d2d6` (8 commits ahead).

Pushed to origin: `git push origin develop` succeeded.

**Diff summary:**
```
13 files changed, 280 insertions(+), 152 deletions(-)
```

Files touched (post-merge):
- `CHANGELOG.md` — sprint-closure entry.
- `docs/AAA-02_API_REFERENCE.md`, `docs/AAA-04_SERVICE_REFERENCE.md` —
  stale credits refs cleanup (17.3b).
- `mini_app/src/api/billing.ts`, `mini_app/src/hooks/queries/useBillingQueries.ts` — Шаг 1.
- `reports/docs-architect/discovery/CHANGES_2026-05-01_17-3b_backend_url_renames.md` —
  17.3b CHANGES file (created in 17.3b).
- `src/api/routers/admin.py`, `src/api/routers/billing.py`,
  `src/core/services/billing_service.py`, `src/tasks/billing_tasks.py` —
  17.3b backend changes.
- `web_portal/src/api/admin.ts`, `web_portal/src/hooks/useAdminQueries.ts`,
  `web_portal/src/screens/admin/AdminUserDetail.tsx` — Шаг 2.

---

## Production impact

- **develop** now contains the full 17.3 bundle (a + b + c). Atomic
  FE+BE alignment: all admin URL callsites match the renamed backend
  endpoints; no dual code paths or compat shims.
- **main** remains at v0.1.0 (`6828cf4`). Any `develop → main` merge
  will require an atomic deploy (FE bundle + backend) since old admin
  URLs return 404 after the backend rename.
- Test infrastructure baseline preserved across the entire sprint.
- Documentation (CHANGELOG + AAA-02 + AAA-04) reflects current state.

---

## Surprises / deviations from plan

**None.** All steps executed in plan order without blockers.

The Шаг 0 audit confirmed:
- Dead code in mini_app exactly as 17.3b implied (`useBuyCredits` had
  zero screen consumers).
- Live callsites in web_portal exactly as expected (1 screen, 1 hook,
  1 api module).
- TS interfaces existed for both admin endpoints — Шаг 2 included
  interface rename + cascaded identifier rename for FE consistency
  (per plan §5 "PlatformCreditResponse → PlatformGrantResponse").

---

## Branch cleanup

`feat/17.3-credits-rename` kept post-merge for traceability. History
preserved in develop via fast-forward. Future cleanup decision deferred
to Marina.

---

🔍 Verified against: `c30d2d6` (develop)
📅 Updated: 2026-05-01T18:00:00+03:00
