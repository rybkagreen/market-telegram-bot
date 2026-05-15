# CHANGES 2026-05-14 — BL-107 Phase B.8 (BL-002 mock infrastructure)

## Context

Phase B.8 builds the Telegram Bot API mock infrastructure that BL-002 has been
blocked on since plan-08 (Playwright `test.fixme` block at
`web_portal/tests/specs/deep-flows.spec.ts:289-296`). Phase B.9 will consume
this infrastructure для:

- BL-002 channel-add E2E unblock
- BL-107 add-flow E2E coverage (verified + not-verified channels)
- Future Playwright/Vitest test expansion без real Telegram API calls

**Q6 wide-scope decision (locked by Marina):** BL-002 bundled into BL-107
instead of separate workstream.

**Scope envelope:** narrow surgical change — new stub directory + 2 SDK
factory tweaks + Settings validator + .env.test entry + 3 unit-test files +
docker-compose.test.yml service. No business logic changes, no schema/migration
touch, no frontend, no API endpoints, no other bot handlers.

Built atop Phase B.7 (`e6fd580`).

## Empirical decisions (versus PROMPT 42 assumptions)

1. **Bot factory locations** — prompt assumed `src/bot/_bot_factory.py`, но не
   существует. Actual locations:
   - `src/bot/session_factory.py:new_bot()` — aiogram single source of truth
     (used by polling и delegated to by `src/tasks/_bot_factory.py`).
   - `src/api/dependencies.py:get_bot()` — python-telegram-bot singleton.
   - `src/tasks/_bot_factory.py` НЕ touched — delegates to session_factory.

2. **`docker-compose.test.yml` ALREADY EXISTS** с full e2e stack (postgres-test,
   redis-test, seed-test, api-test, nginx-test, playwright, api-contract).
   Plan modified existing file (added `telegram-stub` service to `e2e_network`),
   не создавал новый.

3. **Settings env discriminator** — no `environment` field существует. Use
   existing **`sentry_environment`** (default "production"). Validator
   construction: `if sentry_environment == "production" and
   telegram_api_base_url is not None: raise`. Bonus: defaults preserve prod-safe
   behavior even if both fields omitted.

4. **Layer 3 (deploy script assertion) DEFERRED** as operational follow-up — no
   accessible production deploy script. Layers 1 (Pydantic validator) + 2
   (Sentry breadcrumb + logger warning) provide defense-in-depth at startup.

5. **Stub server port 8081** — docker-compose internal only (no external
   port published).

## Changes per file

### New — `tests/e2e/telegram_api_stub/` (entire directory)

**`app.py`** — aiohttp Application + per-method handlers:
- 9 supported methods: `getMe`, `getChat`, `getChatAdministrators`,
  `getChatMember`, `sendMessage`, `sendChatAction`, `deleteWebhook`,
  `setChatMenuButton`, `getUpdates`
- Catch-all default: returns `{"ok": true, "result": {}}` for any unknown
  Telegram method (safe noop pattern)
- Telegram-compatible URL: `/bot{token}/{method}` (HTTP * — GET/POST)
- File-URL: `/file/bot{token}/{path}` (downloads, currently no-op)
- Test introspection endpoints: `/health`, `/__stub__/state`, `/__stub__/reset`

**`fixtures.py`** — `Fixtures` dataclass + helpers:
- `default_fixtures()` — built-in set with `@verified_channel` (15k subs,
  Trustchannelbot admin → passes ФЗ-303 verification) and
  `@not_verified_channel` (5k subs, no Trustchannelbot admin → fails check)
- `load_fixtures(path)` — JSON-loaded fixture, falls back to defaults if file
  missing or malformed
- `Fixtures.resolve_chat()` — accepts numeric id, `@username`, or plain
  username
- `Fixtures.get_admins()`, `Fixtures.get_member()` — admin/member lookups

