# CHANGES 2026-04-25 — Phase 0: env consolidation, URL/ERID centralisation, JWT `aud` + ticket bridge

## Scope

Phase 0 of the production-readiness consolidation plan
(`IMPLEMENTATION_PLAN_ACTIVE.md`). Three sub-phases:

- **0.B.1** — collapse the `ENVIRONMENT` env variable into an explicit
  `ENABLE_E2E_AUTH` feature flag; delete dead `src/config/__init__.py`.
- **0.B.2** — centralise all public URLs through `settings.*`, introduce
  `src/constants/erid.py` with `ERID_STUB_PREFIX`, fix typo
  `rekhaborbot.ru → rekharbor.ru` (×4), wire `VITE_PORTAL_URL` through the
  Dockerfile + docker-compose build args, extend the grep-guard.
- **0.B.3** — add `aud` claim to every JWT, require it on decode, ship a
  `mini_app → web_portal` ticket bridge with manual Redis rate-limits and
  replay protection.

Plus the **0.C** acceptance suite (11 tests) and the meta-rules docs
commit that opened the phase.

## Phase 0 commits (in order on `feature/env-constants-jwt-aud`)

| Commit | Type | Subject |
|--------|------|---------|
| 0809628 | docs | add objections-section + phase-discipline rules |
| 2c5a2f2 | chore(config) | consolidate ENVIRONMENT into explicit ENABLE_E2E_AUTH flag |
| 371b335 | chore(config) | centralise public URLs and ERID prefix; fix typo |
| c5b23da | docs(plan) | correct Phase 0.B.2 URL defaults to subdomain scheme |
| 35dfc8a | feat(api) | JWT aud claim + mini_app→web_portal ticket bridge |
| 11d5f21 | test(api) | JWT aud claim and ticket-bridge acceptance suite |

## Affected files

### 0.B.1 — environment flag

- `src/config/__init__.py` — **deleted** (dead parallel `Settings`, zero
  importers verified before removal).
- `src/config/settings.py` — drop `environment` field, drop
  `is_development/is_production/is_testing` properties; add
  `enable_e2e_auth: bool = Field(False, alias="ENABLE_E2E_AUTH")`.
- `src/api/main.py:193` — `if settings.environment == "testing"` →
  `if settings.enable_e2e_auth`.
- `src/api/main.py:260` — drop `environment` key from `/health` response.
- `src/api/routers/auth_e2e.py` — docstring rewritten under the new flag.
- `.env.example`, `.env.test.example` — drop `ENVIRONMENT=`, add
  `ENABLE_E2E_AUTH=`.

### 0.B.2 — URLs + ERID + typo

- `src/constants/erid.py` — **new**. `ERID_STUB_PREFIX = "STUB-ERID-"`
  (provider type — orthogonal to the placement-test-mode concept that
  Phase 5 introduces).
- `src/core/services/stub_ord_provider.py` — uses `ERID_STUB_PREFIX`.
- `src/config/settings.py` — **subdomain-correct** URL defaults:
  - `mini_app_url = https://app.rekharbor.ru/`
  - `web_portal_url = https://portal.rekharbor.ru` (was `rekharbor.ru/portal`)
  - `landing_url = https://rekharbor.ru` (apex)
  - `api_public_url = https://api.rekharbor.ru`
  - `tracking_base_url = https://t.rekharbor.ru` (was `rekharbor.ru/t`)
  - `terms_url = https://rekharbor.ru/terms`
  - `ticket_jwt_ttl_seconds = 300`
  - `sandbox_telegram_channel_id = None`
- 8 backend hardcoded URL replacements:
  - `src/api/main.py` CORS origins → `settings.{mini_app,landing}_url`
  - `src/bot/main.py:65` `WebAppInfo(url=...)` → `settings.mini_app_url`
  - `src/bot/handlers/shared/legal_profile.py` `PORTAL_URL` →
    `settings.web_portal_url`
  - `src/bot/handlers/shared/start.py` `TOS_TEXT` Terms link →
    `settings.terms_url`
  - `src/bot/handlers/shared/login_code.py` `_CODE_TEMPLATE` →
    `settings.web_portal_url`
  - `src/core/services/publication_service.py` tracking URL →
    `settings.tracking_base_url`
  - `src/core/services/link_tracking_service.py` (×2 sites) →
    `settings.tracking_base_url`
