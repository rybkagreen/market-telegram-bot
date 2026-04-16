# S-32 Step 2: Payout Service Integration in Bot Handler

## Affected Files
- `src/bot/handlers/payout/payout.py`

## Business Logic Impact

**Before:** Bot handler directly instantiated `PayoutRequest` model, manually deducted `user.earned_rub`, and added to session. Skipped:
- Cooldown checks (24-hour minimum interval)
- Velocity validation (80% withdrawal-to-topup ratio limit)
- NDFL tax calculation (13% for individuals)
- Platform account accounting (payout_reserved, profit tracking)
- Transaction logging (refund_full, payout_fee, ndfl_withholding transactions)

**After:** Bot handler delegates to `PayoutService.create_payout()`, which handles all validations and accounting:
- ✅ Cooldown validation with remaining time feedback
- ✅ Velocity check for 30-day withdrawal limits
- ✅ NDFL/NPD status calculation based on legal_status
- ✅ Platform account updates (payout_reserved += gross, profit += fee)
- ✅ Three transaction records (refund_full, payout_fee, ndfl_withholding if applicable)
- ✅ User balance deduction (earned_rub -= gross)

## New/Changed API Contracts

### FSM Handler: `payout_requisites_input()`
- **Input:** User-provided requisites (card 16 digits or phone)
- **Processing:** Calls `PayoutService.create_payout(session, user_id, gross_amount)`
- **Output:** Returns `PayoutRequest` with:
  - `net_amount = gross - fee - ndfl_withheld`
  - `ndfl_withheld` = 13% for individuals, 0% for legal entities/entrepreneurs
  - `npd_status` = "pending" for self-employed (awaits receipt)
  - Three transaction records created automatically

### Error Handling
New exception hierarchy now caught explicitly:
- **ValueError:** Minimum amount, active payout, cooldown, insufficient funds, user not found
- **VelocityCheckError:** 30-day withdrawal limit exceeded (custom exception from exceptions.py)
- **Generic Exception:** Fallback for unexpected errors

All error paths clear FSM state to prevent stuck user sessions.

## Database Impact
No schema changes. Service now populates additional fields that were previously manual/empty:
- `PayoutRequest.ndfl_withheld` (was nullable, now calculated)
- `PayoutRequest.npd_status` (was nullable, now set to "pending" or business logic)
- Transaction records created for auditing (existing schema supports it)

## Testing Considerations
- Bot handler now exercises the full PayoutService flow
- Integration tests should verify error messages match user-friendly Russian strings
- Velocity/cooldown checks no longer tested at handler level (delegated to service layer)
- Mock session/payout_service needed for handler unit tests

---

🔍 Verified against: ba95e6453d7d4991d11e5cf2dfa5abca4b880cf5 | 📅 Updated: 2026-04-16T00:00:00Z
