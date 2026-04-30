# CHANGES — 17.2 Commit 1: meta_json keys rename

**Date:** 2026-05-01
**Branch:** feat/17-2-clean-sweep-persisted-credits
**Series:** 17.x (BL-053 umbrella)
**Closes:** Category A + F of 17.2 (per `PHASE_17_2_RESEARCH_2026-05-01.md`).

## Summary

Single-currency-RUB cleanup of persisted JSON keys in `Transaction.meta_json` and YooKassa create-topup response payload. Three keys renamed; one redundant key dropped entirely. Three integration-test fixtures follow.

## Changes

| Old | New | Sites |
|---|---|---|
| `meta_json["credits"]` (yookassa write + response payload) | `meta_json["amount_rub"]` | `yookassa_service.py:230, 246` |
| `meta_json["credited"]` (idempotency gate) | `meta_json["applied"]` | `billing_service.py:165, 166, 173, 189` |
| local var `credited = meta.get("credited")` | local var `applied = meta.get("applied")` | `billing_service.py:165, 166` (mirrors key) |
| `meta_json["rub_credited"]` (debug-only redundant copy of `Transaction.amount`) | **deleted** | `billing_service.py:174` (line removed) |
| test fixture `"credits"` | `"amount_rub"` | `test_bot_topup_handler.py:78`; `test_yookassa_create_topup_payment.py:85, 186` |

`billing_service.py:176` log line `"Payment {payment_id} credited: ..."` preserved as banking-verb usage (not a JSON key) — out of scope per inventory Category D filter.

## Files touched

- `src/core/services/yookassa_service.py` — 2 edits (meta write + response payload).
- `src/core/services/billing_service.py` — 4 edits (read, compare, write, payload) + 1 line removed (`rub_credited`).
- `tests/integration/test_bot_topup_handler.py` — 1 edit.
- `tests/integration/test_yookassa_create_topup_payment.py` — 2 edits.

## Verification

- `grep '"credits"\|"credited"\|"rub_credited"'` against the 4 touched files → 0 matches.
- `grep '\bcredited\b\|\brub_credited\b'` in `billing_service.py` → 1 match remaining at `:176` (banking-verb log message, preserved).
- Pre-prod: `transactions = 0` (verified earlier in session). No data migration needed.

## Out of scope (deferred)

- Enum values `credits_buy` / `admin_credit` → Commit 2.
- Pydantic schema `PlatformCreditRequest` + handler → Commit 3.
- URL paths `/credits/...` → 17.3.
- `User.credits` / `Badge.credits_reward` columns → future scope decision.
- FE TS interfaces (`BuyCreditsResponse`, etc.) → 17.3 bundle with URL rename.

## Baseline impact

Internal data-shape change only. No public API contract change (no Pydantic schema name, no URL, no OpenAPI operation_id). CHANGELOG.md not updated.

🔍 Verified against: HEAD prior to commit | 📅 Updated: 2026-05-01T00:00:00Z
