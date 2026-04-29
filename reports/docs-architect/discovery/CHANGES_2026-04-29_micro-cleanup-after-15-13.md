# CHANGES — 2026-04-29 — Micro-cleanup after 15.13 (15.13.1)

## Summary

3 follow-up tasks from 15.13 closure отчёта. Scope-bounded defensive
cleanup. **No public contract changes, no business logic changes.**

Closes серия 15.x окончательно.

## Distortion note

15.13 closure отчёт surface'ил два code observations как "pre-existing
diagnostics". Промт 15.13.1 v1 интерпретировал их как tool-flagged
baseline issues и заявлял `mypy: 10 → 9`, `ruff: 21 → 20`. Шаг 0
empirical verification показал: оба issue ниже mypy detection threshold
(yookassa SDK Any-pollution / tuple-unpack F841 gap). Pyright detect'ит
оба после edit, mypy не видит. v1 прерван на Шаг 0, v2 переписан без
false baseline claims. BL-015 паттерн.

## What changed

### Renamed
- `InvalidSignatureError` → `WebhookAuthError` in
  `src/core/services/yookassa_service.py:63` (class definition + 3 raises
  at lines 289, 293, 295) + caller in `src/api/routers/billing.py:687,697`
  + tests in `tests/unit/test_yookassa_process_webhook.py:18,59,65,71`.
- Reason: YooKassa использует IP whitelist (not HMAC); previous name
  implied cryptographic signature. New docstring also future-proofs для
  HMAC-based providers если добавятся позже.

### Changed (type honesty, not bug fix)
- `YookassaService.get_payment_status` return type: `str` → `str | None`
  (`src/core/services/yookassa_service.py:322`). Implementation hardened:
  `getattr(payment, "status", None)` + `isinstance(status, str)` check.
- Single caller `src/bot/handlers/billing/billing.py:150` updated:
  explicit `if status is None:` guard with warning log + UX message
  "статус пока неизвестен" (вместо misleading "не прошёл" fallback).
- 4 new unit tests in `tests/unit/test_yookassa_get_payment_status.py`
  covering: succeeded path, missing status attribute, status=None,
  non-string status. All pass.

### Changed (defensive cleanup)
- `src/api/routers/billing.py:579` `buy_credits` endpoint: removed unused
  `amount_paid, _, _ = await ...` unpack. Replaced with bare
  `await billing_service.buy_credits_for_plan(...)` since return tuple
  целиком не нужен (call для side effect — raises на insufficient).
- Verified: `BillingService.buy_credits_for_plan` deducts ровно `amount_rub`
  или raises `InsufficientFundsError`. Нет partial credit / discount /
  promo logic — `amount_paid == int(body.desired_amount)` всегда. Не
  money-bug.

### Not changed
- Public webhook contract: URL `/api/billing/webhooks/yookassa`, response
  shape `{"status": "ok"|"error", ...}`, status codes (403 на IP mismatch),
  idempotency.
- `YookassaService.process_webhook` and `BillingService.process_topup_webhook`
  business logic.
- DB schema, migrations, Celery routing.
- mypy / ruff baselines (см. ниже).

## CI baseline (honest)

| Check | Before | After | Note |
|-------|--------|-------|------|
| mypy src/ | 10 errors in 5 files | 10 | Touched lines below mypy threshold (Any-pollution) |
| ruff src/ | 21 errors | 21 | Touched lines below ruff F841 threshold (tuple-unpack gap) |
| pytest test_yookassa_process_webhook | 12 pass | 12 pass | Rename only |
| pytest test_yookassa_get_payment_status | (new) | 4 pass | None handling tests |

**Honest:** no baseline reduction. Defensive cleanup + type honesty.

## Plan + BACKLOG updates

- `IMPLEMENTATION_PLAN_ACTIVE.md` Status overlay: серия 15.x → ✅ DONE
  2026-04-29; new row 15.13.1 added to series table.
- `reports/docs-architect/BACKLOG.md`: BL-052 added (CLOSED).

## Files changed

- `src/core/services/yookassa_service.py` (rename + return type fix)
- `src/api/routers/billing.py` (rename + unused unpack removed)
- `src/bot/handlers/billing/billing.py` (None-guard for get_payment_status)
- `tests/unit/test_yookassa_process_webhook.py` (rename in imports + raises)
- `tests/unit/test_yookassa_get_payment_status.py` (new — 4 tests)
- `IMPLEMENTATION_PLAN_ACTIVE.md` (status overlay)
- `reports/docs-architect/BACKLOG.md` (BL-052 added)
- `reports/docs-architect/discovery/CHANGES_2026-04-29_micro-cleanup-after-15-13.md` (this file)
- `CHANGELOG.md` (Unreleased entry)

## Origins

- 15.13 closure отчёт (Surprises section + pre-existing diagnostics).
- Серия 15.x final closure.
- v1 → v2 rewrite после Шаг 0 STOP gate (premise mismatch на baseline
  claims).

🔍 Verified against: develop @ 7b61e82 | 📅 Updated: 2026-04-29
