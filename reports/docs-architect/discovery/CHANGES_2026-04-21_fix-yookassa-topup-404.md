# CHANGES 2026-04-21 — fix: web-portal top-up returned 404 on yookassa.ru/payment/{uuid}

## Problem

Web-portal users clicking "Оплатить" on the balance top-up screen were sent to URLs of the
form `https://yookassa.ru/payment/973414fa-0222-4c15-866e-9dff68d775b4`, which always
returned "Ошибка 404" from yookassa.ru.

Root cause: `BillingService.create_payment` fabricated a local UUID and a synthetic URL
string instead of calling the YooKassa SDK. No payment was ever registered with the
provider, so the redirect destination did not exist.

## Fix

`src/core/services/billing_service.py` — `BillingService.create_payment` now actually
creates the payment via the YooKassa Python SDK (`yookassa.Payment.create`, wrapped in
`asyncio.to_thread`) and stores the real `payment.id` and
`payment.confirmation.confirmation_url` on the `YookassaPayment` row.

Guards added:
- Raises `RuntimeError` if `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` are not configured.
- Raises `RuntimeError` if YooKassa does not return a confirmation URL.
- Propagates `yookassa.domain.exceptions.ApiError` up the stack (logged).

## Affected files

- `src/core/services/billing_service.py`
  - Added imports: `asyncio`, `yookassa.Configuration`, `yookassa.Payment`,
    `yookassa.domain.exceptions.ApiError`, `src.config.settings.settings`.
  - Rewrote the body of `create_payment` to perform a real API call instead of
    constructing `https://yookassa.ru/payment/{uuid}`.
  - DB schema for `YookassaPayment` is unchanged; the `payment_url` column now holds the
    real `confirmation_url` returned by YooKassa.

## Business logic impact

- Top-up flow from web-portal (`POST /api/billing/topup`) now returns a working
  confirmation URL (`https://yoomoney.ru/checkout/payments/v2/contract?...`) that lets
  the user actually pay.
- Webhook handling (`YooKassaService.handle_webhook`) continues to work: it looks up the
  `YookassaPayment` row by the YooKassa-issued `payment_id`, which is now identical to
  the ID stored at creation time.
- Transaction row (`transactions.yookassa_payment_id`) now references the real YooKassa
  payment ID, so reconciliation against YooKassa's dashboard is possible.

## API / FSM / DB contracts

- API: `POST /api/billing/topup` response schema unchanged (`TopupResponse`:
  `payment_id`, `payment_url`, `status`). Only the content of `payment_url` changed from
  a fake string to a real confirmation URL.
- FSM: no change.
- DB: no schema change. `yookassa_payments.payment_id` now holds YooKassa-issued IDs
  (previously a local UUID).

## Deploy

Rebuilt & recreated the api container:

```
docker compose up -d --build api
```

Container came up clean (uvicorn reloader running, no startup errors).

---
🔍 Verified against: 45bdb04 | 📅 Updated: 2026-04-21T14:51:25+03:00
