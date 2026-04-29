# CHANGES — Acceptance infrastructure (15.9 / 5)

🔍 Verified against: `fix/acceptance-infrastructure` HEAD | 📅 Updated: 2026-04-29

## What

Third of 5+ prompt fee model consistency rewrite. **Re-acceptance loop at
`CONTRACT_TEMPLATE_VERSION` mismatch.**

After Промт 15.8 the templates and backend constants both say v1.1, but
`needs_accept_rules` only ran a truthy check on `User.platform_rules_accepted_at`,
so a user who accepted v1.0 was never re-prompted on the bump. This prompt
closes that loop end-to-end (backend → web_portal → mini_app → bot).

## Affected files

### Backend

- `src/db/repositories/contract_repo.py` — added `get_latest_acceptance` (status='signed', order by signed_at DESC).
- `src/core/services/contract_service.py`:
  - **new** `needs_accept_rules(user_id)` — version-aware (4a→4c, read-only).
  - **fix** `accept_platform_rules(user_id)` UPDATE branch now refreshes
    `template_version` (was a silent bug pre-15.9). Sub-stages 5a→5e.
- `src/api/routers/users.py` — `GET /api/users/needs-accept-rules` now wires
  to `ContractService.needs_accept_rules`. Added `NeedsAcceptRulesResponse`
  Pydantic schema (`{needs_accept: bool}`, `frozen=True`).
- `src/bot/middlewares/acceptance_middleware.py` (**new**) — blocks bot
  interaction with accept prompt when `needs_accept_rules` True. Sub-stages
  10a→10d. Fail-open on DB errors. Exempt patterns: `/start`, `terms:*`
  callbacks, `contract:accept_rules` callback.
- `src/bot/main.py` — `AcceptanceMiddleware` registered after
  `RoleCheckMiddleware`, before `FSMTimeoutMiddleware`.

### Frontend (web_portal)

- `web_portal/src/hooks/useUserQueries.ts` — `useNeedsAcceptRules` staleTime
  5min → 0 + `refetchOnWindowFocus: true`.
- `web_portal/src/components/guards/RulesGuard.tsx` — now reads
  `useNeedsAcceptRules` (was `useMe` truthy check).
- `web_portal/src/components/layout/PortalShell.tsx` — removed redundant
  accept-rules banner (RulesGuard hard redirect is the single gate now).
- `web_portal/src/hooks/useContractQueries.ts` — `useAcceptRules` invalidates
  `['user', 'needs-accept-rules']` and `['user', 'me']` on success.

### Frontend (mini_app)

- `mini_app/src/api/users.ts` — added `checkNeedsAcceptRules`.
- `mini_app/src/hooks/queries/useUserQueries.ts` — added `useNeedsAcceptRules`
  (staleTime: 0, refetchOnWindowFocus: true).
- `mini_app/src/components/RulesGuard.tsx` — switched from `useMe` truthy
  check to version-aware `useNeedsAcceptRules`.
- `mini_app/src/hooks/useLegalAcceptance.ts` — `useAcceptRules` invalidates
  `['user', 'needs-accept-rules']` after accept.

### Tests (new)

- `tests/integration/test_acceptance_flow.py` (5 tests):
  - `test_needs_accept_rules_true_for_new_user`.
  - `test_needs_accept_rules_false_for_current_version`.
  - `test_needs_accept_rules_true_for_old_version`.
  - `test_accept_platform_rules_atomic_update`.
  - `test_version_bump_forces_re_accept` (monkeypatches the constant,
    verifies re-accept stamps the bumped version).
- `tests/integration/test_needs_accept_rules_endpoint.py` (1 test):
  - `test_needs_accept_rules_endpoint_returns_true_for_new_user` —
    exercises ASGI client with `app.dependency_overrides` for both
    `get_db_session` and `get_current_user`.

### Docs

- `reports/docs-architect/BACKLOG.md` — added BL-039.
- `CHANGELOG.md` — `[Unreleased]` entry under feat(legal).

## Public contract delta

