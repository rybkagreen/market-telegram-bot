# Change: Platform Credit & Gamification Bonus Endpoints

**Date:** 2026-04-10  
**Type:** feat (backend)  
**Sprint:** S-29 (Platform Balance Disbursements)

---

## Summary

Added two new admin API endpoints that allow administrators to disburse funds from the platform's `profit_accumulated` balance to user accounts. This enables manual crediting from platform commissions (15% placement fees + 1.5% payout fees) without requiring external payment processing.

---

## Files Modified

| File | Change |
|------|--------|
| `src/db/models/transaction.py` | Added `admin_credit` and `gamification_bonus` to `TransactionType` enum |
| `src/core/services/billing_service.py` | Added `admin_credit_from_platform()` and `admin_gamification_bonus()` methods |
| `src/api/routers/admin.py` | Added `POST /api/admin/credits/platform-credit` and `POST /api/admin/credits/gamification-bonus` endpoints |

---

## Business Logic Impact

### TransactionType Enum (transaction.py:40-45)
- **New values:** `admin_credit = "admin_credit"`, `gamification_bonus = "gamification_bonus"`
- **No breaking changes** — existing transaction types unchanged
- **No migration needed** — Python enum values map to existing `type` column (VARCHAR)

### BillingService Methods (billing_service.py:1426-1573)

#### `admin_credit_from_platform(session, admin_id, user_id, amount, comment)`
- **Source:** `PlatformAccount.profit_accumulated` (id=1)
- **Destination:** `User.balance_rub`
- **Pre-checks:**
  1. PlatformAccount exists (creates if missing)
  2. User exists (raises `ValueError` if not)
  3. `profit_accumulated >= amount` (raises `ValueError` if insufficient)
- **Transaction:** `type=admin_credit`, `meta_json={"type": "admin_credit", "admin_id": ..., "comment": ...}`
- **Atomicity:** Called within caller's session (no internal `async_session_factory`)

#### `admin_gamification_bonus(session, admin_id, user_id, amount, xp_amount, comment)`
- **Source:** `PlatformAccount.profit_accumulated` (id=1)
- **Destination:** `User.balance_rub` + `User.advertiser_xp`
- **Pre-checks:**
  1. PlatformAccount exists (creates if missing)
  2. User exists (raises `ValueError` if not)
  3. If `amount > 0`: `profit_accumulated >= amount`
- **Flexibility:** `amount` can be 0 (XP-only bonus), `xp_amount` can be 0 (cash-only bonus)
- **Transaction:** `type=gamification_bonus`, `meta_json={"type": "gamification_bonus", "admin_id": ..., "xp_amount": ..., "comment": ...}`

### API Endpoints (admin.py:798-910)

#### `POST /api/admin/credits/platform-credit`
- **Auth:** `AdminUser` dependency (requires `is_admin=True`)
- **Request body:**
  ```json
  {
    "user_id": 42,
    "amount": 5000.0,
    "comment": "Compensation for SLA violation"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "transaction_id": 123,
    "new_platform_balance": "45000.00",
    "new_user_balance": "15000.00"
  }
  ```
- **Error codes:** 404 (user not found), 400 (insufficient platform balance / invalid amount)

#### `POST /api/admin/credits/gamification-bonus`
- **Auth:** `AdminUser` dependency (requires `is_admin=True`)
- **Request body:**
  ```json
  {
    "user_id": 42,
    "amount": 1000.0,
    "xp_amount": 50,
    "comment": "Monthly champion reward"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "transaction_id": 124,
    "new_platform_balance": "44000.00",
    "new_user_balance": "16000.00",
    "new_user_xp": 550
  }
  ```
- **Error codes:** 404 (user not found), 400 (amount=xp_amount=0, insufficient platform balance, invalid amount)

---

## Database Contract Changes

**No migration required.** Both new transaction types are Python enum values stored in the existing `transactions.type` column (VARCHAR). The `meta_json` column (JSON) stores the additional metadata (`admin_id`, `xp_amount`, `comment`).

---

## Security Considerations

- Both endpoints require `AdminUser` dependency → only accessible to users with `is_admin=True`
- Admin ID is recorded in transaction `meta_json` for audit trail
- No PII logged — only numeric IDs and amounts
- `ValueError` from service layer is caught and returned as 400 Bad Request (no stack trace exposure)

---

## Edge Cases Handled

| Edge Case | Handling |
|-----------|----------|
| PlatformAccount (id=1) doesn't exist | Auto-created with default values |
| User doesn't exist | `ValueError` → 404 HTTP |
| `profit_accumulated < amount` | `ValueError` → 400 HTTP |
| `amount=0` AND `xp_amount=0` (gamification) | 400 HTTP: "At least one must be > 0" |
| `amount=0` but `xp_amount > 0` | Valid — XP-only bonus, no platform balance deduction |
| `amount > 0` but `xp_amount=0` | Valid — cash-only bonus |

---

🔍 Verified against: HEAD | 📅 Updated: 2026-04-10T09:24:00Z
