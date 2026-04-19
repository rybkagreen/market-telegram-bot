# Changes: Fix web portal issues - ORD message, tariff payment, disputes navigation
**Date:** 2026-04-19T00:00:00Z
**Author:** Claude Code
**Sprint/Task:** S-38 escrow recovery

## Affected Files
- `web_portal/src/screens/advertiser/OrdStatus.tsx` — Fixed ORD registration message to say "маркировка происходит до публикации" instead of "после публикации"
- `web_portal/src/api/billing.ts` — Fixed API endpoint from `billing/purchase-plan` to `billing/plan`
- `web_portal/src/components/layout/PortalShell.tsx` — Added "Споры" nav item for regular users and breadcrumb entries

## Business Logic Impact
- ORD message now correctly states that advertising is marked BEFORE publication (as required by ФЗ-38)
- Tariff payment now works because the correct API endpoint is used
- Users can now access the disputes screen from the navigation menu

## API / FSM / DB Contracts
- API endpoint changed: `POST /api/billing/purchase-plan` → `POST /api/billing/plan`

## Migration Notes
none

---
🔍 Verified against: add7b6d | 📅 Updated: 2026-04-19T00:00:00Z