- **Modified:** `GET /api/users/needs-accept-rules`
  - Response shape unchanged: `{needs_accept: bool}`.
  - Result semantics: was `User.platform_rules_accepted_at is None`, now
    True if no signed acceptance OR
    `latest.template_version != CONTRACT_TEMPLATE_VERSION`.
- **Existing:** `POST /api/contracts/accept-rules` — internal upgrade
  (atomic 5-stage flow, UPDATE branch refreshes `template_version`);
  response shape unchanged.

## Sub-stage tracking (BL-037 first applied)

`accept_platform_rules`:

- 5a. Capture `now()` + current `CONTRACT_TEMPLATE_VERSION`.
- 5b. Upsert authoritative `platform_rules` Contract row (signed,
  `template_version=current`).
- 5c. Mirror onto legacy `privacy_policy` row if present.
- 5d. Sync denormalized `User.platform_rules_accepted_at` cache.
- 5e. Flush; caller commits.

`needs_accept_rules`:

- 4a. Fetch latest signed acceptance.
- 4b. None → True.
- 4c. Version compare → True/False.

Bot `AcceptanceMiddleware`:

- 10a. Extract `event_from_user.id`.
- 10b. DB user lookup; new users (no record) pass through to onboarding.
- 10c. Call service; fail-open on exception (logged).
- 10d. If blocking, send accept prompt; return without invoking handler.

## Critical operational notes

- DB пустая, no real users → impact zero on deploy.
- Bot middleware **fail-open**: if `needs_accept_rules` raises (DB
  unavailable, etc.), user is *not* blocked. Surfaced finding for Marina:
  prod may prefer fail-closed (safer) over the current fail-open (robust
  to transient infra glitches).
- `/api/contracts/platform-rules/text` carve-out comment **not added** —
  15.10 territory per plan.
- Frontend `mini_app/src/screens/advertiser/TopUpConfirm.tsx:66` still
  hardcodes 0.035 — 15.10.

## Gate baseline (pre → post)

| Gate | Pre | Post |
|------|-----|------|
| Forbidden-patterns | 17/17 | 17/17 |
| Ruff `src/` | 21 (ceiling) | 21 (ceiling) |
| Mypy errors | 10 | 10 |
| Pytest substantive | 76F + 17E + 655P | 76F + 17E + **661P** (+6 new) |

## Drift from plan (Шаг 0 outcome)

- `Contract.template_version` field already existed (default "1.0",
  server_default "1.0") — Шаг 2 skipped per плану.
- `User.platform_rules_accepted_at` + `privacy_policy_accepted_at`
  already existed.
- `accept_platform_rules` already mostly atomic (Contract upsert + User
  cache sync); only the UPDATE branch missed `template_version` refresh —
  fixed точечно.
- Web_portal `RulesGuard` already wired into App.tsx route tree but used
  `useMe` truthy check — switched to version-aware hook.
- Mini_app `RulesGuard` similar — switched to version-aware hook.
- Bot middleware was the only fully greenfield surface (no prior
  acceptance gate in bot).

## Surfaced findings

- **Bot middleware fail-open vs fail-closed.** Current behaviour: DB
  failure → user proceeds. Documented for Marina decision; default
  pre-launch is fail-open to avoid lockout under transient errors, but
  prod may want to flip once an alerting story is in place.
- **Pre-existing pyright/mypy diagnostics** (act_service.py, contract_service.py,
  users.py:121) surfaced during the session but are part of the
  documented 529-error baseline — not in scope per "Не while-we're-here
  фиксы" and the 10-error mypy ceiling held.

## Origins

- `PLAN_centralized_fee_model_consistency.md`.
- BL-038 (15.8) closing caveat: "Re-acceptance loop при version bump НЕ
  active в этом промте — Полная реализация — Промт 15.9."

## Next prompt — 15.10

Frontend `/fee-config` consumption + TopUpConfirm.tsx:66 hardcode fix +
extend grep-guard на TS literals + inline comment in `/contracts/platform-rules/text`
route per Phase 1 carve-out.
