# CHANGES 2026-05-14 — BL-107 Phase B.1 (schema additions)

## Context

Foundation schema layer для BL-107 (ФЗ-303 blogger registry verification).
Adds verification state fields к `TelegramChat` + new Enum. Per Marina locked
design decision Q3+Q4: 7 net new fields с `member_count_*` naming (NOT
`subscriber_count_*`). Per BL-061 pre-prod exception: edited `0001_initial_schema.py`
вместо new revision.

Design ref: `BL-107_DESIGN_2026-05-14.md` @ `38dbc94`.

## Changes

### Added — `TelegramChat` model

- `is_blogger_registry_verified: bool` (NOT NULL, default False, server_default 'false')
- `blogger_registry_verified_at: datetime | None` (TIMESTAMP с timezone)
- `blogger_registry_application_number: str(64) | None` (Госуслуги application №)
- `blogger_registry_verified_by_admin_id: int | None` (FK users.id, ondelete SET NULL)
- `blogger_registry_verification_method: BloggerRegistryVerificationMethod | None`
- `member_count_at_verification: int | None` (snapshot для threshold-crossing detection)
- `last_blogger_registry_check_at: datetime | None` (periodic re-check timestamp)

### Added — Enum

- `BloggerRegistryVerificationMethod(StrEnum)` — values `trustchannelbot_admin`, `manual_evidence`
- File: `src/core/enums/blogger_registry.py`

### Modified — migration

- `0001_initial_schema.py`: enum type addition (`bloggerregistryverificationmethod`) + 7 new columns on `telegram_chats` table + FK constraint per pre-prod policy
- `alembic check` post-edit (post DB reset + re-upgrade): **No new upgrade operations detected** (drift-free)

### Added — tests

- `tests/unit/test_bl107_schema_regression.py` — 15 tests covering:
  - Enum contract (4): exact values, str subclass, individual member values
  - Column existence + nullability + FK ondelete (7)
  - ORM instantiation positive (3): unverified default, fully-populated, manual_evidence
  - Relationship preservation (1): existing relationships unaffected
- Pure introspection / ORM-level — no DB connection required
- All 15 pass

### Forced scope expansion — bidirectional FK disambiguation

Adding 2nd FK `blogger_registry_verified_by_admin_id → users.id` ambiguated existing `TelegramChat.owner ↔ User.telegram_chats` relationship (surfaced via `sqlalchemy.exc.AmbiguousForeignKeysError` на mapper init). SQLAlchemy requires explicit `foreign_keys=` argument on both sides of bidirectional `back_populates` pair when ≥2 FK paths link the same tables. One-line fix on each model:

- `src/db/models/telegram_chat.py` L106: `foreign_keys=[owner_id]` added к existing `owner` relationship
- `src/db/models/user.py` L112-117: `foreign_keys="TelegramChat.owner_id"` added к existing `telegram_chats` back-relationship

**Reason:** SQLAlchemy AmbiguousForeignKeysError при 2+ FK paths к same target. Both sides bidirectional relationship require explicit `foreign_keys=`. **No behavior change, schema layer scope** — forced by ORM mapper init requirement, не discretionary. Surfaced by schema regression tests in 2.4.

## Verification

- `make typecheck`: 0 errors (300 → 301 files, +blogger_registry.py)
- `make format-check`: clean (418 files)
- `make lint`: 7 errors (BL-024 baseline preserved — no new violations)
- `alembic check`: drift-free
- `pytest tests/unit/test_bl107_schema_regression.py -v`: 15/15 passing
- Stop-hook discipline: 0 fires (BL-113 fix active)

## Untouched (deferred к subsequent phases)

- Gate framework (Phase B.2): `PlacementGate.G19_*`, `GateReason` codes, `_CHANNEL_CONTEXT_GATE_CHECKERS` registry, `check_g19_channel_add` + `check_g19` checkers
- Telegram API integration (Phase B.3): `verify_trustchannelbot_admin`, lazy cache, settings additions
- Channel-add hookup (Phase B.4): API router + bot handler integration of `check_gates_for_channel_add`
- Admin review UI (Phase B.5): 5 API endpoints + 2 web_portal screens + 1 mini_app screen
- Celery periodic task (Phase B.6): `parser:check_channel_registry_status`
- O.7 carve-out (Phase B.7): bot handler `is_test` parity
- BL-002 mock infrastructure (Phase B.8): custom aiohttp stub + docker-compose.test.yml
- E2E tests (Phase B.9): Playwright spec unblock

## Migration Notes

Pre-production DB reset выполнен в Pre-Шаг 0.5: DROP DATABASE + CREATE DATABASE + `alembic upgrade head` applied edited 0001 + e6a88faa9fa0 chain cleanly. `alembic check` drift-free.

First production user deploy precondition: this consolidated 0001 edit pattern terminates после first user; subsequent migrations будут incremental revisions per standard Alembic rules (CLAUDE.md).

🔍 Verified against: branch HEAD post-commit | 📅 Created: 2026-05-14
