# Research: 17.3 — Credits API + FE TS interfaces inventory

**Date:** 2026-05-01
**Scope:** read-only inventory, no mutations
**Branch:** develop @ `4d853f3` (post BL-071)

## Executive summary

Inventory surfaces **3 backend URL paths** containing `/credits`, **0 backend
Pydantic schemas with "Credit"** in the name, and **3 FE TS interfaces**
(`BuyCreditsResponse`, `PlatformCreditResponse`, `GamificationBonusResponse`)
with matching hardcoded URL strings.

**Critical surprise:** 17.2 «persisted credits sweep» left a substantial
residue beyond URL paths — namely `User.credits` (model field), `UserResponse.credits`
(Pydantic schema), `Badge.credits_reward` (model field + 12 seed_badges
entries), 5 mirroring TS `User.credits: number` fields, and 2 likely runtime
bugs in `notification_tasks.py` / `billing_tasks.py` that read `user.credits`
where they should read `user.balance_rub`. Scope of 17.3 as originally framed
(URL + FE interfaces only) is **insufficient** to remove the term — full
de-credits requires either 17.2 reopen or 17.3 expansion.

Test impact: 6 pytest files mention "credit"; 1 contract snapshot
(`user_response.json`) carries the `credits` field; 1 stale assertion in
`test_gamification.py` asserts a key (`credits_awarded`) the service no
longer returns (`balance_rub_awarded`).

## Backend findings

### Endpoints with `/credits` URL or Credit response

All 3 endpoints return **plain `dict`** — no Pydantic response schema.

| Method | URL | File:line | Function | Body schema | Semantics |
|---|---|---|---|---|---|
| POST | `/billing/credits` | `src/api/routers/billing.py:561` | `buy_credits()` | `TopupRequest` | Pays for a plan from `balance_rub`. Docstring: «Оплатить тариф с рублёвого баланса (кредиты удалены, единая валюта ₽)». URL noun "credits" is a misnomer post-migration. |
| POST | `/admin/credits/platform-credit` | `src/api/routers/admin.py:834` | `create_admin_grant()` | `AdminGrantRequest` | Admin grants money from `PlatformAccount.profit_accumulated` to `user.balance_rub`. |
| POST | `/admin/credits/gamification-bonus` | `src/api/routers/admin.py:890` | `create_gamification_bonus()` | `GamificationBonusRequest` | Admin gives gamification bonus (₽ amount + XP) from `profit_accumulated`. |

**Mini-finding:** `POST /billing/credits` is consumed by **only** `useBuyCredits`
in `mini_app/src/hooks/queries/useBillingQueries.ts:33`, which is **not
imported by any screen** in `mini_app/`. Endpoint may be dead in practice —
verify before rename, candidate for removal.

### Schemas with "Credit" naming

`grep -rn "class.*Credit" src/api/schemas/ src/core/ src/` → **0 matches.**

Conclusion: no Pydantic class names contain "Credit". The 3 endpoints above
return `dict[str, Any]`, not typed responses. Naming decision is
TS-side-only on the response side.

### Residual `credits` (post-17.2 check)

17.2 was scoped as «persisted credits sweep (meta_json keys, enum values,
schemas)». The following persists on `develop @ 4d853f3` and was clearly
not in 17.2's scope catalogue:

#### A. Currency residue — model + schema fields

| File:line | Token | Type |
|---|---|---|
| `src/db/models/user.py:69` | `credits: Mapped[int]` | SQLAlchemy column on `User` |
| `src/db/models/badge.py:47` | `credits_reward: Mapped[int]` | SQLAlchemy column on `Badge` |
| `src/api/schemas/user.py:25` | `credits: int = 0` | Pydantic field on `UserResponse` |
| `src/db/migrations/versions/0001_initial_schema.py:54` | `sa.Column("credits", sa.Integer(), ...)` | DB column (initial schema, immutable per CLAUDE.md migration rule until first prod user) |

#### B. Currency residue — populating callsites

| File:line | Token |
|---|---|
| `src/api/routers/auth.py:252` | `credits=user.credits` (LoginResponse builder) |
| `src/api/routers/auth.py:553` | `credits=current_user.credits` (`/me`) |
| `src/api/routers/users.py:136` | `credits=current_user.credits` (`/users/me`) |

#### C. Likely runtime bugs (read `user.credits` where `balance_rub` is meant)

These are **not just naming** — they show stale value in user-facing
messages. Worth surfacing as objections, not deferred:

| File:line | Code | Why suspicious |
|---|---|---|
| `src/tasks/notification_tasks.py:1231` | `f"Текущий баланс: {user.credits} ₽\n\n"` | Says «Текущий баланс» but reads `.credits` (defaulted to 0). Real balance lives on `.balance_rub`. |
| `src/tasks/billing_tasks.py:138` | `f"Недостаточно кредитов для продления (нужно {plan_cost}, было {user.credits})"` | Plan-extension insufficient-funds message references `.credits`; charge actually deducts from `.balance_rub`. |

#### D. Badge reward currency

| File:line | Token |
|---|---|
| `src/db/seed_badges.py:32-178` | 12 seed entries with `"credits_reward":` |
| `src/tasks/badge_tasks.py:46, 194, 219, 229, 244, 245` | Reads `Badge.credits_reward`; user message `f"+{credits_reward} кр\n"` |
| `src/core/services/badge_service.py:193, 194, 385` | Computes `reward_amount = Decimal(str(badge.credits_reward))`; serializes `"credits_reward": badge.credits_reward` |

#### E. Comment / docstring residue (low priority, not bugs)

- `src/api/routers/billing.py:684` — comment "credit balance"
- `src/constants/legal.py:3-4` — header docstring referencing legacy
- `src/core/services/yookassa_service.py:117` — docstring "credits (int rubles for YooKassa metadata)"
- `src/core/services/billing_service.py:175, 1001` — log strings "credited" / "Admin credit"
- `src/api/routers/admin.py:871` — log string "credited"

#### F. Semantic verb usage — NOT residue

| Token | File:line | Note |
|---|---|---|
| `admin_credit_from_platform` | `src/core/services/billing_service.py:939` | "credit" as verb (зачислить); should NOT be renamed during a noun-cleanup. |

## Frontend findings

### TS interfaces with "Credit" in name

| Name | File:line | Fields | Used by |
|---|---|---|---|
| `BuyCreditsResponse` | `mini_app/src/api/billing.ts:87` | `{ amount_rub: number }` | `buyCredits()` (api), `useBuyCredits` hook (`mini_app/src/hooks/queries/useBillingQueries.ts:33`) — hook **orphan**, no screen consumer. |
| `PlatformCreditResponse` | `web_portal/src/api/admin.ts:82` | `{ success: boolean; transaction_id: number; new_platform_balance: string; new_user_balance: string }` | `createPlatformCredit()` api fn → `useCreatePlatformCredit` hook (`web_portal/src/hooks/useAdminQueries.ts:104`) → `web_portal/src/screens/admin/AdminUserDetail.tsx:39`. |
| `GamificationBonusResponse extends PlatformCreditResponse` | `web_portal/src/api/admin.ts:97` | adds `{ new_user_xp: number }` | `createGamificationBonus()` api fn → `useCreateGamificationBonus` hook (`web_portal/src/hooks/useAdminQueries.ts:156`) → `web_portal/src/screens/admin/AdminUserDetail.tsx:47`. |

#### Rename options for `PlatformCreditResponse`

- **(a) `PlatformGrantResponse`** — emphasises admin-driven grant action.
  Pairs cleanly with backend body schema `AdminGrantRequest`. Removes
  "credit" entirely.
  *Trade-off:* loses the "credit" verb continuity with service method
  `admin_credit_from_platform` (which we keep as legitimate verb usage).
- **(b) `AdminBalanceCreditResponse`** — preserves "credit" as a verb
  (= зачисление), explicit about target field (`balance_rub`).
  *Trade-off:* longer; "credit" verb may still confuse a reader given
  the codebase-wide `credits → balance_rub` migration just happened.
- **(c) Keep TS name, rename URL only** — minimal-risk option, but leaves
  TS reader looking at `PlatformCreditResponse` for an endpoint named
  `/admin/grants/...`. Inconsistent.

#### Rename options for `GamificationBonusResponse`

- Already has clean name. If parent renames to `PlatformGrantResponse`
  it must rename its `extends` clause; otherwise no action needed.

#### Rename options for `BuyCreditsResponse`

Conditional on the orphan-hook decision (see Open question 5):
- **(a) Drop entirely** — if `POST /billing/credits` is removed.
- **(b) `PlanPurchaseResponse`** — if endpoint kept and rebranded as
  plan-from-balance charge.
- **(c) Keep name, rename URL only** — same inconsistency as PlatformCredit case.

### Hardcoded URL strings

