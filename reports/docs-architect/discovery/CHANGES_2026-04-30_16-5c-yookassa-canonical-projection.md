# CHANGES — 2026-04-30 — 16.5c YooKassa webhook canonical projection

**Series:** 16.x (final implementation step before closure metadata)
**BL:** BL-051 sub-task 6 (last open) — closes the LOW-batch BL-051 series.
**Branch:** `feature/16-5c-yookassa-over-collection-trim` (off develop `21ad121`)
**Commits:** `9c964f9`, `dafb700`, `a81d577`, this report.

## Goal

YooKassa `payment.succeeded` webhook persisted the **full** webhook
``object`` payload to the JSONB column `YookassaPayment.yookassa_metadata`
at `src/api/routers/billing.py:731`. That payload contains customer PII
(`receipt.customer.{full_name,inn,email,phone}`), card PAN fragments
(`payment_method.card.{first6,last4}`), and YooKassa-internal transport
identifiers (`recipient.{account_id,gateway_id}`, `payment_method.id`,
`confirmation.confirmation_url`) that we have no business retention
basis for. Per the Шаг 0 audit nothing in the codebase reads these
fields back out, so dropping them is safe. This change replaces the
direct assignment with a canonical projection function that retains
fiscal/audit data (УСН/КУДиР reconciliation, dispute resolution) and
our own roundtrip metadata, while dropping PII and transport.

## Шаг 0 — Empirical inventory

### Readers audit

```bash
grep -rn "yookassa_metadata" src/ tests/ --include="*.py"
```

| Location | Role | Notes |
|---|---|---|
| `src/api/routers/billing.py:731` | **WRITER** (only one) | Full payload assignment; this is the call we're changing. |
| `src/db/models/yookassa_payment.py:37` | model definition | `Mapped[dict[str, Any] \| None]` JSONB column. |
| `src/db/migrations/versions/0001_initial_schema.py:861` | migration | `sa.Column("yookassa_metadata", postgresql.JSONB(), nullable=True)`. |

**Readers in `src/`:** 0.
**Readers in `tests/`:** 0.

The two adjacent reads at `billing.py:724-725` operate on `event.payload`
(the upstream DTO), not on `record.yookassa_metadata`, and they extract
`payment_method.type` → `record.payment_method_type` and
`receipt.id` → `record.receipt_id` into normalised columns BEFORE the
projection. So those values continue to be persisted; only the JSONB
shadow copy is trimmed.

### Payload structure inventory

Sources used (in priority order):

1. JSON fixtures: **none** for YooKassa (only `tests/fixtures/yandex_ord/*`).
2. Existing parser code: `src/core/services/yookassa_service.py`
   `WebhookEvent.payload: dict[str, Any]` — no Pydantic schema; only
   `event`, `object`, `object.id` are validated structurally.
3. Existing test sample: `tests/unit/test_yookassa_process_webhook.py`
   `_valid_body()` — minimal; covers `id`, `status`, `amount`,
   `payment_method.type`, `receipt.id`, `metadata`.
4. YooKassa public API: `https://yookassa.ru/developers/api#payment_object`
   for the full field set.

### Categorization matrix

| key_path | category | rationale |
|---|---|---|
| `id` | FISCAL | payment UUID, audit trace |
| `status` | FISCAL | succeeded/canceled/etc — dispute relevance |
| `amount` | FISCAL | gross amount |
| `income_amount` | FISCAL | net (post-YK fee) — КУДиР |
| `paid` | FISCAL | bool flag |
| `captured_at` | FISCAL | capture timestamp |
| `created_at` | FISCAL | creation timestamp |
| `expires_at` | FISCAL | expiry timestamp |
| `description` | FISCAL | platform-set text, audit-relevant |
| `refundable` | FISCAL | bool |
| `refunded_amount` | FISCAL | refund ledger |
| `receipt_registration` | FISCAL | fiscal status string |
| `cancellation_details` | FISCAL | party + reason for canceled |
| `authorization_details` | FISCAL | rrn, auth_code, 3DS flags |
| `transfers` | FISCAL | split payments |
| `deal` | FISCAL | deal info |
| `metadata` | ROUNDTRIP | our `user_id`/`desired_balance`/etc |
| `test` | TRANSPORT | sandbox flag — retained for diagnostic |
| `recipient` (subtree) | TRANSPORT | YK internal IDs — drop |
| `payment_method` (subtree) | drop | type already in normalized column; card.first6/last4 PCI; account_number PII for yoo_money |
| `confirmation` (subtree) | drop | consumed pre-success, transport |
| `merchant_customer_id` | drop | customer-identifying — drop (not currently set, future-proof) |
| `receipt.id` | FISCAL | also normalized; retained for completeness |
| `receipt.items` | FISCAL | line items, supplier info is ours |
| `receipt.tax_system_code` | FISCAL | СНО |
| `receipt.registered_at` | FISCAL | fiscal registration ts |
| `receipt.fiscal_provider_id` | FISCAL | OFD provider |
| `receipt.fiscal_document_number` | FISCAL | fiscal doc № |
| `receipt.fiscal_storage_number` | FISCAL | kassa serial |
| `receipt.fiscal_attribute` | FISCAL | fiscal stamp |
| `receipt.type` | FISCAL | payment/refund |
| `receipt.status` | FISCAL | receipt status |
| `receipt.customer` (subtree) | PII | full_name/inn/email/phone — drop per ФЗ-152 |