- `src/constants/legal.py` — typo `rekhaborbot.ru → rekharbor.ru` (4
  sites: lines 53, 83, 107, 108).
- `mini_app/src/screens/common/LegalProfileSetup.tsx`,
  `mini_app/src/screens/common/LegalProfilePrompt.tsx` — drop hidden
  fallback `|| 'https://rekharbor.ru/portal'`. Now reads
  `import.meta.env.VITE_PORTAL_URL` directly.
- `mini_app/.env.example` — add `VITE_PORTAL_URL=https://portal.rekharbor.ru`.
- `docker/Dockerfile.nginx` — `ARG VITE_PORTAL_URL=...` + `ENV ...` in
  the `builder-miniapp` stage so the value is baked into the build.
- `docker-compose.yml` — `services.nginx.build.args.VITE_PORTAL_URL`
  pulled from the host env (`${VITE_PORTAL_URL:-...default...}`).
- `scripts/check_forbidden_patterns.sh` — three new guards: hardcoded
  `https?://[a-zA-Z0-9.\-]*rekharbor\.ru` URLs in `src/`,
  `mini_app/src/`, `web_portal/src/` (with documented exclusions).
- `IMPLEMENTATION_PLAN_ACTIVE.md` — frozen URL defaults updated to the
  subdomain scheme so the historical record matches the code.

### 0.B.3 — JWT aud + ticket bridge

- `src/api/auth_utils.py`:
  - `JwtSource = Literal["mini_app", "web_portal"]` exported.
  - `create_jwt_token` — required `source: JwtSource` parameter; payload
    now carries `aud`.
  - `decode_jwt_token` — required positional `audience` argument
    (`JwtSource | list[JwtSource] | None`). No default by design — every
    caller must explicitly decide what it accepts. `None` is the
    explicit opt-out for legacy/audit helpers.
- `src/api/dependencies.py`:
  - `get_current_user` — accepts both audiences, rejects aud-less
    legacy tokens with **401**.
  - **new** `get_current_user_from_web_portal` — rejects mini_app JWT
    with **403**. To be wired into ФЗ-152 paths in Phase 1.
  - **new** `get_current_user_from_mini_app` — rejects web_portal JWT
    with 403; consumed by the bridge endpoint below.
- `src/api/routers/auth.py` — adds:
  - `POST /api/auth/exchange-miniapp-to-portal` — mints short-lived
    ticket-JWT (`aud="web_portal"`, `jti=uuid4`,
    `TTL=settings.ticket_jwt_ttl_seconds`); stores
    `auth:ticket:jti:{jti}` in Redis with JSON body
    `{user_id, issued_at, ip}`.
  - `POST /api/auth/consume-ticket` — public endpoint with manual Redis
    `INCR + EXPIRE` rate-limits:
    - 10 req/minute/IP → 11th = 429.
    - 5 fails/5 min/user_id → 6th = 429 + `event=ticket_consume_user_blocked`.
    - One-shot Redis `DELETE` on jti — replay returns 401 +
      `event=ticket_consume_failed`.
    - Real client IP via `X-Forwarded-For` → `X-Real-IP` →
      `request.client.host` chain. nginx/conf.d/default.conf already sets
      both upstream headers on every `/api/*` block — verified.
  - Helpers `_client_ip`, `_check_ip_rate_limit`,
    `_check_user_fail_limit`, `_record_user_fail`.
- `src/api/routers/auth_login_widget.py:111`,
  `src/api/routers/auth_login_code.py:124`,
  `src/api/routers/auth.py:90`,
  `src/api/routers/auth_e2e.py:47` — pass `source=` on every
  `create_jwt_token` call.
- `src/api/middleware/audit_middleware.py` — comment-only `FIXME(security)`
  on `_extract_user_id_from_token`. No logic change. The middleware
  decodes JWT without signature verification; today this is safe because
  it runs after the authenticated dependency, but the pattern should be
  reworked to read a pre-validated payload off `request.state.user`.
  Tracked as a TODO ticket (separate from this commit).
- `src/api/schemas/auth.py` — **new**. Pydantic models `TicketResponse`
  and `AuthTokenResponse`.
- `tests/unit/test_contract_schemas.py` — both new schemas registered;
  snapshots checked in at
  `tests/unit/snapshots/{ticket_response,auth_token_response}.json`.

### 0.C — acceptance suite

