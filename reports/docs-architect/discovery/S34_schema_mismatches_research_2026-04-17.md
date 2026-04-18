# S-34 Pydantic Schema vs SQLAlchemy Model Audit

**Date:** 2026-04-17  
**Branch:** feature/s-31-legal-compliance-timeline  
**Scope:** Read-only audit; no files modified.

---

## ⚠️ STOP Conditions

### STOP-1 — CampaignResponse crashes at runtime on every request (CRITICAL)

`CampaignResponse` (campaigns.py:63) has two required fields — `title: str` and `text: str` — that do
not exist on `PlacementRequest` (the underlying model, aliased as `Campaign` at campaigns.py:14).
`from_attributes = True` on the schema means Pydantic tries to read `placement_request.title` and
`placement_request.text`; both raise `AttributeError` → `ValidationError` → HTTP 500.

**Affected endpoints (all crash 100% of the time):**

| Method | Path | Crash site |
|---|---|---|
| POST | `/api/campaigns` | campaigns.py:119 `return placement_request` |
| GET | `/api/campaigns` | campaigns.py:156 `CampaignResponse.model_validate(c)` |
| GET | `/api/campaigns/{id}` | campaigns.py:200 `return placement_request` |
| PATCH | `/api/campaigns/{id}` | campaigns.py:255 `return updated` |

**Not affected** (uses `CampaignItem` with manual construction):
- `GET /api/campaigns/list` (Mini App) — campaigns.py:429, title built as
  `camp.ad_text[:50] if camp.ad_text else "Без названия"`.

### STOP-2 — ChannelResponse missing required fields in activate_channel

`ChannelResponse.owner_id: int = Field(...)` and `ChannelResponse.created_at: str = Field(...)` are
both required (no default). The `activate_channel` endpoint at channels.py:558 constructs
`ChannelResponse(...)` without passing either field → `ValidationError` → HTTP 500 on every call
to `POST /api/channels/{id}/activate`.

**Evidence (channels.py:558–569):**
```python
return ChannelResponse(
    id=channel.id,
    telegram_id=channel.telegram_id,
    title=channel.title,
    username=channel.username,
    member_count=channel.member_count,
    ...  # owner_id and created_at ABSENT
)
```

---

## Таблица расхождений

| # | schema_field | model_field | schema_type | model_type | cause_hypothesis | evidence (file:line) | recommended_fix |
|---|---|---|---|---|---|---|---|
| 1 | `CampaignResponse.title` | *(absent)* | `str` (required) | *(no such field)* | Historical artifact — designed for a standalone Campaign model that was replaced by PlacementRequest alias | campaigns.py:67, campaign.py:14 | Delete field; map `title` to `ad_text[:50]` like `CampaignItem` does at campaigns.py:466 |
| 2 | `CampaignResponse.text` | `PlacementRequest.ad_text` | `str` (required) | `str` NOT NULL | Name mismatch — `text` was renamed to `ad_text` in model rebuild | campaigns.py:68 vs placement_request.py:84 | Rename `text → ad_text` in schema |
| 3 | `CampaignResponse.filters_json` | `PlacementRequest.meta_json` | `dict \| None` | `JSONB \| None` | Name mismatch — `filters_json` → `meta_json`; also present in `CampaignUpdate` which writes it to wrong key | campaigns.py:70 vs placement_request.py:157 | Rename to `meta_json` or remove if distinct semantics are needed |
| 4 | `CampaignResponse.scheduled_at` | `PlacementRequest.proposed_schedule` | `str \| None` | `datetime \| None` | Name + type mismatch — both the key name and serialization format differ | campaigns.py:71 vs placement_request.py:87 | Rename to `proposed_schedule`, change type to `datetime \| None` |
| 5 | `CampaignResponse.created_at` | `PlacementRequest.created_at` | `str` | `datetime` | Type mismatch — schema stringifies, model stores datetime; `from_attributes=True` will coerce via FastAPI JSON encoder | campaigns.py:72 vs placement_request.py (TimestampMixin) | Change to `datetime` — FastAPI/Pydantic handles serialization |
| 6 | `CampaignResponse.updated_at` | `PlacementRequest.updated_at` | `str` | `datetime` | Same as #5 | campaigns.py:73 vs placement_request.py (TimestampMixin) | Change to `datetime` |
| 7 | `ChannelSettingsResponse.owner_payout` | *(absent)* | `Decimal` | *(not a DB column)* | Intentional computed field — calculated in router as `price_per_post × 0.85`; `from_attributes=True` is misleading | channel_settings.py:40,119 | Mark as computed: remove `from_attributes=True` (schema is always constructed manually) or use Pydantic v2 `@computed_field` |
| 8 | `ChannelResponse.owner_id` | `TelegramChat.owner_id` | `int` (required) | `int` NOT NULL | Omitted in `activate_channel` constructor — **STOP-2** | channels.py:558 | Add `owner_id=channel.owner_id` to the constructor call |
| 9 | `ChannelResponse.created_at` | `TelegramChat.created_at` | `str` (required) | `datetime` | Type mismatch + omission in `activate_channel` — **STOP-2** | channels.py:558 | Add `created_at=channel.created_at.isoformat()` to constructor |
| 10 | `PlacementCreateRequest.proposed_price` | `PlacementRequest.proposed_price` | `int` | `Numeric(10,2)` / `Decimal` | Intentional: frontend sends integer, router converts `Decimal(str(v))` at placements.py:388 | placements.py:176, placements.py:388 | Low risk — explicit conversion is safe; optionally change to `Decimal` for clarity |
| 11 | `ChannelSettingsUpdateRequest.price_per_post` | `ChannelSettings.price_per_post` | `int \| None` | `Numeric(10,2)` / `Decimal` | Same intentional int→Decimal pattern | channel_settings.py:60, channel_settings.py:163 | Same recommendation as #10 |
| 12 | `ActResponse.act_number` | `Act.act_number` | `str \| None = None` | `str` NOT NULL | Schema is more permissive than model; `act_to_response()` constructs manually — no crash | schemas/act.py:22 vs models/act.py:33 | Change to `str` to match model and tighten API contract |
| 13 | `UserResponse.first_name` | `User.first_name` | `str \| None = None` | `str` NOT NULL | Schema is more permissive than model; DB guarantees non-null | users.py:38 vs user.py:55 | Change to `str` to match model; misleading contract otherwise |

