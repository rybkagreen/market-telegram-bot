# Next session — Phase 8.1 block D: API hardening

## What's already done this sprint

### Block A — Test harness (complete, 286 assertions passing per CI run)

| Suite                  | Tests | File                                          |
| ---------------------- | ----- | --------------------------------------------- |
| API contract (pytest)  | 76    | `tests/e2e_api/`                              |
| UI smoke (Playwright)  | 105   | `web_portal/tests/specs/smoke.spec.ts`        |
| Visual regression      | 105   | `web_portal/tests/specs/visual.spec.ts`       |

All run inside a single Docker compose (`docker-compose.test.yml`) with
fresh tmpfs Postgres/Redis, seeded users (advertiser tg=9001, owner 9002,
admin 9003) and deterministic fixtures. Baselines committed under
`web_portal/tests/visual-snapshots/`.

**Run:**
```bash
make test-e2e              # full suite (~10 min)
make test-e2e-api          # just pytest (~15 s)
make test-e2e-up           # stack up, iterate manually
make test-e2e-down         # teardown
make test-e2e-visual-update  # after intentional UI change
```

### Block B — Mobile row-layout pass (complete)

Three screens fixed (`MyCampaigns`, `OwnChannels`, `TransactionHistory`)
where an inner `<div className="flex gap-2">` blocked `ScreenHeader`'s
outer `flex-wrap` on 320px mobile. Rest of the 20+ ScreenHeader consumers
audited via fresh mobile baselines — no other overflow bugs.

### Bugs surfaced & fixed on the way (iter 1–4)

1. `MistralAIService()` instantiated at module-import time → crashed every
   environment without `MISTRAL_API_KEY`. Fixed with lazy `__getattr__`
   (`src/core/services/mistral_ai_service.py`).
2. Same pattern in `AnalyticsService.__init__` → `/api/analytics/*`
   returned 500. Fixed with `@property`-backed lazy init.
3. `GET /api/placements/?status=active` returned 500 (`ValueError: 'active'
   is not a valid PlacementStatus`). Fixed: router now accepts
   `active`/`completed`/`cancelled` aliases + concrete enum values;
   unknown → 400 not 500.
4. `src/api/main.py`: pyright noise (unused params, ORD shutdown
   narrowing).

---

## Start here — Block D: API hardening

**Goal:** catch the class of bugs that slipped through the new contract
suite. The surface area is all 15 routers — hunt down contract hazards and
pin them with tests.

### Priority tasks (suggested order)

#### D1. Grep remaining `Literal[...]` and `Enum` query params
The `status=active` 500 was a single instance of a broader issue: every
FastAPI query param typed as `Literal[...]`, `Enum`, or a strict type that
raises `ValueError` on parse failure will 500 when the frontend sends an
unexpected value. Find them all:
```bash
grep -rnE 'Annotated\[(Literal|.*Enum).*,\s*Query' src/api/routers/
grep -rnE 'Query.*regex=' src/api/routers/
```
For each hit, verify:
- Invalid value → 400/422, not 500
- Add an entry to `tests/e2e_api/test_query_params.py`

The `/api/billing/cashflow` endpoint was mentioned in prior work as another
likely suspect (was it fixed in S-47? check `CHANGELOG.md`).

#### D2. Response-model round-trip consistency
Every `response_model=` endpoint returns data the web_portal TS interfaces
consume. Hazards:
- `Decimal` sometimes serialized as `"123.45"` (string) vs `123.45`
  (number). Frontend must parse one way.
- `datetime | None` — dropped silently when None? Check Pydantic v2
  default behaviour.
- Union/discriminated types serialized consistently?

Pattern for a check: add to `tests/e2e_api/test_serialization.py`:
```python
async def test_placement_decimal_fields_serialized_as_strings(advertiser_client):
    resp = await advertiser_client.get("/api/placements/")
    for row in resp.json():
        assert isinstance(row["proposed_price"], str)  # or number — pick & pin
```

#### D3. 500-path envelope consistency
Grep for unhandled exceptions leaking to the wire. The existing
`rekharbor_error_handler` only catches `RekHarborError`. Confirm:
- generic exceptions land in a sanitized `{"detail": "Internal error"}`
  envelope, never a stack trace
- Sentry capture hooks still fire
- no PII leaks in error bodies (passport_series, etc. are scrubbed via
  `_SENTRY_PII_KEYS` in main.py — verify)

#### D4. Rate-limit audit
Which endpoints have `@limiter.limit(...)`? Expensive ones (Mistral AI
generation, OCR, file upload) must have it. Missing ones = DoS risk +
billing blast.
```bash
grep -rn "@_limit\|@limiter" src/api/routers/
```

### Definition of done for block D

- New test file `tests/e2e_api/test_query_params.py` extended (≥20 more
  parametrized cases for the other `Literal[]` / `Enum` query params).