**`state.py`** — `StubState` dataclass:
- Thread-safe (Lock) recording of side-effects: `sent_messages`,
  `chat_actions`, `webhook_deletions`, `menu_button_sets`, `method_calls`
- `record_call(method)` invoked on every dispatched method
- `snapshot()` returns JSON-serializable frozen copy
- `reset()` between scenarios

**`__main__.py`** — standalone entry point:
- Env: `STUB_PORT` (default 8081), `STUB_HOST` (default 0.0.0.0),
  `STUB_FIXTURES_PATH` (optional, falls back to defaults)
- Smoke test verified в Шаг 2.4 (curl на all 9 methods + catch-all + state
  snapshot)

**`Dockerfile`** — minimal `python:3.12-slim` + aiohttp:
- aiohttp range `>=3.11,<3.13` — matches project pin `^3.11.11` (lockfile
  3.12.15)
- COPY stub directory only — no app source
- CMD: `python -m tests.e2e.telegram_api_stub`
- EXPOSE 8081

**`fixtures/*.json`** — 3 sample fixtures (verified_channel, not_verified_channel,
api_failure) — drop-in for `STUB_FIXTURES_PATH` env var.

### Modified — `docker-compose.test.yml`

- New `telegram-stub` service: builds from stub Dockerfile, joins `e2e_network`,
  healthcheck on `http://localhost:8081/health` (urllib-based, no extra deps)
- `api-test.depends_on` now includes `telegram-stub: condition: service_healthy`
  — guarantees stub is ready before API bot attempts any Telegram call
- No port published — internal-only to `e2e_network`

### Modified — `src/config/settings.py`

- Added `model_validator` import alongside existing `field_validator`
- New field `telegram_api_base_url: str | None` (alias `TELEGRAM_API_BASE_URL`,
  default None) — base URL override for both Telegram SDKs
- New `_validate_telegram_api_base_url` `@model_validator(mode="after")` — R4
  production guard layer 1: raises `ValueError` if `sentry_environment ==
  "production"` and `telegram_api_base_url is not None`

### Modified — `src/bot/session_factory.py`

- `new_bot()` extended: when `settings.telegram_api_base_url` is set, the
  AiohttpSession is built with `api=TelegramAPIServer.from_base(<URL>)` so
  aiogram routes through stub instead of api.telegram.org
- Proxy + base_url compose cleanly: both kwargs are collected into a single
  session_kwargs dict, allowing test setups that need both

### Modified — `src/api/dependencies.py`

- `get_bot()` extended for python-telegram-bot: when
  `settings.telegram_api_base_url` is set, `Bot.base_url` rewritten to
  `<base>/bot` and `Bot.base_file_url` rewritten to `<base>/file/bot`
- Trailing slash on base URL is normalized via `.rstrip("/")`
- Proxy + base_url compose: both honored together

### Modified — `src/api/main.py` + `src/bot/main.py` (R4 layer 2)

Both startup files emit:
- `logger.warning(...)` если `settings.telegram_api_base_url` is set —
  surfaces test-mode runs to ops without depending on Sentry
- `sentry_sdk.add_breadcrumb(category="config", level="warning", ...)` если
  `sentry_dsn` is also set — keeps audit trail в Sentry

Layer 2 is observability-only. Layer 1 (Settings validator) is the hard guard.

### Modified — `.env.test`

- `TELEGRAM_API_BASE_URL=http://telegram-stub:8081` — routes the E2E stack's
  bots to the in-network stub service
- `SENTRY_ENVIRONMENT=test` — unlocks the override at the validator level

### New — `tests/unit/test_bl107_b8_stub_server.py` (10 tests)

