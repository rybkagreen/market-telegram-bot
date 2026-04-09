# CHANGES — 2026-04-08 — portal: owner statuses, tax dedup, payment toast

## Affected files

| File | Change |
|---|---|
| `web_portal/src/screens/owner/OwnRequests.tsx` | Bug fix: added `pending_payment` / `escrow` to owner placement filters |
| `web_portal/src/components/admin/TaxSummaryBase.tsx` | New: shared base component for tax/accounting screens |
| `web_portal/src/screens/admin/AdminAccounting.tsx` | Refactor: now delegates to TaxSummaryBase |
| `web_portal/src/screens/admin/AdminTaxSummary.tsx` | Refactor: now delegates to TaxSummaryBase, adds KUДиР table |
| `web_portal/src/shared/ui/Toast.tsx` | New: self-contained toast component (fixed bottom-right, auto-dismiss) |
| `web_portal/src/hooks/useToast.ts` | New: `useToast()` hook returning `{ showToast, ToastComponent }` |
| `web_portal/src/screens/advertiser/CampaignPayment.tsx` | UX: success toast + 1500ms delay before redirect; error toast replaces inline error |
| `web_portal/src/shared/ui/index.ts` | Export added: `Toast` |
| `web_portal/src/styles/globals.css` | Added `@keyframes fadeInUp` for Toast animation |

## Business logic impact

### Fix 1 — Owner missing placements (HIGH)
- **Before:** `pending_payment` and `escrow` statuses were absent from all owner filter arrays → after advertiser pays, placement disappeared from owner's UI entirely.
- **After:** `pending_payment` → tab "Новые" (owner sees payment is pending); `escrow` → tab "Активные" (owner sees funds locked). Action buttons (Accept/Reject/Counter) now shown only for `pending_owner` / `counter_offer` — not for `pending_payment`.
- **New status labels:** `💳 Ожидает оплаты`, `🔒 В эскроу`.

### Fix 2 — Tax/Accounting code deduplication (LOW)
- `AdminAccounting` and `AdminTaxSummary` shared ~80% of code (API call, period selector, KPI grid, download buttons).
- Extracted into `TaxSummaryBase` with `coloredKpis`, `showEmptyHint`, `downloadMode`, and `children` render-prop.
- Routes `/admin/accounting` and `/admin/tax-summary` unchanged.

### Fix 3 — Payment toast UX (MEDIUM)
- **Before:** Successful payment navigated silently to `/waiting`; errors shown as inline static Notification.
- **After:** On success — toast "Оплата прошла успешно…" shown for 3s, redirect happens after 1500ms. On error — toast (not inline notification) shown. No external libraries added.

## New/changed contracts

- No API contract changes.
- No FSM changes.
- No DB migrations.

## Toast contract (internal)
```ts
// useToast
const { showToast, ToastComponent } = useToast()
showToast(message: string, type: 'success' | 'error', duration?: number /* ms, default 3000 */)
// render: {ToastComponent} anywhere in JSX
```

🔍 Verified against: cf0e7de7b6e13fdccd812337f9e78dae5cff1650 | 📅 Updated: 2026-04-08T00:00:00Z
