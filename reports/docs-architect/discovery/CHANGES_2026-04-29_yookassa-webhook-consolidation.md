# CHANGES — 2026-04-29 — YooKassa webhook consolidation (14b)

## Summary

Webhook handler в `src/api/routers/billing.py::yookassa_webhook`
consolidated на новый `YooKassaService.process_webhook(...)`. Router
становится thin orchestrator: он делегирует authorization (IP whitelist)
+ payload parsing на сервис, ловит typed exceptions, и далее запускает
существующий business-logic путь (record updates → `BillingService.process_topup_webhook` → status mark → commit) — без изменений в этой части.

Closes 14b — финальный промт серии 15.x. Деferred from BL-034 (14a).

## What changed

### Added

- `YooKassaService.process_webhook(body: bytes, client_ip: str | None) -> WebhookEvent`
  in `src/core/services/yookassa_service.py`. Метод НЕ трогает БД, не
  открывает session, не commit'ит — S-48 contract preserved.
- `WebhookEvent` frozen dataclass:
  - `event_type: str` (e.g. `"payment.succeeded"`)
  - `payment_id: str` (YooKassa-side ID)
  - `payload: dict[str, Any]` (full `object` payload — caller извлекает
    `payment_method` / `receipt` / `metadata` по необходимости)
- `InvalidSignatureError` — raised когда client IP отсутствует, malformed,
  или вне `YOOKASSA_IP_NETWORKS`. Имя сохранено для protocol-vocabulary
  consistency; docstring уточняет что для YooKassa "signature" =
  IP whitelist (это документированный YooKassa механизм:
  https://yookassa.ru/developers/api/notifications#ip-address).
- `InvalidPayloadError` — raised на JSON parse failure либо отсутствии
  обязательных полей `event` / `object` / `object.id`.
- `YOOKASSA_IP_NETWORKS` — module-level tuple с CIDR-ами whitelist'а;
  перенесён из router'а.
- **Tests:** `tests/unit/test_yookassa_process_webhook.py` (12 unit
  tests — pure unit, no DB / no network):
  - 5 авторизация тестов (whitelisted IPv4, off-whitelist, missing,
    malformed, IPv6 whitelisted).
  - 6 payload validation тестов (invalid JSON, non-object body, missing
    event / object / payment_id, pass-through other event types).
  - 1 immutability test (frozen dataclass).

### Changed

- `src/api/routers/billing.py` webhook endpoint:
  - Удалены: inline IP-whitelist verification (`from ipaddress import ...`),
    JSON parsing через `request.json()`, локальный `YOOKASSA_IPS` constant.
  - Добавлены: вызов `YooKassaService.process_webhook(body_bytes, client_ip)`,
    translation `InvalidSignatureError` → HTTP 403, `InvalidPayloadError` →
    HTTP 200 + `{"status": "error", "detail": "Invalid webhook payload"}`
    (преserves "always 200 to disable YooKassa retries on bad payloads"
    behaviour).
  - Удалена константа `YOOKASSA_IPS` (теперь
    `YooKassaService.YOOKASSA_IP_NETWORKS`).
  - Business logic dispatch (record updates → `BillingService.process_topup_webhook`
    → status mark → commit) **не изменена** — те же вызовы, тот же commit
    в router, те же поля.

### Not changed

- Public contract:
  - URL: `POST /api/billing/webhooks/yookassa` — same.
  - Response shape: `{"status": "ok"}` (success) or
    `{"status": "error", "detail": "..."}` (errors), HTTP 200 always
    кроме IP mismatch (HTTP 403) — same as before.
  - Idempotency: `Transaction.yookassa_payment_id` + `meta_json["processed"]`
    в `BillingService.process_topup_webhook` — без изменений.
- `BillingService.process_topup_webhook` — body untouched.
- DB schema — без изменений, no migration.
- `tests/integration/test_billing_hotfix_bundle.py::test_topup_webhook_writes_transaction_with_yookassa_payment_id`
  — passes без модификаций (тестирует service напрямую, не HTTP layer).

## S-48 compliance

- `YooKassaService.process_webhook` не вызывает `session.begin()`,
  не делает `commit()`, не открывает session. Работает с pure bytes
  + str input, возвращает frozen DTO.
- Router остаётся outermost caller: открывает `async_session_factory()`,
  делает `await session.commit()` после business logic. Это уже было,
  не меняется.
- `BillingService.process_topup_webhook` — guard в
  `tests/test_billing_service_idempotency.py::test_process_topup_webhook_has_no_session_begin`
  passes (метод не trogаем).

## Affected files

```
src/api/routers/billing.py                      # endpoint refactored, YOOKASSA_IPS removed
src/core/services/yookassa_service.py           # +process_webhook +WebhookEvent +exceptions
tests/unit/test_yookassa_process_webhook.py     # NEW: 12 unit tests
reports/docs-architect/discovery/CHANGES_2026-04-29_yookassa-webhook-consolidation.md
CHANGELOG.md
```

## CI baseline (before / after on feature branch)

Pre-existing `make ci-local` baseline (BL-007 ruff drift; tests/ has 107
ruff errors unrelated to этого промта; `make ci-local` падает на ruff
tests/ step ещё до моих изменений). Поэтому baseline захватывался
покомпонентно:

| Check                                       | Before | After |
|---------------------------------------------|--------|-------|
| `poetry run ruff check src/`                | 21     | 21    |
| `poetry run ruff check tests/`              | 107    | 107   |
| `poetry run mypy src/`                      | 10     | 10    |
| `poetry run pytest test_billing_hotfix_bundle.py` | 6 pass | 6 pass |
| `poetry run pytest test_billing_service_idempotency.py` | 25 pass | 25 pass |
| `poetry run pytest test_no_dead_methods.py` | 3 pass | 3 pass |
| `poetry run pytest test_yookassa_create_topup_payment.py` | 4 pass | 4 pass |
| `poetry run pytest test_yookassa_process_webhook.py` | n/a | 12 pass (new) |

Net: +12 passing tests, no regressions, no new ruff/mypy errors.

## Public-contract verification

- URL preserved: `POST /api/billing/webhooks/yookassa`.
- Response shape preserved: `{"status": "ok"}` / `{"status": "error", ...}`.
- HTTP 403 only on IP-whitelist mismatch (same code path semantics, just
  different exception layer).
- HTTP 200 on bad payloads (preserves "no YooKassa retry" behaviour).
- Idempotency mechanism (`Transaction.yookassa_payment_id` +
  `meta_json["processed"]`) untouched.

## Origins

- BL-034 (14a) closure: process_topup_webhook consolidation deferred
  на 14b.
- Серия 15.x closure: 15.13 — финальный промт.
- IMPLEMENTATION_PLAN_ACTIVE.md серия 15.x table.

## Pre-existing diagnostics not addressed (scope discipline)

Surfaced during inventory but **deliberately not fixed** here (out of
scope; no plan item):

- `src/core/services/yookassa_service.py:333` — `payment.status` returns
  `Unknown | None` from yookassa SDK, declared return type `str`.
  Pre-existing in `get_payment_status`.
- `src/api/routers/billing.py:579` — `amount_paid` unpacked but unused
  in `change_plan` endpoint. Pre-existing.

These should be addressed in a dedicated cleanup промт if the team wants
to tighten the mypy baseline below 10 errors.

🔍 Verified against: `feature/yookassa-webhook-consolidation` HEAD | 📅 Updated: 2026-04-29
