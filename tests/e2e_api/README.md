# E2E API contract tests

Pytest suite that hits the same Docker-based runtime as the Playwright UI
suite (postgres-test + redis-test + seed-test + api-test + nginx-test) and
asserts backend contracts:

- auth / session behaviour per role (advertiser / owner / admin / anonymous)
- query-parameter coercion, including the enum-alias class of bugs
- role boundaries across all 15 routers (200 for the owning role, 401 for
  unauthenticated, 403 for insufficient privilege)

All tests run against the real nginx → FastAPI stack — no ASGITransport,
no monkeypatching. A 500 on any endpoint is a hard failure.

## Running

```bash
make test-e2e-api        # API contract only
make test-e2e            # API contract + Playwright UI
```

## Writing new tests

- Use the role fixtures from `conftest.py` (`advertiser_client`,
  `owner_client`, `admin_client`, `anonymous_client`) — they already have
  JWTs injected.
- Seed data comes from `scripts/e2e/seed_e2e.py`; extend that if you need
  more fixtures. Keep it idempotent.
- Don't import from `src.*` here — these tests only talk to the running
  API over HTTP. That keeps them fast and isolated from the in-process
  unit tests under `tests/unit/` and `tests/integration/`.
- The parent `tests/conftest.py` (heavy in-process DB fixtures) is **not**
  loaded for this suite — `tests/e2e_api/pytest.ini` overrides it.

## Folder layout

| File                          | Purpose                                         |
| ----------------------------- | ----------------------------------------------- |
| `conftest.py`                 | Role-based httpx.AsyncClient fixtures           |
| `pytest.ini`                  | Standalone config — avoids parent conftest      |
| `test_auth.py`                | Session / login / me endpoint contracts         |
| `test_query_params.py`        | Coercion & alias regression tests (placements)  |
| `test_role_boundaries.py`     | 401 / 403 / 200 sweep across ~17 routes         |
