# S-AUDIT-ROLES — Role Model Audit Report
**Date:** 2026-04-19 | **Branch:** feature/s-38-escrow-recovery | **Mode:** read-only

---

## Executive Summary

**Interpretation: C (hybrid-split).** There is no `current_role` field in the DB or ORM. Users can
act simultaneously as advertiser and owner — both menus are always visible. Stats are tracked
**per-role** in the DB (XP, reputation scores, violations, blocked flags are all split).  
A corrective sprint is **warranted but not urgent**: the biggest issue is a stale `current_role`
field in `mini_app/src/lib/types.ts` that the backend never populates. No drift between ORM and
migration. The S-39a XP-gap finding is **partially resolved** by the new `src/api/schemas/user.py`
created in S-38.

---

## User Model Fields Related to Role

Source: `src/db/models/user.py`

| Field | Type | Notes |
|---|---|---|
| `advertiser_xp` | `int` | XP accumulation for advertiser flow |
| `advertiser_level` | `int` | Derived level for advertiser flow |
| `owner_xp` | `int` | XP accumulation for owner flow |
| `owner_level` | `int` | Derived level for owner flow |
| `ai_uses_count` | `int` | Unified — not role-split |
| `login_streak_days` | `int` | Unified — not role-split |
| `max_streak_days` | `int` | Unified — not role-split |

**No `current_role`, no `is_advertiser`, no `is_owner`, no role enum.**  
`advertiser_id` / `owner_id` in `PlacementRequest` are deal-participant FKs — semantically correct,
not role flags. A user can be `advertiser_id` in one deal and `owner_id` in another.

---

## ReputationScore Fields — Actual State

Source: `src/db/models/reputation_score.py`

| Field | Type | Split? |
|---|---|---|
| `advertiser_score` | `float` | ✅ split |
| `owner_score` | `float` | ✅ split |
| `is_advertiser_blocked` | `bool` | ✅ split |
| `is_owner_blocked` | `bool` | ✅ split |
| `advertiser_blocked_until` | `datetime\|None` | ✅ split |
| `owner_blocked_until` | `datetime\|None` | ✅ split |
| `advertiser_violations_count` | `int` | ✅ split |
| `owner_violations_count` | `int` | ✅ split |

**Fully split.** `RoleCheckMiddleware` checks both blocked flags on every request regardless of
which flow the user invokes — correct behavior for hybrid architecture.

---

## Role Flow in Bot

Source: `src/bot/keyboards/shared/main_menu.py`, `src/bot/handlers/shared/start.py`

- **No role selection on `/start`.** Users get TOS → welcome → main menu immediately.
- **Main menu always shows both buttons**: "📣 Рекламодатель" (`main:adv_menu`) and "📺 Владелец"
  (`main:own_menu`) — no gating, no role check.
- **No `current_role` in FSM states.** None of the 12 state files reference `current_role` or
  `UserRole`.
- **No switch-role handler.** Keyword search for `change_role`, `switch_role`, `setRole` returns
  zero matches.
- **Role context lives in the handler tree, not in User state.** When a user clicks "Рекламодатель"
  they enter the advertiser FSM flow; when they click "Владелец" they enter the owner FSM flow.
  Nothing is persisted to `User.current_role` because the field doesn't exist.

**Conclusion:** There is no persistent role — it is flow-context only. The bot is fully
dual-role by design; the comment in `main_menu.py:8` ("без переключателя ролей") confirms this
was an explicit product decision.

---

## Role Flow in Frontend

### mini_app (`mini_app/src/lib/types.ts`)

```typescript
export type UserRole = 'new' | 'advertiser' | 'owner' | 'both'

export interface User {
  // ...
  current_role: UserRole   // line 63 — declared but never populated
  advertiser_xp: number
  advertiser_level: number
  owner_xp: number
  owner_level: number
}
```

- `current_role` is declared in the type but **used nowhere in any screen component or store**.
- `grep -rn '.current_role'` across `mini_app/src/screens/` and `mini_app/src/components/` returns
  **zero matches**.
- `advertiser_xp` / `owner_xp` / `advertiser_level` / `owner_level` are declared in the type and
  **backed by the API** (present in `UserResponse`), but also not rendered in any current screen.
- Auth store (`authStore.ts`) stores `User` from the API response — since the API never returns
  `current_role`, the field will always be `undefined` at runtime despite the TypeScript declaration.

### web_portal (`web_portal/src/lib/types/user.ts`)

Does **not** have `current_role` in its `User` interface — accurately reflects the actual API
contract. The web portal type is more correct than the mini_app type.

---

## XP Service Behavior

Source: `src/core/services/xp_service.py`

