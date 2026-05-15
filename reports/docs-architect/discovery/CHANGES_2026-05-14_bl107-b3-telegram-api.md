# CHANGES 2026-05-14 — BL-107 Phase B.3 (Telegram API + settings)

## Context

Telegram API integration layer для BL-107 (ФЗ-303 blogger registry verification).
Adds cross-SDK Protocol abstraction, lazy cache для Trustchannelbot ID
resolution с asyncio.Lock, helper function для admin verification, 5 new RKN
settings fields, `.env.example` update.

Replaces Phase B.2 temporary `_DEFAULT_RKN_THRESHOLD = 10_000` module constant с
`settings.rkn_threshold_subscribers` reference. Single source of truth migration —
one constant → one import.

Pure helpers + settings layer: NO API/router/bot/channel-add hookup. Phase B.4
will wire `verify_trustchannelbot_admin` invocation в API router + bot handler
channel-add code paths.

Design ref: `BL-107_DESIGN_2026-05-14.md` @ `38dbc94` § 3 (Cross-SDK Protocol)
+ § 4 (Lazy cache + env override) + § 5 (Settings).

Built atop Phase B.2 gate framework (`97137d9`) — Phase B.4 invocation pattern
will be:

```python
try:
    is_verified = await verify_trustchannelbot_admin(bot, channel.telegram_id)
except TrustchannelbotResolutionError:
    # → emit GateResult с SUBSCRIBER_COUNT_UNKNOWN reason
    return ChannelAddDeclined(...)
channel_data = ChannelAddContext(
    telegram_id=...,
    username=...,
    member_count=...,
    is_blogger_registry_verified=is_verified,  # populated from helper
)
gates = await legal_compliance.check_gates_for_channel_add(user, channel_data)
```

## Changes

### Added — Telegram verification module

New file: `src/utils/telegram/verify_blogger_registry.py`

- **`TelegramAdminLister(Protocol)`** — cross-SDK abstraction для
  `get_chat_administrators(chat_id) -> list[Any]` и `get_chat(chat_id) -> Any`.
  Compatible с aiogram.Bot и telegram.Bot (python-telegram-bot) — both expose
  the same coroutine names returning objects shaped `.user.id` и `.id`.
  Duck-typing на returned objects — neither SDK forces concrete class hierarchy.
- **`TrustchannelbotResolutionError(Exception)`** — raised когда:
  - `settings.rkn_trustchannelbot_id is None` (no env override), AND
  - module cache `_TRUSTCHANNELBOT_ID_CACHE` empty, AND
  - `bot.get_chat(username)` API call fails.

  Phase B.4 channel-add helper catches this → returns GateResult с
  `GateReason.SUBSCRIBER_COUNT_UNKNOWN` (channel-add blocked, owner informed).
- **`resolve_trustchannelbot_id(bot) -> int`** — lazy resolver:
  1. `settings.rkn_trustchannelbot_id` set → return directly (env override)
  2. Module cache populated → return cache (fast path, no lock)
  3. Acquire `_TRUSTCHANNELBOT_CACHE_LOCK`, double-check cache, fetch via
     `bot.get_chat(username)` → cache → return
  - Lock prevents N parallel cold-start callers from issuing duplicate API requests.
- **`verify_trustchannelbot_admin(bot, chat_id) -> bool`** — primary helper:
  - Resolves Trustchannelbot ID via `resolve_trustchannelbot_id`
  - Calls `bot.get_chat_administrators(chat_id)`
  - Returns True если any admin has `.user.id == trustchannelbot_id`
  - Empty admin list / malformed admin object → returns False (no raise)
  - `TrustchannelbotResolutionError` propagates (caller wraps)
  - `get_chat_administrators` API exception propagates
- **`_reset_cache_for_testing()`** — test-only cache reset helper (name-mangled
  underscore prefix, not public API).

Module-level state:

- `_TRUSTCHANNELBOT_ID_CACHE: int | None = None` (process lifetime, не survives restart)
- `_TRUSTCHANNELBOT_CACHE_LOCK = asyncio.Lock()` (concurrent-safe resolution)

### Added — RKN settings fields (5)

В `src/config/settings.py` после `admin_telegram_bot_token` и перед `admin_ids` property:

- `rkn_trustchannelbot_username: str = Field("@Trustchannelbot", alias="RKN_TRUSTCHANNELBOT_USERNAME", ...)`
- `rkn_trustchannelbot_id: int | None = Field(None, alias="RKN_TRUSTCHANNELBOT_ID", ...)` (auto-resolved if None)
- `rkn_threshold_subscribers: int = Field(10_000, alias="RKN_THRESHOLD_SUBSCRIBERS", ...)` (ФЗ-303 порог)
- `rkn_periodic_check_enabled: bool = Field(True, alias="RKN_PERIODIC_CHECK_ENABLED", ...)` (Phase B.6 feature flag)
- `rkn_block_unverified_placements: bool = Field(False, alias="RKN_BLOCK_UNVERIFIED_PLACEMENTS", ...)` (production guard)

### Added — `.env.example` section

Appended new section с 5 keys + section header `# RKN BLOGGER REGISTRY (BL-107 / ФЗ-303)` +
inline comments. Format mirrors existing sections (`# ════════` separators, Russian comments).

