# CHANGES — 2026-04-30 — PII encryption at rest (16.2 / Group B)

## Summary

Series 16.x Group B — encrypt PII at rest. `PayoutRequest.requisites`
и `DocumentUpload.ocr_text` columns переведены с plaintext на
`EncryptedString` (Fernet TypeDecorator). Pre-prod migration policy:
`0001_initial_schema.py` обновлён directly (no new Alembic revision).

Closes:

- **BL-047** (HIGH-3: `DocumentUpload.ocr_text` plaintext at rest, ФЗ-152).
- **BL-048** (HIGH-4: `PayoutRequest.requisites` plaintext at rest, ФЗ-152).

(Note: prompt 16.2 had BL-047/BL-048 mapping inverted from BACKLOG.md;
authoritative source is BACKLOG → BL-047 = ocr_text, BL-048 = requisites.)

## Шаг 0 audit findings

### EncryptedString infrastructure (production-ready)

- Definition: `src/core/security/field_encryption.py:24`.
- Type: `TypeDecorator` (impl=`String`), Fernet AES-128-CBC + HMAC-SHA256.
- Null-safe: `None` stays `None`. Legacy plaintext fallback returns
  `None` + warning (handles a partial-migration scenario gracefully).
- Key source: `settings.field_encryption_key` (env: `FIELD_ENCRYPTION_KEY`,
  required Field with `...`). Key configured в `.env`.
- Existing usage (production-tested):
  - `src/db/models/legal_profile.py` — 12 fields (inn, kpp, bank_*,
    passport_*, file_id scans).
  - `src/db/models/platform_account.py` — 3 fields (inn, bank_account,
    bank_corr_account).
- Sibling `HashableEncryptedString` — for searchable hashed columns
  (e.g. `inn_hash`); not needed for our case (no WHERE/filter usage).

### `PayoutRequest.requisites` pre-state

- Model: `src/db/models/payout.py:41`, `String(512)`, `nullable=False`.
- Migration: `0001_initial_schema.py:694`, `sa.String(512)`, NOT NULL.
- Read sites (2):
  - `src/api/routers/payouts.py:188` — write at PayoutRequest creation.
  - `src/api/routers/admin.py:1108` — `_payout_to_admin_response` reads
    plaintext into `AdminPayoutResponse`.
- Schema exposure (2):
  - `PayoutResponse.requisites` (`src/api/schemas/payout.py:43`) —
    owner viewing own payout.
  - `AdminPayoutResponse` (subclass) — admin viewing all payouts.
- Filter / WHERE / `==` clauses: **none** — safe to encrypt without
  search-hash workaround.
- Tests touching field: 4 files (`test_payout_lifecycle.py`,
  `test_payout_concurrent.py`, `test_escrow_payouts.py`,
  `test_admin_payouts.py`).

### `DocumentUpload.ocr_text` pre-state

- Model: `src/db/models/document_upload.py:47`, `Text`, nullable.
- Migration: `0001_initial_schema.py:381`, `sa.Text()`, nullable.
- Write site (1): `src/tasks/document_ocr_tasks.py:132` — bulk update
  via `update_values` dict, capped at 10 000 chars.
- Read sites: zero in routers, schemas, services. Pure internal storage.
- API exposure: **none** (not present in any Pydantic response model).
- Filter / WHERE / `==` clauses: **none**.
- Tests touching field: zero.

### Migration file convention (verified)

`0001_initial_schema.py` docstring (lines 10-14) explicitly states
encrypted columns are stored as raw `VARCHAR/TEXT` in PostgreSQL —
encryption is ORM-level only via `EncryptedString`. Existing precedent:

- `legal_profiles.inn` (model: `HashableEncryptedString(300)`) → migration:
  `sa.String(300)`.
- `legal_profiles.passport_issued_by` (`EncryptedString(1000)`) →
  `sa.String(1000)`.
- `platform_account.inn` (`HashableEncryptedString(300)`) → `sa.Text()`.

We follow this convention: model declares `EncryptedString(N)`, migration
keeps a raw SA type sized to fit the encrypted Fernet token (~ 4/3 base64
expansion of the padded ciphertext).

### Pre-existing test failures (BL-054 collection)

Verified pre-existing via `git stash`:

- `tests/unit/test_escrow_payouts.py` — SQLite test infra fails to
  create `placement_requests` table (`no such table` on INSERT).
  Unrelated к этому изменению.
- `tests/unit/test_main_menu.py` (per 16.1 closure note) — collection
  error.
- `tests/unit/test_start_and_role.py` + bot-side tests (per 16.1) —
  ~62 failures.