| URL | File:line |
|---|---|
| `'admin/credits/platform-credit'` | `web_portal/src/api/admin.ts:94` |
| `'admin/credits/gamification-bonus'` | `web_portal/src/api/admin.ts:108` |
| `'billing/credits'` | `mini_app/src/api/billing.ts:92` |

All 3 are inside api-modules (correct per CLAUDE.md screen→hook→api rule
§API Conventions FIX_PLAN_06 §6.7). No leaks into screens / hooks.

### Residual TS variable / state usage (post-17.x sweep)

`User.credits: number` field in TS types **5 places** (mirrors backend
`UserResponse.credits` survival):

| File:line | Interface |
|---|---|
| `web_portal/src/lib/types.ts:23` | `User` |
| `web_portal/src/lib/types/user.ts:13` | `User` |
| `web_portal/src/lib/types/user.ts:44` | `UserAdminResponse` |
| `mini_app/src/lib/types.ts:65` | `User` |
| `mini_app/src/lib/types.ts:417` | `UserAdminResponse` |

Grep `user.credits` / `state.credits` in screen / component code → **0 matches.**
The field is only declared, never read. Dropping it on backend will cause
no FE runtime regression.

## Test impact estimate

6 pytest files reference "credit"; 1 snapshot carries the field:

| File | Mentions | Impact |
|---|---|---|
| `tests/integration/test_payout_concurrent.py` | 1 (comment) | None — comment only. |
| `tests/integration/test_billing_hotfix_bundle.py` | 6 (variables + comments: "manual credit for support", "credited only once") | Variables and string literals; semantic ("credit" verb). Update on language preference, not behavioural break. |
| `tests/unit/test_no_dead_methods.py` | 2 (string literals `refund_escrow_credits`, `_credit_user`) | Verifies dead methods stay dead — keep references. |
| `tests/unit/test_contract_template_version.py` | 2 (`test_platform_rules_template_uses_rubles_not_credits` — guards against "кредит" in legal HTML) | Behavioural — LEAVE INTACT (this is the guard that backs the de-credits initiative). |
| `tests/unit/test_gamification.py` | 4 (`assert result["credits_awarded"] == ...`) | **STALE — see Objection 1.** Currently asserts a key the service no longer returns (`balance_rub_awarded` is what `xp_service.award_streak_bonus` returns at `src/core/services/xp_service.py:556`). |
| `tests/unit/snapshots/user_response.json:23` | 1 (snapshot field) | Will need regeneration when `UserResponse.credits` drops. |

FE tests: `grep '/credits'` in `web_portal/tests/` and `mini_app/tests/` → 0
matches. URL renames need no FE test rewrites.

## Возражения и риски

**1. (BUG) `tests/unit/test_gamification.py` lines 51, 57, 63, 69 assert against
key `result["credits_awarded"]` but `xp_service.award_streak_bonus`
returns `balance_rub_awarded` (xp_service.py:556).**

Either the test was never re-run after a prior dict-key migration, or the
service method silently regressed and the test catches a `KeyError` no
one noticed. This is an active drift between test and code — should be
investigated and fixed during 17.3, not deferred. (Separate from rename
work, but adjacent enough that splitting it out adds friction.)

**2. (BUG) `src/tasks/notification_tasks.py:1231` and
`src/tasks/billing_tasks.py:138` read `user.credits` in user-facing
messages where the intended value is `user.balance_rub`.**

Since `user.credits` defaults to 0 and is never written anywhere
post-migration, both messages display `0 ₽` regardless of the actual
balance. Notification reads «Текущий баланс: 0 ₽» for any user who has
funds; plan-extension insufficient-funds message says «было 0». These
are silently broken in production today. They must be fixed regardless
of rename — recommend rolling them into 17.3 since the field they
reference will be dropped.

**3. (Scope contradiction) 17.3 as scoped (URL + FE TS interfaces) does not
remove "credits" from the codebase.**

After 17.3 lands as currently scoped, the User table still has a
`credits` column, `UserResponse` still has a `credits` field, FE
`User` still has `credits: number`, badges still award `credits_reward`,
and seed data still ships `"credits_reward":` keys. URL rename without
field rename is cosmetic, not a deprecation step.

Recommendation: explicitly choose between (a) **expand 17.3 scope** to
include field drops + bug fixes (single atomic merge), or (b) **make
17.3 URL+TS-only** and immediately follow with **17.3b: residue field
drop** as a separate planned phase. Either is fine; **silently
shipping 17.3 URL-only** with the residue intact ships a
pseudo-completion that 17.4 / future audit will re-discover.

