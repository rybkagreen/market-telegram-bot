# CHANGES — PaymentProviderError handling + bind-mount deploy hygiene

## What

Two issues resolved in a single commit on top of `fix/billing-hotfix-bundle`
(Промт-12 hotfix bundle). See `BACKLOG.md` BL-031.

### 1. PaymentProviderError translation (BL-031)

`BillingService.create_payment` previously caught `ApiError` to log
and re-`raise`, letting the YooKassa SDK exception bubble to FastAPI
as a bare HTTP 500. Frontends saw silent failure on every YooKassa
reject — including the live shop's 403 ForbiddenError stream.

The original premise that `ForbiddenError` was an uncaught "sibling
subclass" of `ApiError` was wrong: `ForbiddenError(ApiError)` is a
subclass and was already caught. The actual bug was the bare re-raise.

This change:

- Catches the full YooKassa exception family explicitly
  (`ApiError`, `BadRequestError`, `ForbiddenError`, `NotFoundError`,
  `ResponseProcessingError`, `TooManyRequestsError`,
  `UnauthorizedError`) — defensive against future SDK refactors.
- Extracts `code` / `description` / `request_id` from `exc.content`
  (the SDK stores the response payload there; direct attribute
  access returns `None`).
- Logs structured info for support traceability.
- Raises a new `PaymentProviderError(code, description, request_id)`
  defined alongside the existing `InsufficientFundsError` in
  `billing_service.py`.
- Endpoint `POST /api/billing/topup` translates the exception to
  HTTP 503 with a Russian user-readable message plus
  `provider_error_code` + `provider_request_id` (so users can quote
  a request ID in support tickets).

### 2. Bind-mount deploy hygiene

The api container has `./src:/app/src` bind-mounted, so `docker
compose restart api` reloads working-tree code, not committed-image
code. The previous session deployed via `restart`. This is harmless
while working tree equals committed `main`, but masks future drift.
Operational note: this commit is deployed via `docker compose up -d
--build api`.

## Code changes

### `src/core/services/billing_service.py`
- `from yookassa.domain.exceptions import` extended (was: `ApiError`
  only).
- New class `PaymentProviderError` next to `InsufficientFundsError`.
- `create_payment` exception block widened to the YooKassa family;
  raises `PaymentProviderError` from the SDK exception, extracting
  fields from `exc.content`.

### `src/api/routers/billing.py`
- Imports `PaymentProviderError`.
- `create_unified_topup` (`POST /topup`) wraps the service call in
  `try/except`; translates `PaymentProviderError` to
  `HTTPException(503, detail={message, provider_error_code,
  provider_request_id})`.

### `tests/integration/test_billing_hotfix_bundle.py`
- New: `test_create_payment_translates_forbidden_to_payment_provider_error`
  — verifies `BillingService.create_payment` raises
  `PaymentProviderError` with `code` / `description` / `request_id`
  from `exc.content` when YooKassa raises `ForbiddenError`.
- New: `test_topup_endpoint_returns_503_on_payment_provider_error`
  — verifies the endpoint returns HTTP 503 with the structured
  detail dict.

## Public contract delta

`POST /api/billing/topup`:

- Before: HTTP 500 + `{"detail": "Internal Server Error"}` on any
  YooKassa-side error.
- After: HTTP 503 + `{"detail": {"message": "Платёжный сервис
  временно недоступен. Попробуйте позже или обратитесь в поддержку.",
  "provider_error_code": "<code>", "provider_request_id": "<id>"}}`.

Other endpoints: unchanged.

## Gate baseline

| Gate | Pre-fix | Post-fix |
|---|---|---|
| `make check-forbidden` | 17/17 | 17/17 ✓ |
| `ruff check src/` | 21 | 21 ✓ (unchanged) |
| `ruff check tests/integration/test_billing_hotfix_bundle.py` | 0 | 0 ✓ |
| `mypy src/` | 10 errors / 5 files | 10 / 5 ✓ |
| `tests/integration/test_billing_hotfix_bundle.py` | 4 passing | 6 passing ✓ |

Full pytest baseline check (`pytest tests/ --ignore=tests/e2e_api
--ignore=tests/unit/test_main_menu.py`) — see commit message; no
regressions vs Промт-12 baseline.

## What this does NOT fix

YooKassa shop 1297633 returns HTTP 403 on every `Payment.create()`
against live credentials. This is a YooKassa-side shop activation /
KYC / compliance issue — resolved in `lk.yookassa.ru`, not via code.

After this commit, a user attempting topup will see a graceful
503 "Платёжный сервис временно недоступен" instead of a silent 500.
Topups still won't complete on live creds until the YooKassa shop
activation issue is resolved (or sandbox creds are swapped in).

## Premise correction (vs Промт-12D)

The Промт-12D plan asserted three issues:
- (1) Git state mismatch — main / develop missing the hotfix.
- (2) ForbiddenError uncaught as a sibling of ApiError.
- (3) Bind-mount obscures running code.

(1) was already fixed by Промт-12's merge chain (verified:
`git log main..fix/billing-hotfix-bundle` empty; main HEAD =
`415ce7f` = "merge: develop → main — billing hotfix bundle"). No
realignment needed; user confirmed course-correction to skip the
no-op merges.

(2) was partially right: the symptom (silent 500 on YooKassa errors)
was real, but `ForbiddenError` extends `ApiError` and was already
caught — the actual bug was bare re-raise. The fix landed translates
the exception family to a structured 503 anyway, which is the
correct outcome.

(3) is an operational concern, kept here as a note rather than a
code change. This commit is deployed via `up -d --build`.

## Origins

- Промт-12B / 12C diagnostic chain (`PROD_STATE_OBSERVATION_*.md`).
- BL-031 entry in `reports/docs-architect/BACKLOG.md`.

🔍 Verified against: `<commit_hash_after_commit>` | 📅 Updated: 2026-04-28T00:00:00Z
