# CHANGES — S-39a Backend Schema Completeness Audit

**Sprint:** S-39a (research only — no code modified)
**Date:** 2026-04-19
**Mode:** read_only

## Affected Files (read only — no edits made)

| File | Nature |
|------|--------|
| `src/api/routers/users.py` | Identified: `UserResponse` missing 9 fields |
| `src/api/routers/auth.py` | Identified: duplicate `UserResponse` schema conflicts with users.py |
| `src/api/routers/placements.py` | Identified: `PlacementResponse` missing 11 fields; `counter_schedule` type bug |
| `src/api/schemas/channel.py` | Identified: `ChannelResponse` missing `is_test` |
| `src/api/schemas/payout.py` | Identified: field name mismatch vs mini_app types |
| `mini_app/src/lib/types.ts` | Read: source of frontend field expectations |
| `web_portal/src/lib/types/user.ts` | Read: source of web_portal field expectations |
| `src/db/models/user.py` | Read: confirmed DB has credits, xp, level, referral_code fields |
| `src/db/models/placement_request.py` | Read: confirmed DB has owner_id, final_schedule, rejection_reason, etc. |
| `src/db/models/telegram_chat.py` | Read: confirmed DB has is_test |

## Business Logic Impact

None — this sprint only read code. No behavior changed.

## New / Changed API / FSM / DB Contracts

None in this sprint. Gaps identified for S-39b:
- `GET /api/users/me` under-serves 9 DB fields frontend expects
- All `GET|POST|PATCH|DELETE /api/placements/*` under-serve 11 DB fields frontend expects
- `GET|POST /api/channels/*` (4 endpoints) missing `is_test`
- `GET|POST /api/payouts/*` field names conflict with mini_app client code

Full detail: `reports/docs-architect/discovery/S39a_backend_schema_completeness_2026-04-19.md`

🔍 Verified against: 9fdf413 | 📅 Updated: 2026-04-19T00:00:00Z
