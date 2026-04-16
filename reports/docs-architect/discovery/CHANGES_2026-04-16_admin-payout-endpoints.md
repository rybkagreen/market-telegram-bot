# S-32 Step 3: Admin Payout Endpoints & Notifications

## Summary
Implemented admin panel endpoints for managing pending payouts and automated admin notifications when new payouts are created.

## Affected Files

### Backend (API & Services)
- `src/api/routers/admin.py` — 3 new admin endpoints
- `src/api/schemas/payout.py` — `RejectPayoutRequest` schema
- `src/api/routers/payouts.py` — notification dispatch on payout creation
- `src/bot/handlers/shared/notifications.py` — `notify_admin_new_payout()` function
- `src/tasks/notification_tasks.py` — `notify_admin_new_payout_task` Celery task

## Public API Contracts

### New Admin Endpoints

**GET `/api/admin/payouts`**
- Auth: Admin required (`AdminUser` dependency)
- Returns: `list[PayoutResponse]`
- Behavior: Lists all pending payout requests, ordered by creation (oldest first)
- No status codes beyond 200/401/403

**PATCH `/api/admin/payouts/{payout_id}/approve`**
- Auth: Admin required
- Path params: `payout_id: int`
- Body: None
- Returns: `{ status: "approved", payout_id: int, payout: PayoutResponse }`
- Status codes:
  - 200: Success
  - 404: Payout not found
  - 409: Payout status != pending (`{ code: "wrong_status", message: "..." }`)
- Side effects:
  - Calls `PayoutService.complete_payout()` (updates status to `paid`)
  - Dispatches `notify_payout_paid` Celery task for owner notification

**PATCH `/api/admin/payouts/{payout_id}/reject`**
- Auth: Admin required
- Path params: `payout_id: int`
- Body: `RejectPayoutRequest { reason: str (1-512 chars) }`
- Returns: `{ status: "rejected", payout_id: int, payout: PayoutResponse }`
- Status codes:
  - 200: Success
  - 404: Payout not found
  - 409: Payout status != pending
  - 400: Invalid request body
- Side effects:
  - Calls `PayoutService.reject_payout(session, payout_id, reason)`
  - Updates payout status to `rejected` with reason stored in `rejection_reason` field

### New Notification Function

**`notify_admin_new_payout(bot, admin_telegram_ids, payout_id, owner_telegram_id, gross_amount, net_amount, requisites)`**
- Location: `src/bot/handlers/shared/notifications.py`
- Signature: `async def → None`
- Behavior: Sends formatted Telegram message to each admin ID
  - Message format: `"💰 *Новая заявка на выплату #{payout_id}*\n\nВладелец: {owner_telegram_id}\n..."`
  - Wraps each send in try/except to prevent failure if admin is blocked
- Called by: `notify_admin_new_payout_task` Celery task

### New Celery Task

**`payouts:notify_admin_new_payout_task(payout_id, owner_id, gross_amount, net_amount, requisites)`**
- Queue: `background`
- Behavior:
  - Fetches `admin_ids` from `settings.admin_ids` property
  - Creates `Bot` instance with `settings.bot_token`
  - Calls `notify_admin_new_payout()` with bot + admin IDs
  - Returns `bool` (success/failure)

### Integration Points

**POST `/api/payouts/` (existing endpoint)**
- After successful payout creation, now dispatches `notify_admin_new_payout_task.delay(...)` with:
  - `payout.id`
  - `current_user.id` (owner)
  - `payout.gross_amount` (as float)
  - `payout.net_amount` (as float)
  - `payout.requisites`

## New Schemas

### `RejectPayoutRequest`
```python
class RejectPayoutRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=512, description="Причина отклонения")
```

## Database

No model changes. Operations use existing `PayoutRequest`, `PayoutStatus` enums, and updated `PayoutService` methods (from S-32 Step 1).

## Key Validations

1. **Admin auth**: All endpoints require `get_current_admin_user()` dependency
2. **Status guards**: approve/reject both check `payout.status == PayoutStatus.pending`, return 409 if not
3. **Not-found handling**: 404 if payout ID doesn't exist
4. **Notification robustness**: Admin notif wrapped in try/except so blocking one admin doesn't fail task

## Testing Notes

- Unit tests should verify endpoint status codes (404, 409, 200)
- Integration tests should verify `PayoutService` method calls
- Task tests should verify Celery dispatch happens on payout creation
- No new migrations required (schema unchanged)

---

🔍 Verified against: `0b7ef70` | 📅 Updated: `2026-04-16T00:00:00Z`
