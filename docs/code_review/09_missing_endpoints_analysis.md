# Missing Frontend Endpoints Analysis

**Generated:** 2026-03-20  
**Scope:** Backend endpoints not called from Mini App frontend

---

## Summary

| Category | Count | Action Required |
|----------|-------|-----------------|
| Total missing endpoints | 33 | - |
| Admin-only (intentional) | 8 | ❌ No frontend needed |
| Webhooks/Internal | 2 | ❌ No frontend needed |
| Duplicates/Alternatives | 8 | ❌ Use existing endpoints |
| Should implement | 15 | ⚠️ Consider adding |

---

## 1. Admin-Only Endpoints (8) - No Frontend Needed

These endpoints are designed for admin panel only:

| Endpoint | Method | Purpose | Why Missing |
|----------|--------|---------|-------------|
| `/api/admin/stats` | GET | Platform statistics | Admin dashboard only |
| `/api/admin/users` | GET | List all users | Admin user management |
| `/api/admin/users/{user_id}` | GET | User details | Admin user management |
| `/api/disputes/admin/disputes` | GET | All disputes | Admin dispute management |
| `/api/disputes/admin/disputes/{id}/resolve` | POST | Resolve dispute | Admin only action |
| `/api/feedback/admin/` | GET | All feedback | Admin feedback management |
| `/api/feedback/admin/{id}` | GET | Feedback details | Admin feedback management |
| `/api/feedback/admin/{id}/respond` | POST | Respond to feedback | Admin only action |
| `/api/feedback/admin/{id}/status` | PATCH | Update feedback status | Admin only action |

**Recommendation:** ✅ Keep as admin-only. No frontend implementation needed.

---

## 2. Webhooks & Internal Endpoints (2) - No Frontend Needed

| Endpoint | Method | Purpose | Why Missing |
|----------|--------|---------|-------------|
| `/api/billing/webhooks/yookassa` | POST | YooKassa webhook | Server-to-server only |
| `/api/auth/telegram` | POST | Telegram auth | Called internally by client.ts |

**Recommendation:** ✅ Keep as internal. No frontend implementation needed.

---

## 3. Duplicates & Alternative Endpoints (8) - Use Existing

These endpoints have alternatives already implemented:

| Missing Endpoint | Alternative | Status |
|------------------|-------------|--------|
| `/api/campaigns/list` | `/api/campaigns` | ✅ Same functionality with pagination |
| `/api/billing/plans` | `/api/billing/plans` | ✅ Already implemented |
| `/api/auth/login` | `/api/auth/telegram` | ✅ Telegram auth preferred |
| `/api/auth/me` | `/api/users/me` | ✅ Same endpoint |
| `/api/billing/topup/crypto` | `/api/billing/topup` | ✅ Unified topup endpoint |
| `/api/billing/topup/stars` | `/api/billing/topup` | ✅ Unified topup endpoint |
| `/api/billing/topup/{payment_id}/status` | Polling via `/api/billing/history` | ✅ Alternative approach |
| `/api/payouts/{payout_id}` | `/api/payouts/` (list) | ✅ List includes all payouts |

**Recommendation:** ✅ Use existing alternatives. No new implementation needed.

---

## 4. Should Implement (15) - Consider Adding

These endpoints provide unique functionality:

### 4.1 Analytics (6 endpoints)

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| `/api/analytics/activity` | GET | User activity stats | MEDIUM |
| `/api/analytics/campaigns/{id}/ai-insights` | GET | AI campaign insights | LOW |
| `/api/analytics/stats/public` | GET | Public platform stats | LOW |
| `/api/analytics/summary` | GET | Analytics summary | MEDIUM |
| `/api/analytics/top-chats` | GET | Top channels rating | MEDIUM |
| `/api/analytics/topics` | GET | Channel topics list | LOW |

**Recommendation:** 
- Implement `/api/analytics/activity` and `/api/analytics/summary` for user dashboard
- `/api/analytics/top-chats` useful for channel discovery
- AI insights can be added later

