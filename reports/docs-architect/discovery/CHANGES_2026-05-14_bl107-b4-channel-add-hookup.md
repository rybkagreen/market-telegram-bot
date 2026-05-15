# CHANGES 2026-05-14 — BL-107 Phase B.4 (Channel-add hookup)

## Context

Critical integration phase для BL-107 (ФЗ-303 blogger registry verification).
Wires Phase B.1 (schema) + B.2 (gate framework) + B.3 (Telegram API helpers)
foundation в production channel-add code paths. **After this commit BL-107
actually enforces ФЗ-303 на новых channel-add операциях.**

Two parallel code paths integrated:
- API router `src/api/routers/channels.py:create_channel` (python-telegram-bot SDK context)
- Bot handler `src/bot/handlers/owner/channel_owner.py:add_channel_confirm` (aiogram SDK context)

Both invoke same Phase B.3 helper (Protocol abstraction) + same Phase B.2
orchestration method — DRY through framework, not duplication.

Design ref: `BL-107_DESIGN_2026-05-14.md` @ `38dbc94` § 2 (Helper architecture).
Built atop Phase B.3 (`8bf5e55`) — Telegram API helpers + settings + RKN config.

## Changes

### Modified — `src/api/routers/channels.py` (create_channel endpoint)

Phase B.4 wiring placed between existing bot ownership check (L389-403) и
existing duplicate check (was L405, moved down to L478). Order:

1. **(preserved)** Admin test bypass + existing user-role compliance check
2. **(preserved)** Bot get_chat / type check / bot admin verification
3. **(NEW + moved up)** member_count fetch (was inside create flow, now upstream
   for G19 evaluation)
4. **(NEW, inside `if not admin_test_bypass:`)** G19 wiring:
   - `verify_trustchannelbot_admin(bot, chat.id)` call
   - `TrustchannelbotResolutionError` → audit log + raise `ChannelAddDeclinedError`
     с `SUBSCRIBER_COUNT_UNKNOWN` blocker
   - `ChannelAddContext` construction (telegram_id, username, member_count,
     is_test computed как `body.is_test and current_user.is_admin`, description)
   - `compliance.check_gates_for_channel_add(current_user, channel_data)` call
   - If blockers — audit log + raise `ChannelAddDeclinedError` с G19 blocker
   - Audit fields population: `last_blogger_registry_check_at = datetime.now(UTC)`;
     если `is_verified` — также verified_at, verification_method=TRUSTCHANNELBOT_ADMIN,
     member_count_at_verification
5. **(preserved)** Duplicate check
6. **(preserved)** Category validation
7. **(MODIFIED)** `repo.create(data)` dict spread с new `**verification_audit`
   fields

New imports added:
- `BloggerRegistryVerificationMethod` от `src.core.enums.blogger_registry`
- `GateReason` от `src.core.enums.gate_reason`
- `PlacementGate` от `src.core.enums.placement_gate`
- `ChannelAddContext` от `src.core.schemas.channel_add_context`
- `verify_trustchannelbot_admin`, `TrustchannelbotResolutionError` от
  `src.utils.telegram.verify_blogger_registry`

(`datetime, UTC` already imported.)

### Modified — `src/bot/handlers/owner/channel_owner.py` (add_channel_confirm)

Phase B.4 wiring placed AFTER existing user-role compliance check (L367-396),
BEFORE TelegramChat instantiation (L398-407). Order:

1. **(preserved)** User lookup + existing user-role compliance check
2. **(NEW)** G19 wiring:
   - Get bot instance from `callback.message.bot` (с None-check)
   - `verify_trustchannelbot_admin(bot, data["channel_telegram_id"])` call
   - `TrustchannelbotResolutionError` → audit log + user-facing
     `callback.answer(...)` + `state.clear()` (no raise — bot UX pattern)
   - `ChannelAddContext` construction с `is_test=False` (O.7 deferred — bot UX
     has no is_test parameter)
   - `compliance.check_gates_for_channel_add(user, channel_data)` call
   - If blockers — audit log + user-facing edit_text message + `state.clear()`
   - Audit fields population: same logic as API
3. **(MODIFIED)** `TelegramChat(...)` instantiation kwargs с new
   `**verification_audit` spread

New imports added:
- `from datetime import UTC, datetime` (was missing entirely)
- `from typing import Any` (для `dict[str, Any]`)
- `BloggerRegistryVerificationMethod`, `PlacementGate`, `ChannelAddContext`,
  `verify_trustchannelbot_admin`, `TrustchannelbotResolutionError`

### Forced scope expansion — Phase B.3 Protocol type fix

`src/utils/telegram/verify_blogger_registry.py`:
- Protocol return type for `get_chat_administrators`: `list[Any]` → `Sequence[Any]`
- Added `from collections.abc import Sequence` import

**Reason:** Real-world `Bot.get_chat_administrators` signatures differ:
- python-telegram-bot returns `Coroutine[Any, Any, tuple[ChatMember, ...]]`
- aiogram returns `Coroutine[Any, Any, list[ChatMember]]`

`list[Any]` rejects tuple (mypy strict — `tuple` is not subtype of `list`).
`Sequence[Any]` accepts both — same iteration behavior at runtime. Surfaced
only через Phase B.4 integration (Phase B.3 tested с AsyncMock spec which
satisfies any return shape).

Pattern parallels Phase B.1 forced FK disambiguation: defect in earlier phase
surfaced by integration in later phase. Fix is 1-line surgical, no behavior
change, no API change.

### Added — wiring tests

New file: `tests/unit/test_bl107_channel_add_g19_integration.py` — 9 tests, two
contexts:

**API router tests (5):**
| # | Test | Coverage |
|---|---|---|
| 1 | test_api_below_threshold_creates_channel_audit_minimum | <10k → channel created, audit minimum (last_check_at only) |
| 2 | test_api_verified_channel_creates_with_audit | ≥10k + verified → all audit fields, TRUSTCHANNELBOT_ADMIN method |
| 3 | test_api_large_channel_unverified_blocked_g19 | ≥10k без verification → 403 channel_add_declined с G19 blocker |
| 4 | test_api_trustchannelbot_resolution_error_blocked | TrustchannelbotResolutionError → 403 с SUBSCRIBER_COUNT_UNKNOWN |
| 5 | test_api_admin_test_bypass_skips_g19 | admin + is_test=True → user_role_spy + verify_spy not called |

**Bot handler tests (4):**
| # | Test | Coverage |
|---|---|---|
| 6 | test_bot_below_threshold_creates_channel | <10k → channel created, audit minimum |
| 7 | test_bot_verified_large_channel_audit_full | ≥10k + verified → all audit fields populated |
| 8 | test_bot_large_channel_unverified_blocked | ≥10k без verification → no channel, user-facing message, audit log |
| 9 | test_bot_trustchannelbot_resolution_error_user_message | API failure → user-facing message, no channel, audit log |

Mock pattern: `AsyncMock` for helper + LegalComplianceService methods;
`MagicMock(spec=ChatMemberAdministrator)` so `isinstance(...)` check passes;
fake_create monkeypatched on `TelegramChatRepository.create` to avoid real
DB roundtrip.

### Modified — existing tests (minimal surgical touch)

`tests/unit/test_bot_channel_owner.py::test_add_channel_confirm_happy_path_creates_channel`:
- Added `verify_trustchannelbot_admin` mock (returns False) — required because
  test FSM data member_count=1000 < 10k threshold, G19 channel-add gate runs
  real, passes naturally; the mock just prevents MagicMock-bot from crashing.

No other existing tests required updates — all G04/G05/G06 fail paths return
early before reaching G19 wiring.

## Verification

- `make typecheck`: 0/303 ✅
- `make lint`: 7 baseline preserved ✅ (I001 auto-fix applied on new test file)
- `make format-check`: 423 files clean ✅ (was 420 + 3 reformatted)
- `alembic check`: drift-free ✅ (Phase B.4 не trogает schema)
- `pytest tests/unit/test_bl107_channel_add_g19_integration.py -v`: 9/9 ✅
- `pytest tests/unit/api/test_channels_create.py -v`: 6/6 ✅ (existing G04-G06 tests unchanged)
- `pytest tests/unit/test_bot_channel_owner.py -v`: 4/4 ✅ (1 fixture mock added)
- BL-107 focused suite (B.1+B.2+B.3+B.4 + existing): 118/118 ✅
- Full unit sweep: 766+ passing (running)

## What Phase B.4 enables (ФЗ-303 enforcement live)

After this commit ships to production:

- **New channels ≥10k subscribers without Trustchannelbot admin** auto-blocked
  at add-time (primary path). Owner sees clear error message + audit log written.
- **Verified channels** (Trustchannelbot in admins) auto-marked
  `is_blogger_registry_verified=True` at creation. Full audit trail
  (verified_at, verification_method=TRUSTCHANNELBOT_ADMIN, member_count_at_verification).
- **Sub-10k channels** + **admin test channels** (is_admin + is_test=True)
  pass-through unchanged — regulation not applicable / admin carve-out.
- **Trustchannelbot API resolution failures** block channel-add с
  `SUBSCRIBER_COUNT_UNKNOWN` reason — recoverable via
  `settings.rkn_trustchannelbot_id` env override (Phase B.3 capability).
- **Existing channels** (created до Phase B.4 shipping) protected by **placement-side
  G19 gate** (Phase B.2) — fires alongside G07 at transitions to `pending_payment`.
  Manual evidence path для these existing channels TBD Phase B.5.

## Untouched (deferred к subsequent phases)

- **Phase B.5** — Admin review UI для manual evidence path (5 endpoints + 2
  web_portal screens + 1 mini_app screen). Manual submission flow для existing
  channels not currently in @Trustchannelbot admin list.
- **Phase B.6** — Celery periodic task `parser:check_channel_registry_status`
  для re-verification of existing channels (member_count growth, Trustchannelbot
  removal detection).
- **Phase B.7** — O.7 5b.7a deferred carve-out: bot handler `is_test` FSM step
  + admin permission parity с API path.
- **Phase B.8** — BL-002 mock infrastructure (custom aiohttp stub +
  docker-compose.test.yml + `TELEGRAM_API_BASE_URL` routing).
- **Phase B.9** — E2E tests + Playwright spec unblock.

## Decisions echoed (от Phase A2 design)

- **Q1**: Single helper в `LegalComplianceService.check_gates_for_channel_add`
  invoked from both call sites — confirmed appropriate.
- **Q2**: Parallel registry `_CHANNEL_CONTEXT_GATE_CHECKERS` orchestration
  via `check_gates_for_channel_add(user, channel_data)` signature.
- **Q4**: `member_count_at_verification` snapshot naming applied consistently.
- **Q5**: Lazy cache (Phase B.3) integration via Protocol abstraction —
  both SDKs работают через single helper, cache shared across calls in same
  worker process.
- **Q7**: O.7 carve-out NOT closed here — bot handler passes `is_test=False`
  hardcoded preserved. Phase B.7 will add FSM step.

🔍 Verified against: branch HEAD post-commit | 📅 Created: 2026-05-14
