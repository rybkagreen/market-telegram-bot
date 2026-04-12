# CHANGES — 2026-04-12 — Mobile Card Layout & Channel Management Fixes

**Session date:** 2026-04-12
**Verified against:** `feature/S-27-web-portal` branch
**Status:** Production ready

---

## Summary

| # | Change | Type | Files |
|---|--------|------|-------|
| 1 | Seed categories table (was empty) | Fix | `src/db/seeds/categories_seed.py`, `0001_initial_schema.py` |
| 2 | Fix web_portal category grid chicken-and-egg bug | Fix | `web_portal/src/screens/owner/OwnAddChannel.tsx` |
| 3 | Auto-navigate to "My Channels" after add | UX | `mini_app/src/screens/owner/OwnAddChannel.tsx`, `web_portal/src/screens/owner/OwnAddChannel.tsx` |
| 4 | Fix channel delete (204 response) | Fix | `mini_app/src/api/channels.ts`, `web_portal/src/api/channels.ts` |
| 5 | Channel soft-delete instead of hard-delete | Fix | `src/api/routers/channels.py` |
| 6 | Mobile icon-only buttons | UX | `web_portal/src/shared/ui/Button.tsx`, `OwnChannels.tsx`, `MyCampaigns.tsx`, `OwnRequests.tsx` |

---

## 1. Categories Seed

**Problem:** `categories` table was empty — no category buttons when adding a channel.
**Fix:** Seeded 11 categories from `src/db/seeds/categories_seed.py` into DB. Added `op.bulk_insert()` to migration `0001_initial_schema.py` so categories are auto-created on fresh deploys.
**Verified:** 11 rows in `categories` table, all `is_active=true`.

## 2. Category Grid Chicken-and-Egg Bug (web_portal)

**Problem:** `canAdd = valid && !duplicate && !!selectedCategory` but `CategoryGrid` only rendered when `canAdd` was true. User couldn't select a category because the grid was hidden.
**Fix:** Split into `showCategoryGrid` (visibility) and `canAdd` (submit guard).
**File:** `web_portal/src/screens/owner/OwnAddChannel.tsx`

## 3. Auto-Navigate After Channel Add

**Problem:** After clicking "Add Channel", user stayed on the same screen.
**Fix:** Added `useEffect` watching `addMutation.isSuccess` → `navigate('/own/channels', { replace: true })`.
**Files:** `mini_app/src/screens/owner/OwnAddChannel.tsx`, `web_portal/src/screens/owner/OwnAddChannel.tsx`

## 4. Delete Channel — 204 Response Handling

**Problem:** Backend returns `204 No Content` but frontend called `.json<void>()` which throws on empty body.
**Fix:** Changed to `.text()` in both API clients.
**Files:** `mini_app/src/api/channels.ts`, `web_portal/src/api/channels.ts`

## 5. Soft-Delete Instead of Hard-Delete

**Problem:** API used `session.delete()` (hard delete), losing channel history. Bot already uses `is_active = False` (soft-delete) — inconsistency.
**Fix:** Changed to `channel.is_active = False` with check for active placements.
**File:** `src/api/routers/channels.py`

## 6. Mobile Icon-Only Buttons

**Problem:** Text buttons overflow on 375px screens. 3 buttons (e.g. "Сравнить / Настройки / Удалить") exceed available width.
**Fix:**
- `Button.tsx`: Added `icon` prop → square buttons `44×44px` (sm), `48×48px` (md), `52×52px` (lg). Fixed `min-h-[36px]` → `min-h-[44px]`. Added `relative` for spinner centering. Added `title` prop for tooltips.
- `OwnChannels.tsx`: 3 icon buttons (⚖️ ⚙️ 🗑️)
- `MyCampaigns.tsx`: 2 icon buttons (📊 ❌)
- `OwnRequests.tsx`: 3 icon buttons (✅ ✏️ ❌)

---

## Files Modified

| File | Change |
|------|--------|
| `src/db/migrations/versions/0001_initial_schema.py` | Added `op.bulk_insert()` for 11 categories |
| `src/api/routers/channels.py` | Soft-delete, active placements check |
| `mini_app/src/api/channels.ts` | `deleteChannel()` uses `.text()` |
| `mini_app/src/screens/owner/OwnAddChannel.tsx` | `useEffect` for auto-navigate |
| `web_portal/src/api/channels.ts` | `deleteChannel()` uses `.text()` |
| `web_portal/src/screens/owner/OwnAddChannel.tsx` | Split `showCategoryGrid`/`canAdd`, auto-navigate |
| `web_portal/src/shared/ui/Button.tsx` | `icon` prop, `min-h-[44px]`, `relative`, `title` |
| `web_portal/src/screens/owner/OwnChannels.tsx` | Icon-only mobile buttons |
| `web_portal/src/screens/advertiser/MyCampaigns.tsx` | Icon-only mobile buttons |
| `web_portal/src/screens/owner/OwnRequests.tsx` | Icon-only mobile buttons |

---

🔍 Verified against: `feature/S-27-web-portal` | 📅 Updated: 2026-04-12T15:30:00Z
