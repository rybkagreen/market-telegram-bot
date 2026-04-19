# CHANGES — S-48: Prod Smoke Blockers Hotfix

**Branch:** `fix/s-48-prod-smoke-blockers`
**Base:** `417b5f8` (main after S-47 Stage 7 plan merge)
**Driven by:** `SMOKE_TEST_2026-04-19_portal-prod.md` (P0/P1 blockers + S-43 drift
leftovers)

---

## Scope

Hotfix for 5 prod blockers surfaced by 2026-04-19 smoke test:

- **A1** — `GET /api/channels/available?category=…` → 422 (int_parsing)
- **D1** — front sent `passport_issued_at`, backend expects `passport_issue_date`;
  `has_passport_data` badge not rendered on `/legal-profile/view`
- **F1** — `GET /api/disputes/admin/disputes?status=open` → 500 Internal Server Error
- **E1** — `/admin/payouts` → 404 in SPA (chunk missing from prod bundle)
- **A7** — `/profile/reputation` → 404 (no SPA route)

Plus S-43 drift leftovers: `owner_comment` → `owner_explanation` on read side
(3 files), confirmation that `page_size` / `gross_amount` / `has_passport_data`
source-code usages are intact (prod bundle is simply stale).

---

## §1 — A1: `/api/channels/available` 422 (P0)

### Root cause

In `src/api/routers/channels.py`, static-path GET endpoints (`/available`,
`/stats`, `/preview`) were declared **after** `GET /{channel_id}` (line 449 in
pre-fix layout). FastAPI matches routes in declaration order — `"available"`
was passed to `channel_id: int` validator, which raised `int_parsing` → 422.

Note: this also silently broke `/api/channels/stats` and `/api/channels/preview`
for GET requests (both 422), though smoke test only surfaced `/available`
because that is the wizard's first call.

### Fix

**`src/api/routers/channels.py`**:

- Moved four `/{channel_id}` endpoints
  (`GET`, `DELETE`, `POST /activate`, `PATCH /category`) to the **end** of the
  router, after all static-path GETs.
- Added section comment: `# ─── Dynamic-path endpoints (/{channel_id}/*) —
  must stay LAST ─────` with rationale.
- No behavior change; only declaration order.

### Verification

```bash
grep -n "^@router\." src/api/routers/channels.py
# /available (489) → /stats (712) → /preview (793) → /compare (894) →
# /compare/preview (923) → /{channel_id} (945) ✓
```

---

## §2 — D1: `passport_issue_date` drift + `has_passport_data` badge (P0)

### Part A — payload field name

`web_portal/src/screens/common/LegalProfileSetup.tsx:163` already sends
`passport_issue_date` (matches backend `LegalProfileUpdate`). Rename was
committed in S-43 §2.5 (`9c8d54a`, 2026-04-19). **Prod bundle is stale**: smoke
test was run against build from before that commit. Fix: `docker compose up -d
--build nginx` rebuilds the static assets — no further code change needed.

### Part B — `has_passport_data` badge (D2 WARN)

`LegalProfileView.tsx` previously showed only an `is_verified` pill. Added
an `info`-pill `📇 Паспорт добавлен` when `profile.has_passport_data === true`,
so Individual/Self-employed users can confirm their PII is on file without
exposing the values.

**Files:**

- `web_portal/src/screens/common/LegalProfileView.tsx` (+5 / −1)

---

## §3 — F1: 500 on `/api/disputes/admin/disputes` (P0)

### Root cause

`DisputeRepository.get_all_paginated` did not eager-load `advertiser` and
`owner` relationships, but the router code at
`src/api/routers/disputes.py:488-489` accesses
`d.advertiser.username` / `d.owner.username`. In an async session this triggers
lazy loading → SQLAlchemy `MissingGreenlet`/sync-IO-outside-greenlet → 500.

Secondary issue: the admin endpoint declared `status_filter: str = "open"`,
but frontend sends `?status=open`. Without an alias, the query param was
silently ignored (backend always used the default `"open"`). Functional for
the default case but broken for any other value.

### Fix

**`src/db/repositories/dispute_repo.py`**:

- Added `from sqlalchemy.orm import selectinload` import.
- `get_all_paginated` now eager-loads `PlacementDispute.advertiser` and
  `.owner` via `selectinload`. Count query stays unchanged (runs on the
  unloaded subquery).

**`src/api/routers/disputes.py`**:

- `get_all_disputes_admin` parameter now declared as
  `status_filter: Annotated[str, Query(alias="status")] = "open"` — accepts
  `?status=…` from frontend while keeping internal variable name intact.
- Added `Query` to `fastapi` imports.

### Verification

Unit: no new test. Manual: after redeploy, `GET /api/disputes/admin/disputes?status=open&limit=20`
with admin JWT should return `200 { items: [...], total, limit, offset }`.

---

## §4 — E1: AdminPayouts missing from prod bundle (P1)

### Investigation