### STOP gate

Clean: 0 readers depend on drop-fields, payload structure understood
from parser code + YK API, 0 ambiguous categories. Proceeded without
approval gate per "inventory-clean path, design pre-approved".

## Шаги 1–3 summary

### Шаг 1 — `src/utils/yookassa_payload.py` (commit `9c964f9`)

New module mirroring the `src/utils/pii_keys.py` pattern (16.5b):

- Module docstring with category definitions, rationale, and
  "Adding a new field" instructions.
- Four `frozenset[str]` constants:
  - `FISCAL_TOP_LEVEL` (16 keys)
  - `RECEIPT_FISCAL_FIELDS` (10 keys, allow-list within `receipt`)
  - `ROUNDTRIP_TOP_LEVEL` (1 key: `metadata`)
  - `TRANSPORT_TOP_LEVEL` (1 key: `test`)
- `extract_persistable_metadata(payload: dict[str, Any] | None)
  -> dict[str, Any]` — pure projection function, returns new dict,
  no input mutation, defensive against `None` / non-dict input.

### Шаг 2 — `tests/unit/utils/test_yookassa_payload.py` (commit `dafb700`)

17 unit tests covering:

- FISCAL retention (top-level + receipt subtree, every constant key
  asserted)
- ROUNDTRIP / TRANSPORT retention
- Drops: `recipient`, `payment_method`, `confirmation`,
  `merchant_customer_id`, `receipt.customer`
- Edge cases: `{}`, `None`, non-dict (list), `receipt: None`,
  `receipt: {}`, receipt with PII-only
- Immutability: result is a new dict, sample never mutated

Created `tests/unit/utils/__init__.py` (new package, mirrors
existing `tests/unit/api/`, `tests/unit/services/` convention).

### Шаг 3 — `src/api/routers/billing.py` (commit `a81d577`)

- Added import: `from src.utils.yookassa_payload import extract_persistable_metadata`
- Replaced `record.yookassa_metadata = event.payload  # сохраняем полный payload`
  with `record.yookassa_metadata = extract_persistable_metadata(event.payload)`
- Single callsite changed; no transaction or DTO-level touches.
  S-48 contract preserved (router still owns transaction lifecycle).
- Incidental `ruff format` cleanup of two adjacent multi-line `quantize`
  statements (Decimal arithmetic, line ~371-376) — no behavioural
  change.

## Verify gates results — `make ci-local`

Baseline numbers from `pytest --no-cov --tb=short` (post-BL-057
aggregate-exit ci-local form):

| Stage | Pre-16.5c (develop `21ad121`) | Post-16.5c (`a81d577`) | Delta |
|---|---|---|---|
| Lint (ruff check) | 128 errors | 128 errors | 0 (BL-058 baseline) |
| Format-check (ruff format --check) | 83 files | 82 files | -1 (billing.py now clean) |
| Typecheck (mypy src/) | ~6 reported in tail | unchanged | 0 (pre-existing; 529 total per CLAUDE.md) |
| Tests passed | 736 | **753** | +17 (new yookassa_payload tests) |
| Tests failed | 76 | **76** | 0 (no regressions) |
| Tests skipped | 7 | 7 | 0 |
| Test errors | 17 | 17 | 0 |

`make ci-local` exits non-zero overall (baseline lint + test failures
hold). Same exit semantics as before. No new failure modes.

