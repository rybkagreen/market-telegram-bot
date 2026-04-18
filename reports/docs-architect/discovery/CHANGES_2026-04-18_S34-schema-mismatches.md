# Changes: S-34 Pydantic Schema ↔ SQLAlchemy Model Mismatches

**Date:** 2026-04-18T00:00:00Z  
**Author:** Claude Code  
**Sprint/Task:** S-34 — Fix Pydantic schema ↔ SQLAlchemy model mismatches (runtime crashes + architectural smells)

---

## Affected Files

### Priority 1 — Runtime crashes (STOP-1, STOP-2)

- `src/api/routers/campaigns.py` — **STOP-1**: Rewrote `CampaignResponse` and `CampaignUpdate` schemas.
  Deleted non-existent `title` field; renamed `text → ad_text`, `filters_json → meta_json`,
  `scheduled_at → proposed_schedule`; changed `created_at`/`updated_at` from `str` to `datetime`.
  Updated `DuplicateResponse`: `title → ad_text`, fixed docstring (`title, text, filters_json` → `ad_text`).
  Used Pydantic v2 `model_config` instead of legacy `class Config`.

- `src/api/routers/channels.py` — **STOP-2 (expanded)**: Added missing `owner_id` and `created_at` to
  `ChannelResponse(...)` constructors in three endpoints that were crashing 100% of the time:
  - `add_channel` (POST `/channels/`) — was missing `created_at`
  - `activate_channel` (POST `/channels/{id}/activate`) — was missing `owner_id` and `created_at`
  - `update_channel_category` (PATCH `/channels/{id}/category`) — was missing `created_at`

### Priority 2 — Architectural smells

- `src/api/routers/channel_settings.py` — Removed `model_config = {"from_attributes": True}` from
  `ChannelSettingsResponse`. Schema is always constructed manually in GET and PATCH endpoints;
  `from_attributes=True` was a trap — calling `model_validate(orm_obj)` would fail because `owner_payout`
  is a computed field absent from the ORM. Also changed `price_per_post: int → Decimal` in
  `ChannelSettingsUpdateRequest`, removing manual `Decimal(str(...))` cast in `_build_update_data`.

- `src/api/routers/users.py` — Tightened `UserResponse.first_name: str | None → str`.
  `User.first_name` is `NOT NULL` in DB; `Optional` was a misleading API contract.

### Priority 3 — Type alignment

- `src/api/routers/placements.py` — Changed `PlacementCreateRequest.proposed_price: int → Decimal`.
  Pydantic now handles JSON number → Decimal coercion directly. Removed manual `Decimal(str(...))` cast
  at placements.py:387.

### Tests

- `tests/unit/test_s34_schema_regression.py` — **New file**: 19 schema-level unit tests (no DB required).
  Covers STOP-1 (CampaignResponse field names, ghost fields, datetime types, ORM-like round-trip),
  STOP-2 (ChannelResponse required fields, constructor validation), P2.1 (from_attributes removed),
  P2.3 (first_name non-optional), P3.1 (proposed_price Decimal coercion).

---

## Business Logic Impact

| Endpoint | Before | After |
|---|---|---|
| `POST /api/campaigns` | 100% crash (ValidationError on `title`/`text`) | 201 Created |
| `GET /api/campaigns` | 100% crash (ValidationError on `model_validate`) | 200 OK |
| `GET /api/campaigns/{id}` | 100% crash | 200 OK |
| `PATCH /api/campaigns/{id}` | 100% crash + silent data loss (`filters_json` never persisted) | 200 OK, `meta_json` persists |
| `POST /api/channels/` | 100% crash (missing `created_at`) | 201 Created |
| `POST /api/channels/{id}/activate` | 100% crash (missing `owner_id`, `created_at`) | 200 OK |
| `PATCH /api/channels/{id}/category` | 100% crash (missing `created_at`) | 200 OK |

**Frontend consumers of `/api/campaigns` CRUD:** None (Step 0 confirmed). Both mini_app and web_portal
use `/placements/` for campaign flows. Free to rename fields without coordination.

**P2.2 (ActResponse.act_number) — MOOT:** No `ActResponse` Pydantic class exists. `acts.py` router
uses `_act_to_dict()` returning plain dict. Research report referenced a non-existent `schemas/act.py`.

---

## API / FSM / DB Contracts

### Changed API response fields (`/api/campaigns` CRUD endpoints)

| Field (before) | Field (after) | Type change |
|---|---|---|
| `title` | *(removed)* | — |
| `text` | `ad_text` | none (both `str`) |
| `filters_json` | `meta_json` | none (both `dict\|None`) |
| `scheduled_at` | `proposed_schedule` | `str\|None` → `datetime\|None` |
| `created_at` | `created_at` | `str` → `datetime` |
| `updated_at` | `updated_at` | `str` → `datetime` |

**Note:** No frontend consumers of these CRUD endpoints were found (Step 0). No breaking change in practice.

### Changed API request fields (`PATCH /api/campaigns/{id}`)

| Field (before) | Field (after) |
|---|---|
| `title` | *(removed)* |
| `text` | `ad_text` |
| `filters_json` | `meta_json` |
| `scheduled_at` | `proposed_schedule` |

### Changed type in `POST /api/placements/` request

- `proposed_price`: JSON `number` → `Decimal` (transparent to frontend, Pydantic coerces)

### Changed type in `PATCH /api/channel-settings/` request

- `price_per_post`: `int` → `Decimal` (transparent to frontend, Pydantic coerces)

---

## Migration Notes

None. All changes are Pydantic schema / router layer only. No model changes, no DB migrations.
`alembic check` still reports zero drift (S-33 baseline preserved).

---

🔍 Verified against: `2d40d0b` | 📅 Updated: 2026-04-18T00:00:00Z