| Method | Writes to | Notes |
|---|---|---|
| `add_xp()` | `advertiser_xp` only | Legacy / backward compat (comment on line 251) |
| `add_advertiser_xp()` | `advertiser_xp` | Sprint 5 split method |
| `add_owner_xp()` | `owner_xp` | Sprint 5 split method |
| `award_streak_bonus()` | `advertiser_xp` only | Bug/inconsistency — streak is unified but bonus writes to advertiser only |
| `get_user_stats()` | reads both | `combined_xp = advertiser_xp + owner_xp`, `combined_level = max(...)` |

**Inconsistency**: `award_streak_bonus()` at line 538 writes to `advertiser_xp` regardless of
the user's actual activity. A user who exclusively uses the owner flow accrues streak XP into
their advertiser pool. Minor semantic issue, not a blocking bug.

---

## Past Sprint Artifacts Check

| Sprint | Artifact | Status | Notes |
|---|---|---|---|
| **S-33** | `0001_initial_schema.py` — reputation_scores | ✅ Consistent | DB snapshot has all 8 split fields matching ORM exactly |
| **S-33** | `0001_initial_schema.py` — users table | ✅ Consistent | `advertiser_xp/level`, `owner_xp/level` in both DB and ORM; no `current_role` in either |
| **S-34** | `src/api/schemas/user.py` `UserResponse` | ✅ Consistent | No `current_role` — correct. XP fields present — correct. |
| **S-37** | Notification tasks using `advertiser_id`/`owner_id` | ✅ Correct | These are deal participants, not role indicators — semantically valid |
| **S-39a** | Research: "advertiser_xp/owner_xp/owner_level/advertiser_level missing from UserResponse" | ⚠️ Stale | These 4 fields are already in `UserResponse` in the S-38 schema file. Gap is resolved. |
| **S-39a** | Research: recommended adding `current_role` to `UserResponse` | ❌ Wrong premise | `current_role` does not exist in `User` model and has no DB column. Cannot be added to UserResponse. |

**Stop-and-report condition triggered:**
`current_role` is declared in `mini_app/src/lib/types.ts` but does not exist in ORM, DB, or API.
This is dead frontend code — TypeScript will never emit a compile error because the field is typed
as non-optional (`current_role: UserRole` without `?`) but the API silently omits it, leaving the
runtime value as `undefined`. Any code that reads `user.current_role` will get `undefined`, which
TypeScript won't catch.

---

## Actionable Corrections

### P1 — Remove `current_role` from mini_app types (dead field causing silent runtime undefined)

**File:** `mini_app/src/lib/types.ts:63`  
**Change:** Remove `current_role: UserRole` from the `User` interface (line 63).  
**Why:** The field is not in the DB model, not in the API response, and not rendered anywhere.
Keeping it creates a false contract — TypeScript says it exists, runtime says it doesn't.  
**Risk:** Zero — no screen reads it. Verified with `grep`.

### P2 — Remove `UserRole` type (if no other usage)

**File:** `mini_app/src/lib/types.ts:6`  
**Change:** Remove `export type UserRole = 'new' | 'advertiser' | 'owner' | 'both'` if unused.  
**Verify first:** `grep -rn 'UserRole' mini_app/src/` — if only referenced in the type declaration
itself, safe to remove.

### P3 — Fix `award_streak_bonus()` XP target (minor semantic)

**File:** `src/core/services/xp_service.py:538`  
`user.advertiser_xp += earned_bonus["xp"]` — consider splitting 50/50 or adding a `role` param.  
**Scope:** Low priority. No user-visible impact until streak XP shows in role-specific stats.

### P4 — Update S-39a gap list

The previously identified S-39a gaps for `advertiser_xp/level/owner_xp/level` are resolved by
the new `src/api/schemas/user.py` created in S-38. The S-39a task list should be updated to
remove those 4 items and clarify that `current_role` is **not a missing field** but a **design
decision** (it doesn't exist and shouldn't be added without a product decision to persist role).

---

## Recommended Scope

**Do NOT create a separate S-33.5.** The only drift is cosmetic (frontend type declaration).
Fold P1 and P2 into **S-39a** as prep-step corrections before the schema completeness work.
P3 can be deferred to a gamification sprint.

| Correction | Target Sprint | Effort |
|---|---|---|
| Remove `current_role` from mini_app types | S-39a (prep) | 2 min |
| Remove `UserRole` type if unused | S-39a (prep) | 2 min |
| Update S-39a gap list (4 XP fields already resolved) | S-39a (planning) | planning only |
| Fix `award_streak_bonus` XP target | Gamification backlog | 30 min |

---

🔍 Verified against: 9fdf413 | 📅 Updated: 2026-04-19T00:00:00Z
