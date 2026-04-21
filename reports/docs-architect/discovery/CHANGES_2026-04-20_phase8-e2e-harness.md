# CHANGES — Phase 8.1 hardening, iteration 1: Dockerised E2E test harness

Kicks off the hardening sprint after S-47 merge. Installs a full-stack
Playwright harness that runs against a production-like container runtime,
plus fixes three production-readiness blockers the harness surfaced on its
first run.

## Files added

### Test infrastructure
- `docker-compose.test.yml` — isolated test stack (postgres-test, redis-test,
  seed-test, api-test, nginx-test, playwright). Uses tmpfs volumes so
  teardown is instant and never leaks data into dev.
- `docker/Dockerfile.nginx-test` — portal-only nginx image on port 80, no
  SSL. Serves `web_portal/dist` and proxies `/api/` to api-test.
- `docker/Dockerfile.playwright` — Microsoft Playwright runner image pinned
  to `v1.59.1-jammy` (matches `@playwright/test` 1.59.1 in tests/package.json
  — mismatched versions fail loudly with "browser not found").
- `docker/entrypoint.playwright.sh` — waits for nginx-test and api-test
  health before starting the suite.
- `nginx/conf.d/test.conf` — minimal test-only nginx config, listens on 80,
  no TLS.
- `scripts/e2e/seed_e2e.py` — idempotent fixture loader. Creates 3 users
  (advertiser TG 9001, owner TG 9002, admin TG 9003), one channel, two
  placements (pending_owner + published).
- `.env.test` + `.env.test.example` — test-stack-only secrets (fake JWT /
  encryption keys). Never reused in dev/prod.

### Playwright suite
- `web_portal/tests/package.json` — isolated from app package.json; declares
  `@playwright/test@1.59.1`, `@axe-core/playwright@^4.10.2`,
  `@types/node@^22`.
- `web_portal/tests/tsconfig.json`
- `web_portal/tests/playwright.config.ts` — 3 projects (mobile-webkit /
  mobile-chromium / desktop-chromium), single-worker, retain-on-failure
  traces, reports to `/e2e/reports` (→ host `reports/e2e/`).
- `web_portal/tests/global-setup.ts` — calls `POST /api/auth/e2e-login` once
  per role, writes JWT into Playwright storageState files under
  `tests/.auth/` (gitignored).
- `web_portal/tests/fixtures/roles.ts`, `fixtures/routes.ts` — route-sweep
  targets derived from `src/App.tsx`.
- `web_portal/tests/specs/smoke.spec.ts` — for every protected route × 3
  viewports: HTTP 200, ≤1 breadcrumbs, no horizontal overflow, no external
  sprite refs, no uncaught client errors, axe-core WCAG AA baseline
  (informational).
- `web_portal/tests/README.md` — runbook.
- `web_portal/tests/.gitignore`

### Makefile
- New targets: `test-e2e` (one-shot full run + teardown, exit code =
  Playwright exit code), `test-e2e-up` / `test-e2e-down` / `test-e2e-logs`
  for iterative development.

### E2E auth endpoint (test-only)
- `src/api/routers/auth_e2e.py` — `POST /api/auth/e2e-login { telegram_id }`
  → JWT. Skips Telegram signature / OTP flows.
- `src/api/main.py` — **mounts the router only when
  `settings.environment == "testing"`**, with a warning log line. Never
  exposed in dev/staging/prod.

## Public contract changes

### NEW: `POST /api/auth/e2e-login` (testing environment only)
Request: `{ "telegram_id": int }` →
Response: `{ access_token, token_type, user }`. 404 if the user isn't in
the seed. Gated on `ENVIRONMENT=testing` at router mount time.

### CHANGED: `GET /api/placements/?status=…`
Previously crashed with HTTP 500 (`ValueError: 'active' is not a valid
PlacementStatus`) if the client sent a status value that wasn't a literal
enum member. Now accepts three semantic aliases matching the frontend UI
groupings:

| alias     | expands to                                                    |
| --------- | ------------------------------------------------------------- |
| active    | pending_owner, counter_offer, pending_payment, escrow          |
| completed | published                                                      |
| cancelled | cancelled, refunded, failed, failed_permissions                |

Concrete enum values (`pending_owner`, etc.) still work. Unknown values
return HTTP 400 with the allowed list — never 500. The same alias table is
applied for `view=advertiser`, `view=owner`, and the default union query.

Caller-visible: `Sidebar.tsx` call
`useMyPlacements('advertiser', 'active')` now succeeds; previously it 500'd
and painted two console.error lines on every advertiser-role route, which
was the first bug the new E2E suite caught.

## Internal behaviour changes

### `src/core/services/mistral_ai_service.py` — lazy singletons
Module-level `mistral_ai_service = MistralAIService()` (plus `ai_service` /
`admin_ai_service` aliases) triggered import-time `RuntimeError` when
`MISTRAL_API_KEY` was absent — breaking any environment without a real
Mistral key (tests, CI, smoke containers). Replaced with module `__getattr__`
so the same three names are lazy: construction still raises the same error
on first *use*, but imports never fail. Consumer imports unchanged.

### `src/api/main.py` — minor cleanups touched while adding the e2e mount
- `lifespan(_app)` / `rekharbor_error_handler(_request, ...)` — underscore
  unused params (pyright).
- ORD provider shutdown: replaced brittle `await provider.close()` (pyright
  couldn't narrow `getattr`'d `close`) with `inspect.isawaitable` guard.
  Runtime behaviour identical.

## What the harness caught on the first run

1. **Bootstrap crash** — api-test wouldn't start without `MISTRAL_API_KEY`
   because of eager module-level instantiation. Fixed (lazy singletons).
2. **/api/placements 500** — `status=active` → `ValueError`. Fixed
   (alias resolver in the router).

Both were latent production bugs; neither had automated coverage before
this change.

## Regression surface

- Pre-existing prod stack unchanged: `docker-compose.yml`, `.env`,
  `nginx/conf.d/default.conf` are not touched.
- `auth_e2e` router fails closed — missing `ENVIRONMENT=testing` means the
  router isn't even imported, so the `/api/auth/e2e-login` route doesn't
  exist (404 via FastAPI default handler).
- The alias table is additive (previous concrete-status requests still
  behave identically).

## Runbook

One-shot:

```bash
make test-e2e
```

Iterative local:

```bash
make test-e2e-up
docker compose -p e2e -f docker-compose.test.yml --env-file .env.test \
    run --rm playwright npx playwright test --project=desktop-chromium
make test-e2e-down
```

Reports land in `reports/e2e/` (html, results.json, artifacts).

## Known limitations

- Single-worker Playwright — seed isn't reset between tests, so specs must
  stay read-only or reset their own state.
- webkit in container is not identical to iOS Safari — true device
  verification still manual.
- Admin screens reach `200` but their data-heavy paths are not yet exercised
  (axe violations logged only).

---
🔍 Verified against: f158495..HEAD | 📅 Updated: 2026-04-20T12:00:00+03:00