### Changed — `src/core/services/gates/owner_gates.py`

- Removed: `_DEFAULT_RKN_THRESHOLD = 10_000` Phase B.2 module-level temporary constant
- Added: `from src.config.settings import settings`
- Replaced: `if member_count < _DEFAULT_RKN_THRESHOLD:` → `if member_count < settings.rkn_threshold_subscribers:`
- Updated `_check_g19_core` docstring — reflects settings-driven threshold + monkeypatch test pattern

### Added — tests

New file: `tests/unit/test_bl107_trustchannelbot_helper.py` — 11 tests, 3 classes:

| Class | # | Tests |
|---|---|---|
| `TestResolveTrustchannelbotId` | 4 | env override no bot call / cache miss + caches / API failure raises / concurrent dedupe via lock |
| `TestVerifyTrustchannelbotAdmin` | 6 | admin found / admin not found / empty list / malformed admin (no .user) / propagates ResolutionError / propagates get_admins exception |
| `TestResetCacheHelper` | 1 | reset clears cache, next call re-fetches |

Test pattern:
- `@pytest.fixture(autouse=True)` resets cache between tests
- `monkeypatch.setattr(settings, "rkn_trustchannelbot_id", ...)` для env override control
- `AsyncMock(spec=TelegramAdminLister)` для bot mocking
- No network, no DB, fast (~1s for 11 tests)

## Verification

- `make typecheck`: 0/303 ✅ (was 0/302 — +1 verify_blogger_registry.py)
- `make lint`: 7 errors ✅ (BL-024 baseline preserved — all pre-existing in `tests/unit/conftest.py`)
- `make format-check`: 422 files clean ✅ (was 420, +2 new — auto-formatted via `ruff format`)
- `alembic check`: drift-free ✅ (Phase B.3 не trogает schema)
- `pytest tests/unit/test_bl107_trustchannelbot_helper.py -v`: 11/11 ✅
- `pytest tests/unit/test_bl107_g19_gate.py -v`: 22/22 ✅ (Phase B.2 still pass)
- `pytest tests/unit/test_bl107_schema_regression.py -v`: 15/15 ✅ (Phase B.1 still pass)
- BL-107 focused suite (helper + G19 + schema + legal_compliance + owner_gates + contract): 123/123 ✅
- Full unit sweep: 757/757 ✅ (was 746 + 11 new tests)

## Phase B.4 dependencies surfaced

- `verify_trustchannelbot_admin` invocation patterns в both:
  - `src/api/routers/channels.py` channel-add endpoint (uses python-telegram-bot Bot from `src/api/...`)
  - `src/bot/handlers/owner/channel_owner.py` channel-add handler (uses aiogram Bot)
- `TrustchannelbotResolutionError` handling → `GateReason.SUBSCRIBER_COUNT_UNKNOWN` GateResult emission
- `ChannelAddContext.is_blogger_registry_verified` populated from helper result
- Both invocation sites currently call `check_gates_for_user_role(user, role="owner")` — Phase B.4 adds
  `check_gates_for_channel_add(user, channel_data)` after Trustchannelbot check

## Untouched (deferred к subsequent phases)

- **Phase B.4** — Channel-add hookup в API router + bot handler (helper invocations + ChannelAddContext construction)
- **Phase B.5** — Admin review UI (5 endpoints + 2 web_portal screens)
- **Phase B.6** — Celery periodic task `parser:check_channel_registry_status` (uses `settings.rkn_periodic_check_enabled`)
- **Phase B.7** — O.7 carve-out closing (bot handler `is_test` parity)
- **Phase B.8** — BL-002 mock infrastructure (custom aiohttp stub + docker-compose.test.yml + `TELEGRAM_API_BASE_URL` routing)
- **Phase B.9** — E2E tests + Playwright spec unblock

## Decisions echoed (от Phase A2 design)

- Q-A2 § 3: `TelegramAdminLister` Protocol pattern — cross-SDK abstraction
  via duck-typing (NOT separate adapter classes per SDK)
- Q5: Lazy cache + env override (NOT boot-time fetch, NOT manual-only)
  с asyncio.Lock для concurrent-safe resolution
- § 5: Settings field naming `rkn_*` для namespace clarity (RKN = Роскомнадзор)
- Single helper module для обоих SDK contexts — duck-typing на returned
  ChatMember.user.id (both SDKs return objects shaped that way)

## Risks / non-deviations

- **Pyright env diagnostics** (`pydantic` / `sqlalchemy.ext.asyncio` / `pytest`
  imports "could not be resolved") — pre-existing environment-level issue
  (not LSP). mypy passes 0/303.
- **Module-level cache** — process-lifetime, doesn't survive worker restart.
  Acceptable per Phase A2 design Q5 (auto-re-resolves on next API call после restart).
  Не shared across processes — each FastAPI worker + Celery worker populates
  independently, but they all resolve к the same chat ID.
- **`reset_cache_for_testing` is leading-underscore** — discoverable via
  `from src.utils.telegram.verify_blogger_registry import _reset_cache_for_testing`
  но not part of public API. Standard test-helper pattern.

🔍 Verified against: branch HEAD post-commit | 📅 Created: 2026-05-14