- `web_portal/src/screens/admin/AdminPayouts.tsx` — **exists** (commit `366aafe`).
- `web_portal/src/App.tsx:74` — `const AdminPayouts = lazy(…)` — **present**.
- `web_portal/src/App.tsx:194` — `{ path: 'admin/payouts', element: <AdminPayouts /> }` — **present**.
- `useAdminPayouts` hook + API client — **present**.

Source tree on `main` is complete. 404 in prod is purely a **stale bundle**:
`docker compose up -d --build nginx` forces Vite to regenerate `dist/` inside
the nginx image. No source change required.

### Fix

No code change — documented as a deploy-only fix so future contributors don't
re-chase it.

---

## §5 — A7: `/profile/reputation` SPA route (P1)

Backend `GET /api/reputation/me/history` is working (smoke A7 — 200 with
correct shape). Frontend hooks `useReputationHistory` and `api/reputation.ts`
exist, but no screen consumed them and no route was registered.

### Fix

**New file:** `web_portal/src/screens/common/ReputationHistory.tsx`

- Reads `useReputationHistory(50, 0)` and renders a list of events.
- Each card shows action label, role, timestamp, delta (coloured ±), and
  `score_before → score_after` transition. Optional `comment` rendered below.
- Loading/error/empty states via shared UI (`Skeleton`, `Notification`,
  `EmptyState`).

**`web_portal/src/App.tsx`**:

- New lazy import: `const ReputationHistory = lazy(() => import('@/screens/common/ReputationHistory'))`.
- New route: `{ path: 'profile/reputation', element: <ReputationHistory /> }`
  (placed between `billing/history` and `acts` — inside RulesGuard like the
  rest of personal screens).

**`web_portal/src/screens/common/Cabinet.tsx`**:

- Added "История изменений →" link at the bottom of the Reputation card,
  linking to `/profile/reputation`.

---

## §6 — S-43 drift leftovers

### `owner_comment` → `owner_explanation` on read side

Backend `DisputeResponse` returns `owner_explanation` (column name), but
`DisputeUpdate` write payload still accepts `owner_comment` as an input
alias. Frontend confusion: 3 files read the response under the wrong key.

**`web_portal/src/lib/types.ts`**:

- `DisputeDetailResponse.owner_comment?: string` →
  `owner_explanation?: string | null`.

**`web_portal/src/screens/shared/MyDisputes.tsx:116`**:

- `d.owner_comment && <span>…</span>` → `d.owner_explanation && …`.

**`web_portal/src/screens/shared/DisputeDetail.tsx:69-73`**:

- `{dispute.owner_comment && …}` and `{dispute.owner_comment}` → use
  `owner_explanation`.

**Not touched:**

- `web_portal/src/api/disputes.ts:42` still sends `{ owner_comment: comment }`
  in the PATCH body — matches backend `DisputeUpdate` schema (input alias).
  Changing this would break writes.

### Confirmed already-clean (no action)

- `page_size` — 0 matches in `web_portal/src/`. `useMyPlacements` passes
  `{ view, status }` (and `getMyPlacements` sends `limit`/`offset` defaults).
  Prod bundle is stale.
- `gross_amount` — found in `types/payout.ts`, `screens/admin/AdminPayouts.tsx`,
  `screens/owner/OwnPayouts.tsx`. Source is correct; prod bundle stale.
- `has_passport_data` — type was already in `types/legal.ts`; added a
  rendering in `LegalProfileView.tsx` (see §2 Part B).

---

## §7 — Deploy notes

Required after merge:

```bash
docker compose up -d --build nginx api
```

`--build` is **mandatory** — without it, prod bundle stays stale and §2 Part A,
§4, and the "bundle-stale" parts of §6 don't take effect.

Post-deploy smoke checklist:

1. `GET /api/channels/available?category=crypto` with advertiser JWT → 200 JSON
   array. Wizard `/adv/campaigns/new/channels` should render a channel list.
2. Save legal profile as `individual` with passport data → refresh
   `/legal-profile/view` → `📇 Паспорт добавлен` pill visible.
3. Admin: `/admin/disputes` → no "Не удалось загрузить список споров" banner.
   Network: `GET /api/disputes/admin/disputes?status=open&limit=20` → 200.
4. Admin: `/admin/payouts` renders filter bar + (empty) list without 404.
5. Cabinet → "Репутация" card → click "История изменений →" →
   `/profile/reputation` renders (empty state acceptable).

---

## §8 — Out of scope for S-48

Deferred to S-49+ per the fix plan
(`reports/20260419_diagnostics/FIX_PLAN_00_index.md`):

- A2 (`page_size` in useCampaignQueries) — already clean in source; no work.
- A3 (counter-offer wiring check on the owner side).
- B1/B2 (show `last_er` / `avg_views` in channel list/detail UI).
- C1 (`/api/contracts/me` 422 — frontend still hits this before the
  `/api/contracts/` fallback).
- F1 user-side (`/disputes` route not mounted — chunk exists but not
  registered in router).
- Stage 4–7 items from the fix plan.

---

🔍 Verified against: 417b5f8d4ea49f88eaf6b8209a4faf55f2125b8a | 📅 Updated: 2026-04-19T00:00:00+03:00