Recorded as **BL-054** for future test infra cleanup; not blocking 16.2.

## What changed

### Models

- `src/db/models/payout.py:11,41` — added `EncryptedString` import;
  `requisites` column type `String(512)` → `EncryptedString(2048)`.
  Length raised because Fernet token of 512 cyrillic UTF-8 chars
  (≤ 1024 bytes plaintext) → ≤ 1464 base64 chars; 2048 leaves headroom.
- `src/db/models/document_upload.py:9,47` — added `EncryptedString` import;
  `ocr_text` column type `Text` → `EncryptedString(50000)`. Capped write
  at 10 000 chars (per `document_ocr_tasks.py:132`); cyrillic UTF-8 → up
  to ~30 KB plaintext bytes → ~40 KB Fernet base64; 50 000 leaves
  headroom.

### Migration (pre-prod policy: edit-in-place)

- `src/db/migrations/versions/0001_initial_schema.py:694` —
  `sa.String(512)` → `sa.String(2048)` for `requisites` to fit encrypted
  bytes.
- `src/db/migrations/versions/0001_initial_schema.py:381` — `sa.Text()`
  for `ocr_text` already accommodates encrypted output (unbounded);
  no change needed.
- Docstring (lines 10-14) updated to list the two new encrypted columns.
- `alembic upgrade head --sql` preview compiles cleanly:
  `requisites VARCHAR(2048) NOT NULL`, `ocr_text TEXT`.

### Tests

- `tests/integration/test_pii_encryption_at_rest.py` (new, 96 lines, 2
  tests):
  - `test_payout_request_requisites_encrypted_at_rest` — ORM round-trip
    returns plaintext; raw SQL `SELECT requisites` returns Fernet token
    starting with `gAAAAA…` (Fernet version byte 0x80 → URL-safe base64).
  - `test_document_upload_ocr_text_encrypted_at_rest` — same pattern,
    multi-line cyrillic passport-shaped payload (~1.5 KB).
- Existing payout tests (`test_payout_lifecycle.py`,
  `test_payout_concurrent.py`, `test_admin_payouts.py`) pass without
  modification: 16/16 ✓.

### Not changed

- Business logic in payout / document services.
- Auth pinning (16.1 done).
- Pydantic response schemas (`PayoutResponse.requisites` etc. — owners
  see own; admin pin via 16.1; encryption at rest still meaningful for
  DB-breach scenarios).
- Bot payout flow (16.3 architectural decision).
- `UserResponse` referral leak (16.4).
- `PlatformSettings.bank_*` (already `EncryptedString`).

## Schema response leak — surface (no fix here)

Inventory in Шаг 0.8:

- `PayoutResponse.requisites` (`src/api/schemas/payout.py:43`) — exposes
  decrypted requisites in API responses.
  - **Owner endpoint** (`GET /api/payouts/{id}`): pinned to web_portal in
    16.1; owner sees own requisites for verification → **acceptable by
    design**.
  - **Admin endpoint** (`GET /api/admin/payouts/*`): pinned to web_portal
    in 16.1; admin needs requisites to execute payout → **acceptable**.
  - Encryption at rest still meaningful: protects DB-only breach
    scenarios (backup leaks, read replicas, snapshot exfil) which are
    independent of API access.
- `DocumentUpload.ocr_text`: zero API exposure → no leak surface.

No new BL filed — both `requisites` exposures are accepted by design.

## CI baseline

| Check | Before | After | Notes |
|-------|--------|-------|-------|
| ruff src/ | 21 | 21 | Unchanged. New test file passes ruff. |
| mypy src/db/models/payout.py | 0 | 0 | Touched files clean. |
| mypy src/db/models/document_upload.py | 0 | 0 | Touched files clean. |
| pytest payout suite (16 tests across 3 files) | 16 pass | 16 pass | No regressions. |
| pytest new regression file | n/a | 2 pass | Added. |

Pyright in IDE may surface `_declared_directive[str]` warnings on
`__tablename__` lines (payout.py:32, document_upload.py:15) — these are
**pre-existing** SQLAlchemy 2.0 typing quirks unrelated to this change;
they fired on touched files because Pyright re-evaluates files on edit.

## Origins

- PII audit `PII_AUDIT_2026-04-28.md` § O.3 (BL-047), Часть 1.2 + § 2.2
  (BL-048).
- Pre-prod migration policy (CLAUDE.md "Migration Strategy").
- 16.x series plan; 16.1 (Group A — auth pinning) closed 2026-04-29.
