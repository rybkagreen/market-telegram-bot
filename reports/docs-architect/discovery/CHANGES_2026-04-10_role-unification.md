# CHANGES_2026-04-10_role-unification

**Date:** 2026-04-10T16:00:00Z
**Sprint:** S-32 — Role Unification
**Author:** Qwen Code

## Summary

Removed `User.current_role` navigation gating. Users no longer switch between "advertiser" and "owner" roles — both capabilities are always available. Context is determined by route (`/adv/*` vs `/own/*`), not by a stored field.

## Breaking Changes

| Component | Before | After |
|-----------|--------|-------|
| `User.current_role` (DB column) | `String(16)`, default `"new"` | **Removed** |
| `GET /api/auth/me` | Returns `role` field | **No `role` field** |
| `GET /api/placements/` | `role` query param (advertiser/owner) | **Union of both**, no param |
| `GET /api/admin/users` | `role` query param + `role` in response | **Removed** |
| `PATCH /api/admin/users/{id}` | `role` in request body | **Removed** |
| Bot main menu | "Выбрать роль" button | **Direct buttons**: 📣 Рекламодатель / 📺 Владелец |
| Mini App `/role` | RoleSelect screen | **Deleted** |
| `UserResponse.role` (frontend) | `string` field | **Removed** |

## Files Changed

### Backend (7 files)
| File | Change |
|------|--------|
| `src/db/models/user.py` | Removed `current_role` column |
| `src/db/migrations/versions/0001_initial_schema.py` | Removed `current_role` column definition |
| `src/bot/middlewares/role_check.py` | Removed role gating — always checks BOTH advertiser and owner blocks |
| `src/bot/handlers/shared/start.py` | Deleted `cb_change_role`, `cb_role_advertiser`, `cb_role_owner` handlers |
| `src/bot/handlers/shared/cabinet.py` | Removed `user.current_role` check for tax block |
| `src/bot/keyboards/shared/main_menu.py` | Replaced "Выбрать роль" with direct 📣/📺 buttons; removed `role_select_kb()` |
| `src/bot/keyboards/shared/cabinet.py` | Removed `role` param from `cabinet_kb()` — always shows topup + payout |

### API (4 files)
| File | Change |
|------|--------|
| `src/api/routers/auth.py` | Removed `role` from `UserResponse` schema and both handlers |
| `src/api/routers/placements.py` | Removed `role` param; returns UNION of advertiser + owner placements |
| `src/api/routers/admin.py` | Removed `role` from all `UserAdminResponse` constructions and update handler |
| `src/api/schemas/admin.py` | Removed `role` from `UserAdminResponse` and `AdminUserUpdateRequest` |

### Mini App (4 files)
| File | Change |
|------|--------|
| `mini_app/src/App.tsx` | Removed `RoleSelect` import and `/role` route |
| `mini_app/src/screens/common/MainMenu.tsx` | Replaced "Выбрать роль" with direct 📣 Рекламодатель → `/adv` and 📺 Владелец → `/own` |
| `mini_app/src/screens/common/RoleSelect.tsx` | **Deleted** |
| `mini_app/src/screens/common/RoleSelect.module.css` | **Deleted** |

### Web Portal (6 files)
| File | Change |
|------|--------|
| `web_portal/src/screens/advertiser/MyCampaigns.tsx` | Removed `useAuthStore` import and role logic; `useMyPlacements()` with no params |
| `web_portal/src/api/campaigns.ts` | Removed `role` param from `getMyPlacements()` |
| `web_portal/src/hooks/useCampaignQueries.ts` | Removed `role` from `useMyPlacements()` signature and queryKey |
| `web_portal/src/stores/authStore.ts` | Removed `role: string` from `User` interface |
| `web_portal/src/api/admin.ts` | Removed `role` from `getUsersList()` and `updateAdminUser()` |
| `web_portal/src/screens/admin/AdminUsersList.tsx` | Replaced role column with plan column |
| `web_portal/src/screens/admin/AdminUserDetail.tsx` | Replaced role badge with plan badge |

### Cleanup (1 file)
| File | Change |
|------|--------|
| `src/core/services/user_role_service.py` | Rewritten as minimal stub — removed all `current_role` references |

## What Was NOT Changed (preserved business logic)

| Component | Reason |
|-----------|--------|
| `ReputationService` (`role` param) | Role = context of action (advertiser vs owner), not user navigation |
| `ReputationHistory.role` | Tracks which context reputation was earned in |
| `Contract.role` | Legal context of contract signing |
| `ContractSignature.role` | Who signed in what capacity |
| `Badge.role` | Badges earned in advertiser vs owner context |
| `PlacementRequestRepository.get_by_advertiser()` / `get_by_owner()` | Both methods remain; API now calls both and unions results |

## QA Results

| Check | Result |
|-------|--------|
| `ruff check src/` | 0 errors |
| `mypy src/` | Success: no issues in 264 source files |
| `web_portal tsc --noEmit` | 0 errors |
| `web_portal vite build` | ✓ built in 727ms |
| `mini_app vite build` | ✓ built in 978ms |
| `grep current_role src/` | 0 matches |

## Migration Notes

The `current_role` column is removed from the `users` table via updated `0001_initial_schema.py`.
Since we're pre-production (no real users), the migration file is updated in-place per QWEN.md migration strategy.
To apply: reset DB and run `alembic upgrade head`.

## E2E Flow After Changes

```
BOT:
  /start → TOS → main_menu [👤 Кабинет | 📣 Рекламодатель | 📺 Владелец | 💬 Помощь | ✉️ Обратная связь]
  "Рекламодатель" → adv_menu (no current_role assignment)
  "Владелец" → own_menu (no current_role assignment)
  "Кабинет" → always shows balance + earned_rub + topup + payout

API:
  GET /api/auth/me → { id, telegram_id, ..., plan, balance_rub, earned_rub }  (no role)
  GET /api/placements/ → UNION(advertiser_placements, owner_placements)
  PATCH /api/admin/users/{id} → { plan?, is_admin? }  (no role)

MINI APP:
  / → MainMenu: [🛡️ Админ, 👤 Кабинет, 📣 Рекламодатель, 📺 Владелец, 💬 Помощь, ✉️ Обратная связь]
  /role → DELETED
  📣 Рекламодатель → /adv
  📺 Владелец → /own

WEB PORTAL:
  /adv/campaigns → GET /api/placements/ (no role param) → shows all campaigns
  /admin/users → table shows "Тариф" instead of "Роль"
```

🔍 Verified against: working tree | 📅 Updated: 2026-04-10T16:30:00Z
