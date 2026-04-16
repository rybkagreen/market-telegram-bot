# Changes: Payout Field Alignment (S-32 Step 5)
**Date:** 2026-04-16T16:14:38Z
**Author:** Claude Code
**Sprint/Task:** S-32-05 Frontend field alignment: amount→gross_amount, fee→fee_amount, payment_details→requisites

## Affected Files

### Backend (Python)
- `src/api/schemas/payout.py` — Updated `PayoutCreate` schema to use `gross_amount` and `requisites` field names instead of `amount` and `payment_details`
- `src/api/routers/payouts.py` — Updated create_payout endpoint to use `payout_data.gross_amount` and `payout_data.requisites` when calling PayoutService and storing requisites

### Frontend — Web Portal
- `web_portal/src/lib/types/billing.ts` — Updated `Payout` interface: renamed `amount` → `gross_amount`, `fee` → `fee_amount`, `payment_details` → `requisites`; added `owner_id`, `admin_id`, `rejection_reason`, `ndfl_withheld`, `npd_status`, `updated_at`
- `web_portal/src/api/payouts.ts` — Updated `createPayout` function signature to accept `{ gross_amount, requisites }` and imported `Payout` type from shared billing types
- `web_portal/src/screens/owner/OwnPayoutRequest.tsx` — Updated form submission to send `{ gross_amount, requisites }` instead of `{ amount, payment_details }`
- `web_portal/src/screens/owner/OwnPayouts.tsx` — Updated display to show `payout.gross_amount` instead of `payout.amount`

### Frontend — Mini App
- `mini_app/src/lib/types.ts` — Updated `Payout` interface with same field names as web portal (gross_amount, fee_amount, requisites) and additional fields
- `mini_app/src/api/payouts.ts` — Updated `createPayout` function signature to accept `{ gross_amount, requisites }`
- `mini_app/src/screens/owner/OwnPayoutRequest.tsx` — Updated form submission to send `{ gross_amount, requisites }`
- `mini_app/src/screens/owner/OwnPayouts.tsx` — Updated display to show `payout.gross_amount` instead of `payout.amount`
- `mini_app/src/hooks/queries/usePayoutQueries.ts` — Updated mutation function type to `{ gross_amount, requisites }`
- `mini_app/src/lib/validators.ts` — Updated `withdrawalSchema` to validate `gross_amount` and `requisites` instead of `amount` and `payment_details`

## Business Logic Impact

**User-facing changes:** None — field names are internal API/UI contracts. Users see same labels ("Запрошено", "Реквизиты") in UI.

**Integration impact:**
- Payout creation flow now sends `gross_amount` and `requisites` to backend instead of `amount` and `payment_details`
- Backend PayoutService receives `gross_amount` parameter (no change to service logic)
- Payout display screens now reference backend response field names correctly (`gross_amount`, `fee_amount`, `requisites`)

**Backward compatibility:** Breaking change for API consumers; existing frontend code updated in this commit.

## API / FSM / DB Contracts

### Changed: POST /api/payouts/ request schema
- **Before:** `{ amount: Decimal, payment_details: str }`
- **After:** `{ gross_amount: Decimal, requisites: str }`

### Unchanged: GET /api/payouts/ response schema
- Response schema already used correct field names: `gross_amount`, `fee_amount`, `requisites` ✓

### Database
- No schema changes — database already stores `gross_amount` and `requisites` columns ✓

## Migration Notes

None required — database schema already contains correct fields. This is purely a request/response schema alignment change.

---
🔍 Verified against: d219a22 | 📅 Updated: 2026-04-16T16:14:38Z