- New test file `tests/e2e_api/test_serialization.py` (≥10 cases for
  Decimal / datetime / null-field consistency).
- Any 500 paths found → fixed (per standing directive).
- `make test-e2e` stays green.
- Write `reports/docs-architect/discovery/CHANGES_<date>_phase8-api-hardening.md`.
- Update `CHANGELOG.md` `[Unreleased]` with a new subsection.

---

## Project standing rules (don't re-derive)

- **Auto mode is on** → execute, don't plan; course-correct when user
  redirects.
- **Production-readiness directive**: during hardening work, fix all
  surfaced issues (Pyright, Ruff, latent bugs), not just in touched files.
  See `memory/feedback_fix_all_production_issues.md`.
- **After every code change**: `reports/docs-architect/discovery/CHANGES_*.md`
  + append to `CHANGELOG.md` `[Unreleased]`. Hooks enforce this.
- **Git flow**: `feat(scope): …` / `fix(scope): …` / `chore(scope): …`.
  Never `git add .`; group changes semantically.
- **Never touch** files listed in `CLAUDE.md` "NEVER TOUCH" section
  (field_encryption.py, audit_middleware.py, log_sanitizer.py,
  audit_log/legal_profile/contract/ord_registration models,
  db/migrations/versions/).
- **After src/ or web_portal/src/ change**: rebuild containers via
  `docker compose up -d --build nginx api` (not just `restart`).

## Uncommitted state at session start

A lot of work is staged/unstaged:
```
 M CHANGELOG.md
 M Makefile
 M src/api/main.py
 M src/api/routers/placements.py
 M src/core/services/analytics_service.py
 M src/core/services/mistral_ai_service.py
 M web_portal/src/screens/advertiser/MyCampaigns.tsx
 M web_portal/src/screens/common/TransactionHistory.tsx
 M web_portal/src/screens/owner/OwnChannels.tsx

?? .env.test.example
?? docker-compose.test.yml
?? docker/Dockerfile.api-contract
?? docker/Dockerfile.nginx-test
?? docker/Dockerfile.playwright
?? docker/entrypoint.playwright.sh
?? nginx/conf.d/test.conf
?? reports/docs-architect/discovery/CHANGES_2026-04-20_phase8-*.md
?? src/api/routers/auth_e2e.py
?? tests/e2e_api/
?? web_portal/tests/
```

**First action in new session**: commit this in semantic groups (not one
big commit). Suggested split:
1. `chore(test): add Dockerised E2E test harness` — compose, Dockerfiles,
   nginx conf, seed script, Makefile targets, .env.test.example, README.
2. `feat(api): e2e-login endpoint gated on ENVIRONMENT=testing` —
   `auth_e2e.py` + main.py mount.
3. `fix(api): lazy-init Mistral client in module + AnalyticsService` —
   mistral_ai_service.py + analytics_service.py.
4. `fix(api): placements status alias resolver (active/completed/cancelled)`
   — placements.py.
5. `test(api): add pytest contract suite` — tests/e2e_api/.
6. `test(ui): add Playwright smoke + visual regression suites` —
   web_portal/tests/ + visual-snapshots.
7. `fix(ui): mobile action-row wrap on 3 screens` — the 3 tsx diffs.
8. `docs: CHANGELOG + CHANGES_* for phase 8.1 iter 1–4`.
9. `chore(api): pyright cleanup in main.py` — main.py (can fold into #3).

After commits, continue with block D.

## Useful references

- Test harness runbook: `web_portal/tests/README.md` + `tests/e2e_api/README.md`
- Phase 8.1 change log: the four CHANGES_2026-04-20_phase8-*.md files
- Test fixtures:
  - `scripts/e2e/seed_e2e.py` — idempotent seed
  - `web_portal/tests/fixtures/roles.ts` — Playwright roles
  - `web_portal/tests/fixtures/routes.ts` — protected routes list
  - `tests/e2e_api/conftest.py` — role-based httpx clients

## Known gotchas

- Playwright version is pinned to `1.59.1` in both `tests/package.json`
  and the `Dockerfile.playwright` image tag. If you bump one, bump both —
  mismatch produces "browser not found" errors.
- The parent `tests/conftest.py` has heavy in-process DB fixtures that
  conflict with network-only E2E tests; the `tests/e2e_api/pytest.ini`
  standalone config sidesteps them — don't move fixtures between the two
  suites.
- Visual baselines are project-scoped (mobile-webkit, mobile-chromium,
  desktop-chromium). Font rendering differs across engines — never
  compare one project's screenshot against another's baseline.
- `tests/e2e_api/test_role_boundaries.py` uses a hand-maintained path
  list. When adding admin endpoints under `/api/admin/*`, append them to
  `ADMIN_ONLY_GETS`; the list pins the namespace convention so
  collisions with user routers trip the suite.