| # | Scenario |
|---|---|
| 1 | `getMe` returns bot identity |
| 2 | `getChat` returns channel info by `@username` (strips `_admins`) |
| 3 | `getChat` returns 400 for unknown chat |
| 4 | `getChatAdministrators` includes Trustchannelbot for `@verified_channel` |
| 5 | `getChatAdministrators` omits Trustchannelbot for `@not_verified_channel` |
| 6 | `sendMessage` accepts POST and records state |
| 7 | Unknown method returns safe-noop `{ok:true, result:{}}` |
| 8 | `/__stub__/state` introspection endpoint reflects method_calls + sent_messages |
| 9 | `load_fixtures(path)` reads from disk |
| 10 | `load_fixtures(missing_path)` falls back to defaults |

### New — `tests/unit/test_bl107_b8_settings_validator.py` (5 tests)

| # | Scenario |
|---|---|
| 1 | Production + base_url → `ValidationError` |
| 2 | Production + base_url=None → accepted |
| 3 | Test env + base_url → accepted |
| 4 | Development env + base_url → accepted |
| 5 | Default (no envs set) → production safe, base_url is None |

Uses `monkeypatch.setenv` with UPPERCASE alias names because Settings does
NOT enable `populate_by_name` — kwargs must match the env-var alias form
to be recognized by Pydantic.

### New — `tests/unit/test_bl107_b8_bot_factory_routing.py` (6 tests)

| # | Scenario |
|---|---|
| 1 | aiogram `new_bot()` без override → default `api.telegram.org` session |
| 2 | aiogram `new_bot()` с override → `TelegramAPIServer.from_base(<URL>)` applied |
| 3 | aiogram `new_bot()` с proxy + base_url → both honored together |
| 4 | python-telegram-bot `get_bot()` без override → default `https://api.telegram.org/bot<TOKEN>` |
| 5 | python-telegram-bot `get_bot()` с override → `<URL>/bot<TOKEN>` + `<URL>/file/bot<TOKEN>` |
| 6 | python-telegram-bot `get_bot()` с trailing-slash override → normalized (no `//bot`) |

PTB tests use autouse `_reset_ptb_singleton` fixture, AsyncMock на `Bot.initialize`
для skip-network. Note: PTB's `Bot.base_url` is `<base>/bot<TOKEN>` — library
concatenates token onto whatever base we pass, so assertions use `.startswith()`.

### Modified — `CHANGELOG.md`

Phase B.8 entry under `[Unreleased]`. Documents Added (stub directory,
docker-compose modification, settings validator, bot factory routing, observability
layers), Closed (BL-002 mock infrastructure ready), и Infrastructure note about
3-layer R4 production guard.

## Verification

- `make typecheck`: 0/305 ✓
- `make lint`: 7 baseline preserved (all 7 in `tests/unit/conftest.py` — BL-024) ✓
- `make format-check` (`poetry run ruff format --check`): clean ✓
- `alembic check`: drift-free ✓ (Phase B.8 не trogает schema)
- `docker compose -f docker-compose.test.yml config`: YAML valid ✓
- `pytest tests/unit/test_bl107_b8_*.py`: 21/21 ✓
- `pytest tests/unit/test_bl107_*.py`: 118/118 ✓ (97 prior + 21 new)
- Stub standalone smoke test (curl on getMe, getChat, getChatAdministrators,
  unknown chat 400, sendMessage POST, unknown method catch-all, state snapshot):
  all expected responses ✓

## R4 production guard — 3-layer defense-in-depth

| Layer | Where | Behavior |
|---|---|---|
| 1 | `src/config/settings.py` `_validate_telegram_api_base_url` | Pydantic model_validator raises `ValueError` if `sentry_environment == "production"` and `telegram_api_base_url` is non-None. Hard fail at Settings construction → app cannot start. |
| 2 | `src/api/main.py` + `src/bot/main.py` startup hooks | `logger.warning(...)` + `sentry_sdk.add_breadcrumb(...)` when base_url is set. Observability — surfaces non-default override to ops/Sentry. |
| 3 | Deployment script assertion | **DEFERRED operational** — no accessible production deploy script in repo. Tracked для ops follow-up. Layers 1+2 provide complete startup-time defense; layer 3 is belt-and-suspenders at deploy-pipeline level. |

