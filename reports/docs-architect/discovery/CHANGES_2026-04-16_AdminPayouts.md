# AdminPayouts Screen Implementation — S32-04

## Overview
Implemented Web Portal admin payouts management screen enabling admins to view, approve, and reject payout requests.

## Affected Files

### Frontend (web_portal)
- `src/screens/admin/AdminPayouts.tsx` (NEW) — Admin payouts list screen with approve/reject actions
- `src/api/admin.ts` — Added 3 API functions for payout operations
- `src/hooks/useAdminQueries.ts` — Added 3 React Query hooks with invalidation
- `src/lib/types/billing.ts` — Added AdminPayout and PayoutListAdminResponse types
- `src/lib/types/index.ts` — Exported new billing types
- `src/App.tsx` — Registered `/admin/payouts` route

## API Contracts (Added)

### GET `/api/admin/payouts`
**Parameters:** `?limit=20&offset=0&status=pending`
**Response:** `PayoutListAdminResponse`
```typescript
interface PayoutListAdminResponse {
  items: AdminPayout[]
  total: number
}

interface AdminPayout {
  id: number
  owner_id: number
  gross_amount: string
  fee_amount: string
  net_amount: string
  status: PayoutStatus  // 'pending' | 'processing' | 'paid' | 'rejected'
  requisites: string
  created_at: string
  processed_at: string | null
  rejection_reason: string | null
  ndfl_withheld: string | null
  npd_status: string | null
}
```

### PATCH `/api/admin/payouts/{id}/approve`
**Body:** `{}`
**Response:** `{ status: string; payout_id: number }`

### PATCH `/api/admin/payouts/{id}/reject`
**Body:** `{ reason: string }`
**Response:** `{ status: string; payout_id: number }`

## Frontend Features

### AdminPayouts Screen
- **Status filters:** All, Pending, Processing, Paid, Rejected
- **List display:** Payout ID, owner ID, gross/fee/net amounts, requisites (truncated), created date
- **Actions (pending payouts only):**
  - Approve button — triggers mutation, invalidates cache, shows success toast
  - Reject button — opens inline reason input, requires confirmation
- **Pagination:** 20 payouts per page
- **Loading/Error states:** Skeleton loader, error notification

### Hooks & Types
- `useAdminPayouts()` — Query with status filtering and pagination
- `useApproveAdminPayout()` — Mutation with success invalidation
- `useRejectAdminPayout()` — Mutation accepting `{payoutId, reason}`

## UI Components Used
- Existing: Card, Button, Skeleton, Notification, StatusBadge, formatDateMSK
- New local state: reject reason input, success message

## Route
- **Path:** `/admin/payouts`
- **Access:** Admin only (via AdminGuard context)
- **Lazy-loaded:** Yes

## Breaking Changes
None — additive feature.

## Testing Notes
- API endpoints presume backend (src/api/routers/admin.py) provides payouts endpoints
- Frontend types match backend PayoutRequest domain model
- No database migrations — uses existing payout tables

---

🔍 Verified against: aea53dc36c298d1a251f7aca66827e6a409d7e5a | 📅 Updated: 2026-04-16T00:00:00Z
