# CHANGES 2026-05-14 — BL-107 Phase B.2 (gate framework extension)

## Context

Gate framework extension layer для BL-107 (ФЗ-303 blogger registry verification).
Adds G19 dual implementation + new parallel registry `_CHANNEL_CONTEXT_GATE_CHECKERS`
для per-channel-context gates + orchestration method `check_gates_for_channel_add`.

Pure framework expansion: NO API/bot/Telegram-API/settings touches. Phase B.3+
will wire Telegram API integration, settings additions, channel-add invocations,
admin UI, periodic Celery task.

Design ref: `BL-107_DESIGN_2026-05-14.md` @ `38dbc94` (Phase A2 Marina-locked
decisions Q1-Q7 applied here).

Built atop Phase B.1 schema foundation (`4ab6d7c`) — G19 body reads:
- `TelegramChat.member_count`, `is_test`, `is_blogger_registry_verified`,
  `blogger_registry_application_number` (Phase B.1 additions)
- `ChannelAddContext` snapshot fields (Phase B.2 new dataclass)

## Changes

### Added — `PlacementGate` enum

- `G19_BLOGGER_REGISTRY_VERIFIED = "G19_BLOGGER_REGISTRY_VERIFIED"`
- Section comment: "Channel-add (owner-side, ФЗ-303 blogger registry — BL-107)"

### Added — `GateReason` enum (3 codes)

- `BLOGGER_REGISTRY_NOT_VERIFIED` — default fail (channel ≥10k, no verification, no manual evidence)
- `BLOGGER_REGISTRY_PENDING_REVIEW` — manual evidence submitted, admin review pending
- `SUBSCRIBER_COUNT_UNKNOWN` — reserved для Phase B.3 (Telegram API failure case при getChatMemberCount)
  — unused в Phase B.2 gate body; defined now to avoid Phase B.3 enum churn

### Added — `ChannelAddContext` dataclass

- New file: `src/core/schemas/channel_add_context.py`
- `@dataclass(frozen=True)` per design intent (pass-by-value snapshot semantics)
- Fields: `telegram_id`, `username`, `member_count`, `is_test=False`,
  `description=None`, `is_blogger_registry_verified=False`,
  `blogger_registry_application_number=None`
- Verification fields default False/None — Phase B.4 channel-add helper populates
  от Trustchannelbot admin check + DB lookup для re-adds
- `src/core/schemas/__init__.py` not touched (pure docstring package, no re-exports)

### Added — G19 implementation в `owner_gates.py`

Mirrors existing G04/G05/G06 dual-variant pattern (shared body + thin wrappers):

- **`_check_g19_core(member_count, is_test, is_verified, application_number) -> GateResult`** —
  pure logic, no I/O. Short-circuit precedence:
  1. `is_test=True` → exempt (admin carve-out)
  2. `member_count < _DEFAULT_RKN_THRESHOLD` → regulation not applicable
  3. `is_blogger_registry_verified=True` → pass
  4. `application_number is not None` → `BLOGGER_REGISTRY_PENDING_REVIEW` (block)
  5. default → `BLOGGER_REGISTRY_NOT_VERIFIED` (block)
- **`check_g19(session, placement)`** — placement-side variant. Reads
  `placement.channel` (TelegramChat) fields.
- **`check_g19_channel_add(session, user, channel_data)`** — channel-context variant.
  Reads `ChannelAddContext` snapshot fields.

Module constant: `_DEFAULT_RKN_THRESHOLD = 10_000` (Phase B.2 temporary state;
Phase B.3 replaces с `settings.rkn_threshold_subscribers`).

### Added — `LegalComplianceService` extensions

- **`ChannelContextGateCheckerFn`** type alias: `Callable[[AsyncSession, User,
  ChannelAddContext], Awaitable[GateResult]]`.
- **`_CHANNEL_CONTEXT_GATE_CHECKERS`** new parallel registry mapping
  `PlacementGate → ChannelContextGateCheckerFn`. Initial: `{G19 → check_g19_channel_add}`.
- **`_CHANNEL_ADD_GATES`** new resolution table — `frozenset[PlacementGate]` of
  gates that fire at channel-add time. Initial: `{G19}`.
- **`check_gates_for_channel_add(user, channel_data) -> list[GateResult]`**
  orchestration method. Iterates `_CHANNEL_ADD_GATES`, dispatches each gate
  через `_CHANNEL_CONTEXT_GATE_CHECKERS`. Pattern 1 (S-48): no transaction
  management; caller (API router в Phase B.4, bot handler в Phase B.4/B.7) owns
  session lifecycle.

### Modified — `_GATE_CHECKERS` (placement-side registry)

- Added: `G19_BLOGGER_REGISTRY_VERIFIED → owner_gates.check_g19` for defense-in-depth.

### Modified — `_TRANSITION_GATES`

G19 added к существующим entries (NOT new transition pairs):

- `(pending_owner, pending_payment)` → `{G07, G19}` (was `{G07}`)
- `(counter_offer, pending_payment)` → `{G07, G19}` (was `{G07}`)