- `tests/unit/api/test_jwt_aud_claim.py` — **new**, 9 cases (8 mandated +
  1 symmetric guard for `get_current_user_from_mini_app`).
- `tests/unit/api/test_jwt_rate_limit.py` — **new**, 2 rate-limit cases.
- Both files reuse a small `FakeRedis` stub + a `monkeypatch` on
  `async_session_factory` — sub-second runs, no testcontainer dependency.

## Public contracts

**New endpoints:**
- `POST /api/auth/exchange-miniapp-to-portal`
  - Auth: `get_current_user_from_mini_app` (mini_app JWT only).
  - Response: `TicketResponse {ticket: str, portal_url: str, expires_in: int}`.
- `POST /api/auth/consume-ticket`
  - Auth: none (rate-limited).
  - Body: `ConsumeTicketRequest {ticket: str}`.
  - Response: `AuthTokenResponse {access_token, token_type="bearer", source="web_portal"}`.

**Changed contracts:**
- All four token-issuing endpoints now return JWTs with `aud` claim.
  Legacy aud-less tokens issued before this phase are rejected on the
  next request — pre-prod policy, one re-login window.
- `decode_jwt_token` signature changed: required `audience` argument.
  Internal helper, but third-party importers (none today) would break.

## Migration notes

- **One-time re-login** required for any session that already carried an
  aud-less JWT. Acceptable in pre-prod.
- `ENVIRONMENT` env variable is now ignored. `.env`-files referencing
  it should be updated to use `ENABLE_E2E_AUTH` (only the test stack
  needs it set to `true`).
- `VITE_PORTAL_URL` must be defined when building the mini_app image.
  The Dockerfile and docker-compose carry the same default
  (`https://portal.rekharbor.ru`) so existing `docker compose up
  --build` keeps working without ops changes.
- `STUB-ERID-` prefix unchanged. The plan's earlier proposal to rename
  it to `TEST-ERID-` was rejected on semantic grounds (STUB describes
  the *provider type*, TEST would describe the *placement mode* — Phase
  5 is the right place for a placement-mode marker).

## Acceptance criteria — verified

- [x] `grep -rn "settings.environment" src/` → 0 results.
- [x] `grep -rn "rekhaborbot" src/` → 0 results.
- [x] `grep -rn "rekharbor.ru" src/ --include="*.py"` → only
      `settings.py` defaults and `src/constants/legal.py` (deferred to
      Phase 6 per plan).
- [x] `scripts/check_forbidden_patterns.sh` → exit 0, 12 checks passed.
- [x] `tests/unit/api/test_jwt_aud_claim.py` → 9/9 passing
      (8 mandated + 1 symmetric guard).
- [x] `tests/unit/api/test_jwt_rate_limit.py` → 2/2 passing.
- [x] `tests/unit/test_contract_schemas.py` → 22/22 passing
      (snapshots committed for both new schemas).
- [x] Ruff clean for every file Phase 0 touched. (Two pre-existing ruff
      errors in `src/api/routers/document_validation.py:107,263` exist
      independently of Phase 0 — verified by `git stash`. Out of scope.)

## Not verified

- mypy — pre-existing 529 errors in 41 files (CLAUDE.md). My changes do
  not introduce new mypy errors in the Phase 0 surface, but full-repo
  `make typecheck` was not re-run.
- E2E (Playwright) — Phase 0 is backend-only; the mini_app `OpenInWebPortal`
  flow lives in Phase 1.

## Why these decisions exist (audit trail)

The original 0.A plan proposed two security-relevant compromises that
were rejected during the consolidation review:
1. *Accept legacy aud-less JWTs with WARN* — defeats the purpose of the
   new claim. Replaced with hard 401 + one-time re-login (pre-prod has
   few users; ops cost is acceptable).
2. *Rename `STUB-ERID-` → `TEST-ERID-`* — would conflate provider type
   with placement mode. Two orthogonal axes; keep them separate.

A third issue surfaced in implementation review:
3. *`request.client.host` for rate-limit IP* — would resolve to the
   nginx container IP (127.0.0.1) and turn the per-IP limit into a
   global limit. Replaced with `X-Forwarded-For` → `X-Real-IP` →
   `request.client.host` chain. nginx config was verified to set both
   headers on every upstream block before the change shipped.

🔍 Verified against: 11d5f21ce5875d4f81b45d2ebb26ba4736d432a4 | 📅 Updated: 2026-04-25T00:00:00Z
