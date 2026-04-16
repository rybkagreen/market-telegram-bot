# S-32: Payout Flow Hardening — Complete Implementation

## Overview
Completed S-32 sprint to harden payout flow by ensuring all payout creation paths route through `PayoutService.create_payout()`, enforcing cooldown (24h), velocity (80%), and NDFL calculation guarantees. Closed all 8 identified gaps (G01–G08) and aligned frontend field names with backend schema.

## Backend Changes

### Modified Files
- **`src/api/routers/payouts.py`** — POST `/api/payouts/` now calls `PayoutService.create_payout()`. Removed inline `PayoutRequest` creation. Added error code mapping for cooldown/velocity/insufficient_balance/active_payout status codes.
- **`src/api/schemas/payout.py`** — Added `ndfl_withheld`, `npd_status`, `npd_receipt_number` (Optional[str]) to `PayoutResponse`. Added `RejectPayoutRequest` schema for admin rejection flow.
- **`src/bot/handlers/payout/payout.py`** — Bot FSM handler now calls `PayoutService.create_payout()` instead of manual `PlacementRequest` creation. Removed inline `earned_rub` modification—service handles all business logic.
- **`src/api/routers/admin.py`** — Added 3 new endpoints:
  - `GET /api/admin/payouts` — retrieve pending payouts list with pagination/filtering
  - `PATCH /api/admin/payouts/{id}/approve` — approve payout, call `complete_payout()`, dispatch owner notification via Celery
  - `PATCH /api/admin/payouts/{id}/reject` — reject with reason, call `reject_payout()`, store rejection_reason
- **`src/bot/handlers/shared/notifications.py`** — Added `notify_admin_new_payout(bot, admin_ids, payout_id, owner_telegram_id, gross_amount, net_amount, requisites)` async function. Dispatches formatted Telegram message to all admin IDs with payout summary.

### API Contracts (Added/Modified)

#### GET `/api/admin/payouts`
**Parameters:** `?limit=20&offset=0&status=pending`  
**Response:** `PayoutListAdminResponse { items: AdminPayout[], total: int }`

#### PATCH `/api/admin/payouts/{id}/approve`
**Body:** `{}`  
**Response:** `{ status: "success", payout_id: int }`  
**Side effects:** Calls `PayoutService.complete_payout()`, dispatches `notify_owner_payout_done()` notification

#### PATCH `/api/admin/payouts/{id}/reject`
**Body:** `{ reason: string }`  
**Response:** `{ status: "success", payout_id: int }`

#### POST `/api/payouts/` (Modified)
**Guarantee:** All payouts created via this endpoint route through `PayoutService.create_payout()`, enforcing:
- Cooldown (24h since last payout)
- Velocity (earned amount ≤ 80% of previous 30-day average)
- NDFL calculation (13% withheld if applicable)
- Status validation (can only create when earned_rub > 0)

## Frontend Changes

### Modified Files
- **`web_portal/src/lib/types/billing.ts`** — Updated `Payout` interface: `amount` → `gross_amount`, `fee` → `fee_amount`, `payment_details` → `requisites`. Added `owner_id`, `admin_id`, `rejection_reason`, `ndfl_withheld`, `npd_status` fields.
- **`web_portal/src/api/payouts.ts`** — `createPayout()` updated to send `gross_amount` and `requisites` fields.
- **`web_portal/src/api/admin.ts`** — Added 3 functions: `getAdminPayouts()`, `approveAdminPayout()`, `rejectAdminPayout()`.
- **`web_portal/src/hooks/useAdminQueries.ts`** — Added 3 hooks: `useAdminPayouts()`, `useApproveAdminPayout()`, `useRejectAdminPayout()` with React Query cache invalidation.
- **`web_portal/src/screens/admin/AdminPayouts.tsx`** — **CREATED** — Admin payout management screen:
  - Pending payouts list with pagination (20 per page)
  - Status filters (all, pending, processing, paid, rejected)
  - Approve button (success toast, query invalidation)
  - Reject button (inline reason input, confirmation)
  - Loading states and error handling
- **`web_portal/src/screens/owner/OwnPayouts.tsx`** — Updated field references to use `gross_amount`/`requisites`.
- **`web_portal/src/screens/owner/OwnPayoutRequest.tsx`** — Form submission updated for new field names.
- **`mini_app/src/api/payouts.ts`** — `createPayout()` updated to `gross_amount`/`requisites`.
- **Mini App payout screens** — Field references updated throughout.

### Route (Added)
- **Path:** `/admin/payouts`
- **Access:** Admin only (via AdminGuard context)
- **Status:** Lazy-loaded in `App.tsx`

## Gaps Closed

| Gap | Description | Resolution |
|-----|-------------|-----------|
| **G01** | Admin approve/reject endpoints missing | Added PATCH `/api/admin/payouts/{id}/approve` and `/reject` |
| **G02** | Admin Payouts screen missing from Web Portal | Created `/admin/payouts` route with full UI (list, approve, reject) |
| **G03** | API router bypassed service logic on POST `/api/payouts/` | Refactored to call `PayoutService.create_payout()` |
| **G04** | Bot FSM handler bypassed service logic | Refactored payout FSM to call `PayoutService.create_payout()` |
| **G05** | Frontend field names mismatched backend schema | Aligned all Payout interfaces: `amount`→`gross_amount`, `payment_details`→`requisites` |
| **G06** | NDFL/NPD fields missing from `PayoutResponse` schema | Added `ndfl_withheld`, `npd_status`, `npd_receipt_number` (Optional) |
| **G07** | Admin notification on new payout request missing | Implemented `notify_admin_new_payout()` and Celery task dispatch in POST `/api/payouts/` |
| **G08** | Owner notification on payout done missing | Covered by existing `notify_owner_payout_done()` in approval flow |

## Business Logic Guarantees

1. **Single Service Entrypoint** — All payout creation (API + Bot) routes through `PayoutService.create_payout()`, guaranteeing:
   - Cooldown (24h minimum between payouts)
   - Velocity (earned ≤ 80% of 30-day rolling average)
   - NDFL tax calculation (13% withheld if applicable)
   - Cannot be bypassed via direct DB or router shortcuts

2. **Admin Workflow** — Admins can:
   - View pending payouts in Web Portal at `/admin/payouts`
   - Approve payouts (call `complete_payout()`, dispatch owner notification)
   - Reject payouts with reason (stored in `rejection_reason` field)
   - Status validation prevents approve/reject on non-pending payouts (409 Conflict)

3. **Notification Pipeline** — Async notifications via Celery:
   - `notify_admin_new_payout_task` — dispatched when owner creates payout (prevents bot ↔ API coupling)
   - `notify_owner_payout_done()` — existing function, called during admin approval

## Testing Notes
- API endpoints require Backend `src/api/routers/admin.py` and `src/core/services/payout_service.py` deployed
- Frontend types match backend `PayoutRequest` and `PayoutResponse` domain models
- No new database migrations required — uses existing payout tables and status enums
- Admin auth enforced via `@admin_required` decorator on all admin endpoints
- Mini App validators updated to accept new field names

## Static Analysis
- **Ruff:** 0 errors (3 SIM warnings pre-existing, not blocking)
- **MyPy:** 16 errors pre-existing (per CLAUDE.md, not introduced by this work)
- **Bandit:** 0 HIGH severity
- **TypeScript (web_portal):** Clean
- **TypeScript (mini_app):** Clean

---

🔍 Verified against: b0cd7770a69582baeb76b9b0be70c2b84bdcb709 | 📅 Updated: 2026-04-16T16:17:33Z