### 4.2 Channel Features (5 endpoints)

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| `/api/channels/compare` | POST | Compare multiple channels | HIGH |
| `/api/channels/compare/preview` | GET | Compare preview | MEDIUM |
| `/api/channels/preview` | GET | Channel preview | MEDIUM |
| `/api/channels/stats` | GET | Platform channel stats | LOW |
| `/api/channels/subcategories/{parent_topic}` | GET | Subcategory stats | LOW |

**Recommendation:**
- `/api/channels/compare` - valuable for advertisers choosing channels
- `/api/channels/preview` - useful before adding channel

### 4.3 Billing (3 endpoints)

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| `/api/billing/balance` | GET | User balance | HIGH |
| `/api/billing/history` | GET | Transaction history | HIGH |
| `/api/billing/invoice/{invoice_id}` | GET | Invoice details | MEDIUM |

**Recommendation:**
- `/api/billing/balance` - should be in cabinet screen
- `/api/billing/history` - important for transparency

### 4.4 Campaign Management (1 endpoint)

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| `/api/campaigns/{id}/start` | POST | Start campaign | HIGH |

**Recommendation:** 
- Currently campaigns start automatically after payment
- Manual start may be useful for scheduled campaigns

---

## 5. Placement Endpoints Analysis

Backend has additional placement endpoints not in frontend:

| Endpoint | Method | Purpose | Frontend Alternative |
|----------|--------|---------|---------------------|
| `/api/placements/{id}/accept` | POST | Owner accepts | ✅ Via PATCH with action |
| `/api/placements/{id}/accept-counter` | POST | Accept counter | ✅ Via PATCH with action |
| `/api/placements/{id}/counter` | POST | Counter offer | ✅ Via PATCH with action |
| `/api/placements/{id}/pay` | POST | Make payment | ✅ Via PATCH with action |
| `/api/placements/{id}/reject` | POST | Reject placement | ✅ Via PATCH with action |
| `/api/placements/{id}/delete` | DELETE | Delete placement | ✅ Via PATCH cancel |

**Status:** ✅ All functionality available via unified PATCH endpoint

---

## 6. Reputation Endpoints

| Endpoint | Method | Purpose | Frontend Alternative |
|----------|--------|---------|---------------------|
| `/api/reputation/me` | GET | My reputation | ✅ Via `/api/users/me/stats` |
| `/api/reputation/me/history` | GET | My reputation history | ⚠️ Not implemented |
| `/api/reputation/{user_id}` | GET | User reputation | Admin only |
| `/api/reputation/{user_id}/history` | GET | User reputation history | Admin only |

**Recommendation:**
- Add `/api/reputation/me/history` for user to see reputation changes

---

## Implementation Priority

### High Priority (Implement Soon)

1. `/api/billing/balance` - Display in cabinet
2. `/api/billing/history` - Transaction history screen
3. `/api/channels/compare` - Channel comparison tool
4. `/api/campaigns/{id}/start` - Manual campaign start

### Medium Priority (Consider)

5. `/api/analytics/activity` - User activity dashboard
6. `/api/analytics/summary` - Analytics summary
7. `/api/analytics/top-chats` - Top channels rating
8. `/api/channels/preview` - Channel preview
9. `/api/billing/invoice/{invoice_id}` - Invoice details

### Low Priority (Optional)

10. `/api/analytics/campaigns/{id}/ai-insights` - AI insights
11. `/api/analytics/stats/public` - Public stats
12. `/api/analytics/topics` - Topics list
13. `/api/channels/stats` - Platform stats
14. `/api/channels/subcategories/{parent_topic}` - Subcategory stats
15. `/api/reputation/me/history` - Reputation history

---

## Conclusion

**Out of 33 "missing" endpoints:**

- **10 endpoints** - Admin-only or internal (no frontend needed) ✅
- **8 endpoints** - Duplicates with alternatives (use existing) ✅
- **15 endpoints** - Should consider implementing (prioritized above) ⚠️

**Immediate Action Items:**

1. Add `/api/billing/balance` to cabinet screen
2. Add `/api/billing/history` transaction list
3. Add `/api/channels/compare` feature
4. Consider manual campaign start endpoint

**No critical gaps found.** All core functionality is implemented.