---

## CampaignResponse.title deep dive

### Schema definition

```python
# campaigns.py:63–76
class CampaignResponse(BaseModel):
    id: int
    title: str          # ← required, no default
    text: str           # ← required, no default
    status: str
    filters_json: dict[str, Any] | None = None
    scheduled_at: str | None = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
```

### Underlying model (PlacementRequest alias)

```python
# campaign.py:14
from src.db.models.placement_request import PlacementRequest as Campaign
```

`PlacementRequest` fields vs `CampaignResponse`:

| Schema field | Exists in PlacementRequest? | Matching model field |
|---|---|---|
| `title` | **NO** | — |
| `text` | **NO** | `ad_text` |
| `filters_json` | **NO** | `meta_json` |
| `scheduled_at` | **NO** | `proposed_schedule` |
| `created_at` | YES | `created_at` (but type mismatch: str vs datetime) |
| `updated_at` | YES | `updated_at` (same type mismatch) |

### All `model_validate` / return points (all crash)

```python
# campaigns.py:119 — POST /campaigns
return placement_request               # FastAPI auto-validates → crash

# campaigns.py:156 — GET /campaigns
CampaignResponse.model_validate(c)    # explicit call → crash

# campaigns.py:200 — GET /campaigns/{id}
return placement_request               # FastAPI auto-validates → crash

# campaigns.py:255 — PATCH /campaigns/{id}
return updated                         # FastAPI auto-validates → crash
```

### Working workaround in Mini App endpoint (campaigns.py:462–474)

```python
# CampaignItem — not CampaignResponse — builds title manually:
CampaignItem(
    id=camp.id,
    title=camp.ad_text[:50] if camp.ad_text else "Без названия",  # ← ad_text used
    status=camp.status.value ...,
    ...
)
```

### Root cause

`CampaignResponse` was written before the v4.2 model consolidation that replaced the standalone
`Campaign` ORM model with `PlacementRequest`. Fields `title`, `text`, `filters_json`,
`scheduled_at` existed on the old model. After aliasing `Campaign = PlacementRequest`, only the
Mini App `/list` endpoint was updated to use `CampaignItem`; the four CRUD endpoints were not.

### CampaignUpdate.filters_json — secondary impact

```python
# campaigns.py:54–60
class CampaignUpdate(BaseModel):
    title: str | None = ...
    text: str | None = ...
    filters_json: dict[str, Any] | None = None
    scheduled_at: str | None = None

# campaigns.py:252–254
update_data = placement_request_data.model_dump(exclude_unset=True)
updated = await placement_repo.update(placement_request_id, update_data)
```

If a client sends `filters_json`, `update_data` will contain `{"filters_json": {...}}`.
`placement_repo.update()` will attempt `setattr(placement_request, "filters_json", ...)` which does
not exist on the model. SQLAlchemy silently ignores unknown attributes set this way — the value is
never persisted.

