# Changes: S-39a Backend Schema Completeness
**Date:** 2026-04-19T09:45:36Z
**Author:** Claude Code
**Sprint/Task:** S-39a — Backend Pydantic schema completeness: consolidate, extend, fix dead code

## Affected Files

### Backend
- `src/api/schemas/user.py` — NEW canonical UserResponse (committed from S-38 untracked state). Single source of truth with full field set: id, telegram_id, username, first_name, last_name, plan, plan_expires_at, balance_rub, earned_rub, credits, advertiser_xp, advertiser_level, owner_xp, owner_level, referral_code, is_admin, ai_generations_used, legal_status_completed, legal_profile_prompted_at, legal_profile_skipped_at, platform_rules_accepted_at, privacy_policy_accepted_at, has_legal_profile
- `src/api/routers/auth.py` — Removed inline `class UserResponse`; imports canonical from `schemas.user`. Login and `/auth/me` endpoints now return all canonical fields
- `src/api/routers/users.py` — Removed inline `class UserResponse` (was missing 14 fields vs canonical); imports canonical from `schemas.user`
- `src/api/routers/placements.py` — PlacementResponse extended with 11 fields: owner_id, final_schedule, rejection_reason, scheduled_delete_at, deleted_at, clicks_count, published_reach, tracking_short_code, has_dispute, dispute_status, erid. counter_schedule type corrected to `datetime | None`
- `src/db/models/placement_request.py` — Added `has_dispute` and `dispute_status` ORM properties using `__dict__.get("disputes")` to safely check eager-loaded relationships without triggering lazy load
- `src/api/schemas/channel.py` — ChannelResponse gains `is_test: bool = False` field (Phase 3)
- `src/api/routers/channels.py` — All 4 `ChannelResponse(...)` constructions updated to pass `is_test=channel.is_test` (list, create, activate, update_category)

### Frontend (mini_app)
- `mini_app/src/lib/types.ts` — Removed `type UserRole` (dead — backend never returns `current_role`). Removed `current_role: UserRole` from `User` interface. Added `ai_generations_used: number` to `User` interface for symmetry with canonical backend schema
- `mini_app/src/screens/owner/OwnPayouts.tsx` — Updated payout field access to use `gross_amount` (renamed in S-32 backend)
- `tests/unit/test_s34_schema_regression.py` — Import path fixed for consolidated UserResponse location

## Business Logic Impact

- **UserResponse consolidation**: Two divergent inline UserResponse classes (auth.py had 13 fields, users.py had 15 fields) replaced by single canonical schema with 19 fields. Frontend now receives XP data, referral_code, credits, plan_expires_at on both `/auth/me` and `/users/me` — previously these were silently missing
- **PlacementResponse completeness**: Frontend can now display dispute badge (`has_dispute`), dispute status, ORD erid token, and tracking code without separate API calls
- **ChannelResponse.is_test**: Admin can distinguish test channels in channel lists — was silently dropped before
- **current_role removal**: Eliminates TypeScript-silent `undefined` runtime value — the field was never returned by backend, creating subtle state bugs in any code that checked it

## API / FSM / DB Contracts

| Endpoint | Changed | What's new |
|---|---|---|
| `GET /api/auth/me` | Yes | +14 fields in response |
| `POST /api/auth/telegram` | Yes | `user` object in response +14 fields |
| `GET /api/users/me` | Yes | +14 fields in response |
| `GET /api/placements/` | Yes | +11 fields per item |
| `GET /api/placements/{id}` | Yes | +11 fields, has_dispute/dispute_status populated via selectinload |
| `GET /api/channels/` | Yes | +is_test field |
| `POST /api/channels/` | Yes | +is_test field |
| `POST /api/channels/{id}/activate` | Yes | +is_test field |
| `PATCH /api/channels/{id}/category` | Yes | +is_test field |

All changes are **additive** (new fields with defaults) — no breaking changes.

## Migration Notes
none — all changes are additive schema fields, no DB schema changes

---
🔍 Verified against: 0075f28 | 📅 Updated: 2026-04-19T09:45:36Z