Targeted yookassa test run (`pytest tests/unit/test_yookassa_*.py
tests/unit/test_billing.py tests/unit/utils/test_yookassa_payload.py`):
49 passed / 1 failed. The 1 failure is
`TestEscrowReleaseLocation::test_release_escrow_only_in_delete_published_post`
— a grep-based source scan that catches a `release_escrow()` mention
in a code comment in `src/api/routers/disputes.py:595`. Pre-existing
in the 76-failed baseline, unrelated to 16.5c.

## Drops summary (legal/compliance audit trail)

After 16.5c, the following fields **NO LONGER PERSIST** to
`YookassaPayment.yookassa_metadata`:

**Top-level subtrees dropped:**

- `recipient.account_id`, `recipient.gateway_id` — YK shop/gateway internal IDs
- `payment_method.id` — YK internal payment-method UUID
- `payment_method.saved`, `payment_method.title` — UX hints
- `payment_method.card.first6` — card BIN (issuer fingerprint)
- `payment_method.card.last4` — card PAN tail
- `payment_method.card.expiry_month`, `expiry_year` — card expiry
- `payment_method.card.card_type`, `issuer_country`, `issuer_name`,
  `card_product` — card brand + issuer metadata
- `payment_method.account_number` (yoo_money) — wallet number (PII)
- `payment_method.phone` (mobile_balance) — phone (PII)
- `confirmation.type`, `confirmation.confirmation_url` — redirect URL
  (consumed pre-success)
- `merchant_customer_id` — customer-identifying token (we don't set
  this currently; defensive future-proof drop)

**Within `receipt` subtree dropped:**

- `receipt.customer.full_name` — ФЗ-152 PII
- `receipt.customer.inn` — ФЗ-152 PII (taxpayer ID)
- `receipt.customer.email` — ФЗ-152 PII
- `receipt.customer.phone` — ФЗ-152 PII

**Retained** (reasoning per category in `src/utils/yookassa_payload.py`
docstring):

- All FISCAL fields needed for УСН/КУДиР reconciliation, fiscal
  receipt reproduction, banking trace (rrn/auth_code/3DS), refund
  ledger, dispute resolution.
- `metadata` (our roundtrip — `user_id`, `desired_balance`,
  `fee_amount`, `gross_amount`).
- `test` flag (sandbox diagnostic).

Note: `payment_method.type` (e.g. `bank_card`, `sbp`) and `receipt.id`
remain available via the **normalized columns**
`YookassaPayment.payment_method_type` and `YookassaPayment.receipt_id`
populated at write time (`billing.py:727-730`) before the JSONB
projection applies.

## Open follow-ups (informational; no action required in this commit)

- **Fiscal-fields retention period review** (BL-059 candidate, deferred):
  no formal retention policy yet exists for the `yookassa_metadata`
  JSONB. КУДиР / 54-ФЗ require ~5 years for fiscal documents.
  Implementing retention would touch `YookassaPayment` model + a
  cleanup task, out of scope for the LOW-batch trim work.
- **Already-persisted records** before 16.5c retain the wide payload.
  Backfill pruning would be a one-shot data migration; not landed in
  this commit. The trim begins at next webhook write.
- BL-058 (ruff 128 + format ~82 baseline cleanup) remains deferred per
  series 16.x policy.

## Files touched

- **New:** `src/utils/yookassa_payload.py`
- **New:** `tests/unit/utils/__init__.py`
- **New:** `tests/unit/utils/test_yookassa_payload.py`
- **Modified:** `src/api/routers/billing.py` (1 import + 1 assignment + ruff-driven cosmetic format on lines ~371-376)
- **New:** `reports/docs-architect/discovery/CHANGES_2026-04-30_16-5c-yookassa-canonical-projection.md` (this file)

## Anything surprising

- During inventory the `feature/16-5b-pii-keys-canonical` and
  `feature/makefile-split-lint-test` branches were unmerged on develop
  despite the handoff prose claiming both were closed. Resolved by
  PROMPT A merging both into develop in the correct order before
  starting 16.5c. Documented in transcript; develop tip moved
  `8eb2de7a` → `21ad121` over those two `--no-ff` merges. From this
  branch's perspective develop = `21ad121` is the empirical base.
- Pyright initially flagged `return {}` at line 105 of
  `yookassa_payload.py` as unreachable code under the original
  `payload: dict[str, Any]` signature. Resolved by widening to
  `dict[str, Any] | None` — this is the genuine input domain (caller
  may pass `None` defensively) and matches the test contract
  (`extract_persistable_metadata(None) → {}`).

🔍 Verified against: `a81d577` | 📅 Updated: 2026-04-30