## Untouched (per Phase B.8 scope envelope)

- Frontend (web_portal/*, mini_app/*) — Phase B.5b stable; Phase B.9 will consume
- Backend endpoints (`src/api/routers/`) — Phase B.5a stable
- Schema / migrations — Phase B.1 done
- Gate framework — Phase B.2 stable
- Telegram helpers — Phase B.3 stable
- Channel-add hookup — Phase B.4 stable
- Admin review — Phase B.5a/b stable
- Periodic re-verification task — Phase B.6 stable
- Bot handlers — Phase B.4/B.7 stable
- `src/tasks/_bot_factory.py` — delegates to `session_factory.new_bot()`, no
  direct touch needed
- Playwright spec (BL-002 `test.fixme` block at `deep-flows.spec.ts:289-296`)
  — Phase B.9 unblock
- Vitest infrastructure (deferred B.5b) — Phase B.9
- BACKLOG.md — deferred to Phase B closure batch

## Decisions echoed

- **Sentry env as discriminator (not new `environment` field).** Default
  "production" keeps prod-safe; tests opt in via `SENTRY_ENVIRONMENT=test`.
- **Single endpoint pattern for stub URLs.** `/bot{token}/{method}` matches
  Telegram Bot API exactly — both SDKs route к ним без custom path mapping.
- **Catch-all default returns success.** Stub is purpose-built для test runs
  where unexpected method calls should not fail the scenario unless asserted
  against. Tests explicitly opt в strict checking via state snapshot.
- **Defense-in-depth для R4.** Layer 1 (validator) is the hard guard — by
  itself sufficient. Layer 2 adds observability — surface unexpected overrides
  in staging. Layer 3 (deploy assertion) deferred operational — not blocking.
- **Stub Docker image kept minimal.** Only aiohttp + stub directory — no app
  source, no Poetry, ~30MB image. Build time ~10 sec.

## What BL-107 Phase B.8 delivers (operational)

After this commit:

- **In-process tests** (`tests/unit/test_bl107_b8_*.py`) consume stub directly
  via `aiohttp.test_utils` — 21 unit tests verify all stub behaviors.
- **In-network tests** (Docker compose) — when E2E stack starts (Phase B.9
  unblock), bots route к stub via `TELEGRAM_API_BASE_URL=http://telegram-stub:8081`
  set in `.env.test`. No real Telegram API hits.
- **Production safety** — settings validator + observability prevent stub URL
  from leaking into production deployments. Even if env var accidentally set,
  app refuses to start.

## R4-L3-DEFERRED operational follow-up

Layer 3 deployment script assertion (bash check `if env=production && base_url is
set: fail`) deferred from automated implementation because the repository does
not contain an accessible production deploy script. When operations are
formalized (Ansible playbook, CI/CD pipeline, Makefile target), the following
should be added to the production deploy step:

```bash
if [ "$SENTRY_ENVIRONMENT" = "production" ] && [ -n "$TELEGRAM_API_BASE_URL" ]; then
    echo "ERROR: TELEGRAM_API_BASE_URL must NOT be set in production deployment"
    exit 1
fi
```

This is operational-grade hardening, not a launch blocker — layers 1+2 already
prevent the misconfiguration at app startup.

## Remaining BL-107 work

- **Phase B.9** — E2E Playwright tests + component tests (vitest) для B.5b
  screens + BL-002 unblock (replace `test.fixme` at `deep-flows.spec.ts:289-296`
  with real test) + BL-107 add-flow E2E coverage.
- **Phase B closure** — CHANGES + CHANGELOG + BACKLOG sweep (BL-107 + BL-002 +
  O.7 closed).

🔍 Verified against: branch HEAD pre-commit `e6fd580` | 📅 Created: 2026-05-14
