# Changes: PayoutService Integration & NDFL/NPD Schema

**Date:** 2026-04-16T00:00:00Z
**Author:** Claude Code
**Sprint/Task:** S-32 Payout Flow

## Affected Files

- `src/api/routers/payouts.py` — Replaced inline PayoutRequest creation with PayoutService.create_payout() call; removed manual validation logic (MIN_PAYOUT, active check, earned_rub check, velocity check); added structured error mapping
- `src/api/schemas/payout.py` — Added three optional fields to PayoutResponse: `ndfl_withheld`, `npd_status`, `npd_receipt_number` to expose tax withholding data

## Business Logic Impact

**Before:** POST /api/payouts/ endpoint validated and created PayoutRequest inline, skipping:
- 24-hour cooldown check between payouts
- 80% velocity limit enforcement
- NDFL (13% tax for individuals) calculation
- NPD (self-employed receipt) status tracking
- Platform account profit/payout_reserved updates
- Transaction logging

**After:** All validation and processing delegated to `PayoutService.create_payout()`, which:
- Enforces MIN_PAYOUT, active request check, earned_rub availability
- Enforces 24-hour cooldown and 80% velocity limit
- Calculates NDFL withholding (13% for individuals) and NPD status based on legal_profile.legal_status
- Updates user.earned_rub and platform_account (payout_reserved, profit_accumulated)
- Creates transactions (refund_full, payout_fee, ndfl_withheld if applicable)
- Returns fully-populated PayoutRequest with all tax data

Router now sets requisites from request payload after service returns, then persists to DB.

## API Contracts

### POST /api/payouts/ Request
**No change** — accepts PayoutCreate with `amount` and `payment_details`

### POST /api/payouts/ Response (PayoutResponse)
**Added fields:**
- `ndfl_withheld: Decimal | None` — NDFL amount withheld (13% for individuals, null for others)
- `npd_status: str | None` — NPD receipt status ('pending' for self-employed, null for others)
- `npd_receipt_number: str | None` — NPD receipt ID once uploaded

**Error responses (HTTP 400/409):**
- 400 with `{"code": "payout_cooldown", "message": "..."}` — 24h cooldown not elapsed
- 400 with `{"code": "velocity_exceeded", "message": "..."}` — 80% velocity limit hit
- 400 with `{"code": "insufficient_funds", "message": "..."}` — earned_rub < requested amount
- 409 with `{"code": "active_payout_exists", "message": "..."}` — pending/processing payout exists

### PayoutRequest Model (DB)
**No schema change** — NDFL/NPD columns already exist (added in earlier migration)

## Migration Notes

None — schema columns (ndfl_withheld, npd_status, npd_receipt_number, npd_receipt_date) already exist in database from prior migration.

---
🔍 Verified against: e4d8250 | 📅 Updated: 2026-04-16T00:00:00Z
