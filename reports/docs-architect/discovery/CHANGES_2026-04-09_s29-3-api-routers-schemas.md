# CHANGES — S-29.3 API Routers + Schemas (credits → balance_rub)

🔍 Verified against: `HEAD` | 📅 Updated: `2026-04-09T00:00:00Z`

## Summary

Phase 3: Converted all API routers and Pydantic schemas from `credits` (int) to `balance_rub` (Decimal). Removed credit packages and unified billing responses.

## Files Changed (9 routers + 1 schema)

| File | Change |
|------|--------|
| `src/api/routers/billing.py` | Removed `CREDIT_PACKAGES`, `BalanceResponse.credits`→`balance_rub`, `PlanResponse.credits_remaining`→`balance_rub_remaining`, `/credits` endpoint simplified, `change_plan` uses `update_balance_rub` |
| `src/api/routers/auth.py` | Removed `credits` from `AuthResponse` schema and both response constructions |
| `src/api/routers/users.py` | Removed `credits` from `UserProfile`, `ReferralStatsResponse.total_earned_credits`→`total_earned_rub` (Decimal) |
| `src/api/routers/admin.py` | Removed `credits` from 4 response constructions (user list, user detail, user update, user create) |
| `src/api/routers/analytics.py` | `SummaryResponse.credits`→`balance_rub` |
| `src/api/routers/placements.py` | Balance check: `current_user.credits`→`current_user.balance_rub`, error "Insufficient credits"→"Insufficient balance" |
| `src/api/routers/auth_login_code.py` | Response: `"credits"`→`"balance_rub"` |
| `src/api/routers/auth_login_widget.py` | Response: `"credits"`→`"balance_rub"` |
| `src/api/schemas/admin.py` | `UserAdminResponse.credits: int` removed |

## API Contract Changes (Breaking)

### `GET /api/billing/balance`
**Before:** `{"credits": 500, "plan": "starter", "packages": [...]}`
**After:** `{"balance_rub": "500.00", "plan": "starter"}` — `packages` field removed

### `POST /api/billing/credits`
**Before:** Returns `{"credits_added": 500, "amount_rub": 500}`
**After:** Returns `{"amount_rub": 500}` — no credits concept

### `POST /api/billing/plan`
**Before:** `PlanResponse.credits_remaining: int`
**After:** `PlanResponse.balance_rub_remaining: Decimal`

### `GET /api/auth/login` and `POST /api/auth/telegram`
**Before:** `AuthResponse.credits: int`
**After:** No `credits` field (already has `balance_rub: str`)

### `GET /api/users/me`
**Before:** `UserProfile.credits: int`
**After:** No `credits` field (already has `balance_rub: str`)

### `GET /api/users/me/referrals`
**Before:** `ReferralStatsResponse.total_earned_credits: int`
**After:** `ReferralStatsResponse.total_earned_rub: Decimal`

### `GET /api/admin/users`
**Before:** `UserAdminResponse.credits: int`
**After:** No `credits` field (already has `balance_rub: str`)

## Verification

- ✅ `poetry run ruff check` — 0 errors

## Next

- S-29.4: Bot Handlers
- S-29.5: Frontend (mini_app + web_portal)
- S-29.6: DB Migration + Constants + Tests