### Recommended fix for CampaignResponse

Replace `CampaignResponse` with a corrected schema:

```python
class CampaignResponse(BaseModel):
    id: int
    ad_text: str                             # was: text (wrong name)
    status: str
    meta_json: dict[str, Any] | None = None  # was: filters_json (wrong name)
    proposed_schedule: datetime | None = None # was: scheduled_at (wrong name + type)
    created_at: datetime                      # was: str (type mismatch)
    updated_at: datetime                      # was: str (type mismatch)
    # title REMOVED — no such field on PlacementRequest
    # (for display use ad_text[:50])

    model_config = {"from_attributes": True}
```

Update `CampaignUpdate` and `DuplicateResponse` similarly. The `duplicate_placement_request`
docstring "Копируется: title, text, filters_json" is also incorrect — it copies only `ad_text`.

---

## ChannelSettings.owner_payout deep dive

### Where it is computed

`owner_payout` is **not a model field**. It is a computed value calculated in the router on every
read and every update of channel settings.

**Formula (channel_settings.py:119 and 221):**
```python
from src.constants.payments import OWNER_SHARE  # = Decimal("0.85")

owner_payout = settings.price_per_post * OWNER_SHARE
# e.g.: price_per_post = 1000.00 → owner_payout = 850.00
```

**Usage:**
```python
# channel_settings.py:121–139 — GET /channel-settings/
return ChannelSettingsResponse(
    channel_id=settings.channel_id,
    price_per_post=settings.price_per_post,
    owner_payout=owner_payout,          # ← injected, not from ORM
    ...
)

# channel_settings.py:223–241 — PATCH /channel-settings/
return ChannelSettingsResponse(
    ...
    owner_payout=owner_payout,          # ← same injection
    ...
)
```

**Classification:** Intentional computed field. This is architecturally sound — the platform fee
(15%) is a business constant and there is no need to store the owner share separately. However:

1. `model_config = {"from_attributes": True}` (channel_settings.py:54) is misleading because
   `ChannelSettingsResponse` is **always** constructed manually, never via `model_validate()`.
   If someone later calls `ChannelSettingsResponse.model_validate(settings_orm)`, `owner_payout`
   will not be present in the ORM object → `ValidationError`.

2. `OWNER_SHARE` is `Decimal("0.85")` (85%). This matches CLAUDE.md commission model.
   The formula is correct.

**Recommended fix:** Remove `from_attributes = True` from `ChannelSettingsResponse` (the schema is
never used with `model_validate`). Consider renaming `owner_payout` to `owner_payout_preview` to
signal it is a derived value, not a stored one.

---

## Recommended order of fixes

Ordered by severity (runtime crashes first, paper issues last):

### Priority 1 — Runtime crashes (fix before any testing)

1. **STOP-1: Rewrite `CampaignResponse`** (campaigns.py:63)
   - Delete `title`, rename `text → ad_text`, rename `filters_json → meta_json`,
     rename `scheduled_at → proposed_schedule`, change `created_at`/`updated_at` to `datetime`.
   - Update `CampaignUpdate` the same way.

2. **STOP-2: Fix `activate_channel`** (channels.py:558)
   - Add `owner_id=channel.owner_id` and `created_at=channel.created_at.isoformat()` to the
     `ChannelResponse(...)` constructor call.

### Priority 2 — Architectural smells (fix in S-34 or S-35)

3. **Remove `from_attributes=True` from `ChannelSettingsResponse`** (channel_settings.py:54)
   — it is never used with ORM objects; the flag is misleading.

4. **Tighten `ActResponse.act_number` to `str`** (schemas/act.py:22)
   — matches model constraint and tightens the API contract.

5. **Tighten `UserResponse.first_name` to `str`** (users.py:38)
   — matches model constraint; current `Optional` misleads API consumers.

### Priority 3 — Low-risk type coercions (backlog)

6. **`PlacementCreateRequest.proposed_price: int → Decimal`** (placements.py:176)
   — Current int→Decimal conversion at placements.py:388 is safe; changing the schema to `Decimal`
   removes the manual cast and aligns with model type. Frontend `number` coerces to Decimal fine.

7. **`ChannelSettingsUpdateRequest.price_per_post: int → Decimal`** (channel_settings.py:60)
   — Same pattern as #6.

---

🔍 Verified against: `d195386` (HEAD feature/s-31-legal-compliance-timeline) | 📅 Updated: 2026-04-17T00:00:00Z
