# CHANGES — Phase 8.1 hardening, iteration 2: API contract test suite

Adds a pytest-based API contract suite that runs inside the existing
`docker-compose.test.yml` stack, alongside Playwright. Same runtime, same
seed data, different assertion style — pytest + httpx rather than browser
automation. Surfaces a different class of bugs (500s on internal endpoints,
missing auth gates, privilege-escalation paths) than the Playwright route
sweep does.

## Files added

- `tests/e2e_api/__init__.py`
- `tests/e2e_api/conftest.py` — role fixtures (`anonymous_client`,
  `advertiser_client`, `owner_client`, `admin_client`). Each role calls
  `/api/auth/e2e-login` once at fixture setup and caches a JWT-bearing
  httpx.AsyncClient.
- `tests/e2e_api/pytest.ini` — standalone config. Critical: parent
  `tests/conftest.py` wires heavy in-process DB fixtures (test_engine,
  db_session, a custom event_loop that conflicts with pytest-asyncio auto
  mode) that these network-level tests don't need and that break when the
  DB isn't reachable from the runner container. Standalone config sidesteps
  the parent.
- `tests/e2e_api/test_auth.py` — `/auth/me` 200/401, `/auth/e2e-login`
  stability per telegram_id, admin-flag leak guard.
- `tests/e2e_api/test_query_params.py` — pins the `status=active` alias
  fix from iteration 1 + sibling aliases; exhaustive parameterization
  across every `PlacementStatus` enum value; pagination edge cases
  (`limit=0`, `limit=101`, `limit=abc`, `offset=-1`) → 422 not 500.
- `tests/e2e_api/test_role_boundaries.py` — 3-list path sweep:
  `PUBLIC_GETS` (intentionally-open endpoints), `COMMON_AUTHENTICATED_GETS`
  (401 unauth, 200 authed), `ADMIN_ONLY_GETS` (401/403 for non-admin, 200
  for admin). Never 500 anywhere.
- `tests/e2e_api/README.md` — runbook.
- `docker/Dockerfile.api-contract` — separate image that installs
  `--with dev` (pytest + friends). Existing `Dockerfile.api` uses
  `--only main`, so pytest isn't present.

## Files changed

- `docker-compose.test.yml` — new `api-contract` service. Shares network
  with playwright; depends on `nginx-test` healthy; writes JUnit XML to
  `reports/e2e/`.
- `Makefile` — new targets `test-e2e-api` (pytest only) and updated
  `test-e2e` (runs API contract then Playwright back-to-back in one stack
  bring-up, tears down at end). Exit code non-zero if either suite fails.
- `src/core/services/analytics_service.py` — `AnalyticsService.__init__`
  no longer eagerly builds `MistralAIService()`. The Mistral client is
  now lazy-initialized via a `@property` that constructs on first
  `self.ai_service.generate(...)` call. Matches the lazy pattern in
  `mistral_ai_service.py` (iteration 1). This fixes **every** analytics
  endpoint (`/api/analytics/summary`, `/activity`, `/cashflow`, …) which
  previously 500'd in any environment without `MISTRAL_API_KEY`.

## What the suite caught on the first run

76 tests, 6 failures revealed real issues:

1. **`/api/analytics/summary` 500 for any authed user.** `AnalyticsService()`
   eagerly instantiated `MistralAIService()` in its `__init__`. Same bug
   class as iteration 1's module-level `mistral_ai_service` eager instance
   — fixed identically (lazy construction). Production impact: analytics
   summary crashed in any environment without MISTRAL_API_KEY, including
   staging.
2. **`/api/billing/plans` serves unauthenticated.** My initial test list
   was wrong — this *is* a public pricing endpoint. Re-classified into a
   new `PUBLIC_GETS` list with an explicit "must serve 200 unauth" test
   so any accidental auth gate in the future trips the suite.
3. **`/api/categories/` serves unauthenticated.** Same — public category
   dropdown. Same treatment.
4. **Test list used wrong admin paths.** I had `/api/contracts`,
   `/api/payouts`, etc. as admin endpoints. Actual admin router mounts at
   `/api/admin/*` (admin_router has `prefix="/admin"` + main.py's
   `prefix="/api"`). Updated `ADMIN_ONLY_GETS` to the real paths. This
   also pins the namespace convention — if someone later adds an admin
   endpoint directly at `/api/contracts` it'd collide with the user
   contracts router; the test list documents the namespace.
5. **`/api/admin/tax/summary` returns 422 for admin** — endpoint has
   required `year` and `quarter` query params. 422 confirms the handler
   lives; expanded `test_admin_paths_accept_admin` to accept 422 in
   addition to 2xx/404 (reject only 5xx and auth-related codes).

All 76 tests pass after the fix. Full `make test-e2e` runs API contract
+ Playwright UI suites end-to-end without manual intervention.

## Public contract changes

No new endpoints. Existing contracts hardened (no more 500s on
`/api/analytics/*` in missing-API-key environments).

## Internal notes

- `AnalyticsService.ai_service` is now a `@property` rather than an
  attribute. External code that imports the class and sets
  `service.ai_service = mock_instance` will fail with AttributeError.
  There are no such callers in the repo today (verified via grep).
- `Dockerfile.api-contract` includes all dev-group deps. It is **not**
  used in prod — prod uses `Dockerfile.api` (`--only main`). Attack
  surface unchanged.

## Regression surface

- Full `make test-e2e`: 76 API contract + 105 Playwright UI = 181 assertions
  pinning the current contract.
- Both suites run in the same compose stack. Extending either is
  incremental: add a route to `routes.ts` (UI) or a path to
  `COMMON_AUTHENTICATED_GETS` (API) and the harness picks it up.

---
🔍 Verified against: f158495..HEAD | 📅 Updated: 2026-04-20T12:15:00+03:00