Rationale: G19 placement-side fires alongside G07 supplementary agreement gate —
both block transition к pending_payment BEFORE money moves to escrow. Aligned
с design intent "G19 fires before placement creates contractual obligation".

### Added — tests

- `tests/unit/test_bl107_g19_gate.py` — 22 tests, pure unit (`AsyncMock(AsyncSession)`,
  no DB):
  - `TestCheckG19Core` (8 scenarios) — pure logic short-circuit precedence + boundaries
  - `TestCheckG19PlacementSide` (3) — `check_g19` reads TelegramChat correctly
  - `TestCheckG19ChannelAdd` (4) — `check_g19_channel_add` reads ChannelAddContext
  - `TestRegistryRegistration` (4) — _GATE_CHECKERS, _CHANNEL_CONTEXT_GATE_CHECKERS, _CHANNEL_ADD_GATES contents
  - `TestCheckGatesForChannelAdd` (3) — orchestration method end-to-end

### Modified — fixture for existing test

- `tests/unit/test_legal_compliance_service.py` parametrize table updated:
  `(pending_owner, pending_payment)` и `(counter_offer, pending_payment)` expected
  gate sets extended `{G07}` → `{G07, G19}` per modified `_TRANSITION_GATES`.
  Forced consequence of intended Phase B.2 change.

### Modified — contract drift snapshot

- `tests/unit/snapshots/gate_result_response.json` regenerated per FIX_PLAN_06 §6.1
  contract drift guard. Diff: single addition `"G19_BLOGGER_REGISTRY_VERIFIED"` к
  PlacementGate enum literal list in GateResultResponse JSON schema.

## Phase B.2 temporary state (surfaced Phase B.3 dependencies)

- `_DEFAULT_RKN_THRESHOLD = 10_000` hardcoded constant — Phase B.3 replaces с
  `settings.rkn_threshold_subscribers`. Single source of truth migration trivial
  (one constant → import).
- `remediation_url = None` в both G19 fail cases (NOT_VERIFIED + PENDING_REVIEW) —
  Phase B.5 populates after admin review / evidence submission UI screens ship.

## Verification

- `make typecheck`: 0/302 (was 0/301 — +1 channel_add_context.py)
- `make lint`: 7 errors (BL-024 baseline preserved — all 7 pre-existing in
  `tests/unit/conftest.py`; introduced one I001 in test file, auto-fixed via
  `ruff --fix`)
- `make format-check`: 420 files clean (was 418 — +2 new files)
- `alembic check`: drift-free (Phase B.2 не trogает schema)
- `pytest tests/unit/test_bl107_g19_gate.py -v`: 22/22 passing
- `pytest tests/unit/test_bl107_schema_regression.py -v`: 15/15 passing (Phase B.1)
- `pytest tests/unit/test_legal_compliance_service.py`: 17/17 passing
- `pytest tests/unit/test_owner_gates.py`: 34/34 passing
- Full unit test sweep: see Шаг 2.7 verification output

## Untouched (deferred к subsequent phases)

- **Phase B.3** — Telegram API integration: `verify_trustchannelbot_admin` helper,
  lazy in-memory cache, `settings.rkn_threshold_subscribers`,
  `settings.trustchannelbot_admin_id`, `settings.blogger_registry_check_interval_hours`.
- **Phase B.4** — Channel-add hookup: API router (`src/api/routers/channels.py`)
  + bot handler (`src/bot/handlers/owner/channel_owner.py`) wire
  `check_gates_for_channel_add` invocations alongside existing
  `check_gates_for_user_role` calls.
- **Phase B.5** — Admin review UI: 5 API endpoints + 2 web_portal screens + 1
  mini_app screen для manual_evidence review.
- **Phase B.6** — Celery periodic task `parser:check_channel_registry_status` для
  re-verification of existing channels.
- **Phase B.7** — O.7 carve-out closing (bot handler `is_test` parity).
- **Phase B.8** — BL-002 mock infrastructure (custom aiohttp stub +
  docker-compose.test.yml).
- **Phase B.9** — E2E tests + Playwright spec unblock.

## Decisions echoed (от Phase A2 design)

- Q2: Parallel registry с `(session, user, channel_data)` signature — confirmed
  appropriate (G19 evaluates per-channel state, not pure User context like G04/G05/G06).
- Q2 sub-decision: G19 dual registration (placement-side `_GATE_CHECKERS` AND
  channel-context `_CHANNEL_CONTEXT_GATE_CHECKERS`) — gives defense-in-depth для
  pre-G19 channels.
- Q3: Field naming `member_count_*` (NOT `subscriber_count_*`) — channel state
  reflected in TelegramChat fields naming convention; gate body uses matching
  parameter names.
- Pure gate body, no I/O — Trustchannelbot verification logic externalized к Phase
  B.3 helper (called by Phase B.4 channel-add hook BEFORE gate dispatch).
- `_DEFAULT_RKN_THRESHOLD` Phase B.2 module constant (NOT inline magic number);
  Phase B.3 replaces atomically с `settings.rkn_threshold_subscribers`.

🔍 Verified against: branch HEAD post-commit | 📅 Created: 2026-05-14
