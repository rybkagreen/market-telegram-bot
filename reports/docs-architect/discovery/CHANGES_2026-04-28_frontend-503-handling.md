# CHANGES — Frontend 503 handling for PaymentProviderError

## What

Frontend completes the loop opened by Промт-12D: when backend returns
HTTP 503 on `/api/billing/topup` with structured `PaymentProviderError`
detail, both `mini_app` and `web_portal` now show a graceful modal с
human-readable Russian message + the YooKassa `provider_request_id`
(copyable for support).

Pure frontend change — no backend, no schema, no Pydantic, no public
contract delta. Backend already emits this shape since Промт-12D.

## Code changes

### mini_app
- `src/lib/types.ts` — added `PaymentProviderErrorDetail` and
  `PaymentProviderErrorResponse` types.
- `src/lib/errors.ts` (new) — `extractPaymentProviderError(err: unknown)`
  helper. Async because ky's `HTTPError.response` is a Fetch `Response`
  whose body must be cloned and `.json()`'d. Returns `null` for any
  shape that doesn't strictly match.
- `src/components/ui/PaymentErrorModal.tsx` + `.module.css` (new) —
  modal built on existing `Modal` + `Notification` + `Button`. No new
  UI dependencies.
- `src/components/ui/index.ts` — export added.
- `src/hooks/queries/useBillingQueries.ts` — `useCreateTopUp` no longer
  wires a default generic-toast `onError`; the screen now owns the
  error UX so the payment-provider modal and a generic toast can't
  fire simultaneously. Other hooks (`useBuyCredits`, `usePurchasePlan`)
  are untouched.
- `src/screens/common/TopUpConfirm.tsx` — `onError` extracts payment
  provider detail asynchronously; payment-provider error → modal,
  anything else → existing toast fallback ("Не удалось создать платёж.
  Попробуйте позже.").

### web_portal
- `src/lib/types.ts` — same two types appended.
- `src/lib/errors.ts` (new) — same helper.
- `src/shared/ui/PaymentErrorModal.tsx` (new) — same modal, Tailwind
  styles per portal conventions, uses existing `Modal` + `Notification`
  + `Button` from `shared/ui`.
- `src/shared/ui/index.ts` — export added.
- `src/screens/shared/TopUp.tsx` — `onError` mirrors the mini_app
  pattern; payment-provider error → modal; generic error rendered
  inline as `<Notification type="danger">{genericError}</Notification>`
  next to the CTA (web_portal pattern, since portal doesn't ship a
  global toast bus). Modal mounted at the root via fragment.

## Public contract delta

None. Frontend-only.

## Verification

- `mini_app/`: `npx tsc --noEmit` exit 0; `npm run build` exit 0.
- `web_portal/`: `npx tsc --noEmit` exit 0; `npm run build` exit 0.
- Python baselines (ruff / mypy / pytest) unchanged — no `src/` or
  `tests/` files touched.
- Manual UX test plan: open portal/mini-app → topup → on a real 503
  from upstream YooKassa, the modal appears with message + copyable
  request ID. Marina to validate live (Шаг 8 of source prompt).

## Origins

- Промт-12D introduced backend `PaymentProviderError → HTTP 503`
  with structured detail.
- Промт-13 ensured frontend wasn't surfacing it (silent / generic).
- Промт-14 (this) closes the user-facing loop.
- BL-033 entry — `reports/docs-architect/BACKLOG.md`.

🔍 Verified against: branch `fix/frontend-503-handling` on top of `main` (5971bcf)
📅 Updated: 2026-04-28T00:00:00Z