**4. (Decision blocker) `POST /billing/credits` may be a dead endpoint.**

Code-path consumer = `useBuyCredits` hook with **0 screen consumers**
in `mini_app/`. Suggests the endpoint is unused. If true, removing it
is cleaner than renaming it. Marina decision needed before naming.

**5. (Naming sensitivity) `admin_credit_from_platform` keeps "credit" as verb.**

Tracking explicitly to make sure the rename plan does not greedily rename
this method. The verb «credit» (= зачислить) is a legitimate accounting
term and shows up in log messages too. Same goes for "credited" in
`tests/integration/test_payout_concurrent.py:250` comment and
`test_billing_hotfix_bundle.py` — those are semantic, not currency.

## Suggested atomic merge structure

**Recommended: split into 3 commits** (or, equivalently, 3 PRs depending
on review preference). Single-commit version is too large and mixes
distinct concerns.

- **Commit 1 — 17.3a (fix bugs + drop residue field).** Drops `User.credits`
  + `UserResponse.credits` + `Badge.credits_reward`; renames seed keys;
  fixes `notification_tasks.py:1231` + `billing_tasks.py:138` to use
  `balance_rub`; fixes `test_gamification.py` assertions; regenerates
  `user_response.json` snapshot. Edits to `0001_initial_schema.py` (drop
  the `credits` Column) per CLAUDE.md migration policy («edit initial
  schema until first prod user»). FE: drops `credits: number` from 5 TS
  interfaces.
  *This is technically completing 17.2 — the URL rename downstream
  becomes meaningful only after this lands.*

- **Commit 2 — 17.3b (URL renames + body schema renames).** Renames
  `/billing/credits` → `/billing/plan-purchase` (or removes if dead per
  Q4); renames `/admin/credits/platform-credit` → `/admin/grants/...`
  (or chosen alternative); renames TS API call URLs; updates router
  inclusion / `prefix=`. **Backend body schemas (`AdminGrantRequest`,
  `GamificationBonusRequest`, `TopupRequest`) need no rename** — they
  already lack "Credit".

- **Commit 3 — 17.3c (FE TS interface renames).** Renames
  `PlatformCreditResponse` / `GamificationBonusResponse` /
  `BuyCreditsResponse`. Updates hook + screen imports. Touches
  `web_portal/src/screens/admin/AdminUserDetail.tsx`.

**Why split:** commit 1 is bug-fix-heavy; commit 2 is URL rename
(reviewer needs to confirm no external callers are broken); commit 3
is FE-only style. Bisecting a regression after a single mega-commit
becomes painful.

**If Marina prefers single commit:** acceptable if no external API
consumers — frontends re-deploy together with backend, and there's no
3rd-party SDK against `/admin/credits/*`. But CHANGES_*.md must list
all 3 layers explicitly.

## Open questions for Marina

1. **Scope of 17.3.** Is this URL+TS-only, or does it absorb the 17.2
   sweep gap (drop `User.credits`, `UserResponse.credits`,
   `Badge.credits_reward`, fix the 2 user-facing-message bugs)? If
   URL-only, schedule a separate phase before "credits" can be claimed
   gone.
2. **`POST /billing/credits` fate.** Verify with a `git log -S buyCredits`
   / runtime usage check whether this is dead code. If dead → drop;
   if live → rename to `/billing/plan-purchase` (or
   `/billing/charge-balance`).
3. **Admin URL convention.** Pick one:
   - **(a)** Resource-oriented: `POST /admin/users/{id}/grants` +
     `POST /admin/users/{id}/gamification-bonus`. Most RESTful.
   - **(b)** Action-oriented under existing admin namespace:
     `POST /admin/grants/platform` + `POST /admin/grants/gamification`.
     Closest to current shape.
   - **(c)** Singular: `POST /admin/grant` taking a `kind: "platform" |
     "gamification"` enum + the union body. Tightens API surface.
4. **`Badge.credits_reward` rename target.** Pick one:
   - `balance_rub_reward` (consistent with `balance_rub`).
   - `bonus_amount` (cleaner, no currency repetition).
   - Other.
5. **TS interface renames.** For `PlatformCreditResponse`, prefer
   `PlatformGrantResponse` (drops "credit") or `AdminBalanceCreditResponse`
   (keeps verb)? Affects 2 hook names + 2 screen imports.

🔍 Verified against: `4d853f3` | 📅 Updated: 2026-05-01T00:00:00Z
