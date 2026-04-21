# Yandex ORD API v7 — Integration Notes

**Status**: stub provider in use (`ORD_PROVIDER=stub`); real provider
`YandexOrdProvider` already implemented at
`src/core/services/yandex_ord_provider.py` but not yet wired with a real
sandbox key. This document summarises what the provider sends and expects,
and how to obtain sandbox access before go-live.

Canonical source of truth for endpoint shapes: the provider implementation
itself (`src/core/services/yandex_ord_provider.py`). The public Yandex ORD
API documentation (https://ord.yandex.ru/api/doc) requires authentication
to read — credentials procedure is below.

---

## 1. Sandbox access procedure

Yandex ORD does **not** offer a self-serve sandbox. Access is granted only
after a legal agreement with Yandex as an ОРД operator.

**Required steps before switching `ORD_PROVIDER=yandex`:**

1. Register a legal entity on https://ord.yandex.ru (the РекХарбор LLC
   profile must already be set up — see `ord_rekharbor_org_id` and
   `ord_rekharbor_inn` in `src/config/settings.py`).
2. Sign a contract with Yandex as an ОРД operator ("договор с оператором
   рекламных данных"). This is a paper contract with КЭП.
3. After contract activation, request API credentials via Yandex support:
   a Bearer token (`ORD_API_KEY`) and base URL (`ORD_API_URL`, typically
   `https://api.ord.yandex.net/v7` for production or
   `https://api-sandbox.ord.yandex.net/v7` if Yandex provisions a staging
   environment — the exact value is provided with the credentials).
4. Verify the token in curl against `GET /api/v7/status?reqid=...` with
   any fake reqid — a 401 means the token is invalid, a 404 confirms
   auth works but the reqid is unknown.

Until those steps are complete, the stub provider (`StubOrdProvider`)
issues synthetic `STUB-ERID-*` tokens and the mock-based test suite in
`tests/unit/test_yandex_ord_provider.py` exercises the real provider's
request/response shape without hitting the network.

---

## 2. Authentication

- Header: `Authorization: Bearer <ORD_API_KEY>`.
- Additional headers: not required.
- Timeouts: 30s (provider default).
- Rate limits: not published publicly; provider raises
  `OrdRegistrationError` on 5xx — caller is responsible for retry.

---

## 3. Endpoints in use (API v7)

All methods use JSON request/response. Base URL is `ORD_API_URL`.

### 3.1 `POST /api/v7/organization` — register advertiser

Request body (`register_advertiser`):

```json
{
  "id": "org-<user_id>",
  "inn": "<advertiser_inn>",
  "isOrs": false,
  "isRr": false,
  "name": "<legal_name>"
}
```

- `id`: stable `org-{user_id}` — acts as idempotency key; Yandex upserts.
- `isOrs`: `false` — РекХарбор is a regular rekladodatel, not OPC.
- `isRr`: `false` — not a rekladoraspragatel (that flag is for the
  platform registration instead).

Response: organisation object with the same `id` echoed back. 2xx = OK.

### 3.2 `POST /api/v7/platforms` — register Telegram channel as platform

Request body (`register_platform`):

```json
{
  "organizationId": "<ord_rekharbor_org_id>",
  "platforms": [
    {
      "platformId": "platform-<channel_id>",
      "type": "site",
      "name": "<channel_name>",
      "url": "https://t.me/<channel_username>",
      "isOwned": false
    }
  ]
}
```

- `platformId`: stable `platform-{channel_id}`.
- `type`: `"site"` is the correct value for Telegram channels in Yandex ORD.
- `isOwned: false` — РекХарбор does not own the channel, owner does.

### 3.3 `POST /api/v7/contract` — register placement contract

Request body (`register_contract`):

```json
{
  "id": "contract-<placement_request_id>",
  "type": "contract",
  "contractorId": "<ord_rekharbor_org_id>",
  "clientId": "<advertiser_ord_id>",
  "isRegReport": true,
  "date": "YYYY-MM-DD",
  "amount": "<amount_rub>",
  "subjectType": "distribution"
}
```

- РекХарбор is the `contractorId` (исполнитель/РР).
- Advertiser is the `clientId` (заказчик/РД).
- `subjectType: "distribution"` — платформа распространяет рекламу.
- `isRegReport: true` — РекХарбор отчитывается в ЕРИР сам.

### 3.4 `POST /api/v7/creative` — register the ad creative, obtain erid

Request body (`register_creative`):

```json
{
  "id": "creative-<placement_request_id>",
  "creativeType": "creative",
  "form": "text_block" | "text_graphic_block" | "text_video_block",
  "isSocial": false,
  "isSocialQuota": false,
  "contractIds": ["contract-<placement_request_id>"],
  "textData": ["<ad_text>"],
  "kktuCodes": ["30.10.1"]
}
```

Response (the important bit):

```json
{
  "token": "<erid>",
  "requestId": "<yandex_request_id>"
}
```

- `token` is the ERID that must be inserted into the ad copy as
  `"erid: <token>"`.
- `requestId` is used for polling ERIR status via
  `GET /api/v7/status?reqid=<requestId>`.
- `token !== requestId`. Creative registration is **synchronous** (the
  token is returned immediately), but the ERIR submission is asynchronous
  and only `requestId` lets us know its final state.

`kktuCodes: ["30.10.1"]` is Yandex's code for "размещение рекламы".

### 3.5 `POST /api/v7/statistics` — report a publication

Request body (`report_publication`):

```json
{
  "statistics": [
    {
      "creativeId": "creative-<placement_request_id>",
      "platformId": "platform-<channel_id>",
      "dateStartFact": "YYYY-MM-DD",
      "dateEndFact": "YYYY-MM-DD",
      "dateStartPlan": "YYYY-MM-DD",
      "dateEndPlan": "YYYY-MM-DD",
      "impsFact": 1,
      "impsPlan": 1,
      "type": "other",
      "amount": {
        "excludingVat": "0",
        "vatRate": "100",
        "vat": "0",
        "includingVat": "0"
      }
    }
  ]
}
```

`amount` is sent as a placeholder (all zeros) because the settlement
amount is tracked in the contract registration step. Yandex requires the
field to be present.

### 3.6 `GET /api/v7/status?reqid=<requestId>` — poll ERIR status

Returns JSON with a `status` string. The provider maps these to internal
states:

| Yandex `status` string        | Internal meaning |
|-------------------------------|------------------|
| `ERIR sync success`           | `erir_confirmed` |
| `ERIR async success`          | `erir_confirmed` |
| `ERIR sync error`             | `erir_failed`    |
| `ERIR async error`            | `erir_failed`    |
| `ORD rejected`                | `erir_failed`    |
| anything else                 | pending (retry)  |

Provider's `SUCCESS_STATUSES` / `ERROR_STATUSES` sets at
`yandex_ord_provider.py:28-29`.

---

## 4. `legal_status` → Yandex `orgType` mapping

From `yandex_ord_provider.py:21-26`:

| Our `legal_status`        | Yandex `orgType` |
|---------------------------|------------------|
| `legal_entity`            | `ul`             |
| `individual_entrepreneur` | `ip`             |
| `self_employed`           | `fl`             |
| `individual`              | `fl`             |

Default (unknown status) maps to `fl`. VAT rate defaults to `"22"` for
`ul`, `"100"` (without VAT) for everything else.

**Known simplification**: `self_employed` and `individual` both map to
`fl`. Yandex technically distinguishes `sp` (selfemployed) from `fl`
(physical person) in some API versions, but v7 accepts `fl` for both.
Revisit if Yandex enforces `sp`.

---

## 5. Error handling matrix

Provider raises `OrdRegistrationError` for:

- Connection timeout / transport error → retry by the Celery layer.
- HTTP 422 → validation error, do not retry without changing payload.
- HTTP 4xx (other) → client error; logs and aborts.
- HTTP 5xx → server error, retried by Celery (`ord:register_creative`
  has default retry policy in `src/tasks/ord_tasks.py`).

Creative registration must never silently succeed without a token:
`yandex_ord_provider.py:221-222` raises if `token` is missing from the
2xx response.

---

## 6. Deterministic IDs — idempotency

Every POST uses a deterministic ID derived from our domain:

| Entity       | ID format                            | Scope             |
|--------------|--------------------------------------|-------------------|
| Organization | `org-{user_id}`                      | One per advertiser |
| Platform     | `platform-{channel_id}`              | One per channel    |
| Contract     | `contract-{placement_request_id}`    | One per placement  |
| Creative     | `creative-{placement_request_id}`    | One per placement  |

This makes every call naturally idempotent — Yandex performs upsert on
the deterministic key. Double-invocations due to Celery retry are safe.

---

## 7. Local testing

The test suite at `tests/unit/test_yandex_ord_provider.py` drives the
provider through `httpx.MockTransport`, with fixtures under
`tests/fixtures/yandex_ord/`. No real network is hit. The integration
test at `tests/integration/test_ord_service_with_yandex_mock.py`
exercises the full chain `OrdService.register_creative → YandexOrdProvider
→ mock HTTP`.

When real credentials are provisioned:

1. Put them in `.env` per `.env.ord.sample`.
2. Run only the unit tests — they still pass without network.
3. Optionally add an opt-in integration test gated by the presence of
   `ORD_API_KEY` to verify the round-trip against the sandbox.

---

## 8. Follow-ups

- Replace `amount: {excludingVat:"0", ...}` in `report_publication` with
  actual settlement figures once invoicing is wired through ORD.
- Confirm `type: "other"` is accepted in production statistics — Yandex
  accepts several `type` values (`banner`, `video`, `other`); `other`
  works for Telegram text+media posts per the docs provider implemented
  against.
- Add a post-launch monitor that alerts on `erir_failed` status — Celery
  polling currently logs but does not page.
