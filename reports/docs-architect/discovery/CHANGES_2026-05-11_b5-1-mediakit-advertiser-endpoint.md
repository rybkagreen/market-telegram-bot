# 2026-05-11 — Phase B.5.1 advertiser-readable mediakit endpoint (backend)

## What

Adds advertiser-readable mediakit JSON endpoint:

- `GET /api/channels/{channel_id}/mediakit` → 200 `MediakitAdvertiserResponse`
  если `ChannelMediakit.is_published=True`
- Otherwise 404 (consistent across: not-published / not-exists / no-mediakit)

Consumer: mini_app advertiser preview (B.5 frontend, PROMPT_28 next).
Counterpart: B.2 owner-only PDF endpoint at
`/api/channels/{channel_id}/mediakit/pdf` (already shipped).

## Files

- `src/api/schemas/mediakit.py` (new) — `MediakitAdvertiserResponse` Pydantic
  schema (6 advertiser-visible fields + `from_attributes=True`)
- `src/core/services/mediakit_service.py` (extended) — new method
  `get_published_for_advertiser(channel_id, session)` → `ChannelMediakit | None`.
  Read-only, no commits, no flushes (Pattern 1 strict, S-48).
- `src/api/routers/channels.py` (extended) — new route handler
  `get_channel_mediakit_for_advertiser` above existing `get_mediakit_pdf`.
  Uses `CurrentUser` (mini_app + web_portal audiences) и `get_db_session`.
- `tests/integration/test_mediakit_advertiser_endpoint.py` (new) —
  5 integration cases (happy / unpublished-404 / not-exists-404 /
  no-mediakit-404 / unauthenticated-401)
- `reports/docs-architect/discovery/CHANGES_2026-05-11_b5-1-mediakit-advertiser-endpoint.md`
  (this file)

## Architecture

- **Privacy gate by `is_published`**. Unpublished → 404 (NOT 403).
  Reason: 403 leaks существование unpublished draft; 404 keeps existence
  parity across all "not visible" reasons (not-published, not-exists,
  no-mediakit).
- **Excluded from response:** `is_published`, `owner_user_id`, `views_count`,
  `downloads_count`, `id`, `channel_id` (channel_id implicit от URL path).
  Advertiser sees content fields only (description, audience_description,
  logo_file_id, theme_color, avg_post_reach, updated_at) — no control fields.
- **Schema field names verified против model:**
  - `description: str | None` (nullable on model)
  - `audience_description: str | None` (nullable on model)
  - `logo_file_id: str | None` (NOT `logo` — corrected vs initial prompt)
  - `theme_color: str | None`
  - `avg_post_reach: int` (NOT NULL, default 0)
  - `updated_at: datetime` (from `TimestampMixin`)
- **S-48 compliance:** service method read-only — no `commit`, no `flush`.
  Route owns transaction lifecycle через `Depends(get_db_session)`.
- **Auth:** advertiser-accessible (same dependency as `/api/channels/available`).
  `CurrentUser = Annotated[User, Depends(get_current_user)]` — accepts
  mini_app + web_portal audiences.
- **Tests:** real-DB fixtures via existing `db_session` conftest factory;
  mirrors B.2 PDF endpoint test scaffolding (dependency_overrides for
  `get_db_session` + `get_current_user`). BL-024 — no `conftest.py` edits.

## Verification

- `make format-check`: 401 files already formatted (0 errors) ✓
- `make lint`: 7 errors (BL-024 baseline preserved — все в `tests/unit/conftest.py`) ✓
- `make typecheck`: 0 errors (293 source files, +1 vs baseline) ✓
- `make ci-local` pytest: 1013 passed (+5) / 2 skipped / 0 failed / 0 errored ✓
- `make ci-local` exit: 1 (lint baseline, expected) ✓
- Frontend baselines preserved bit-for-bit (no touch):
  - `web_portal/`: 2 errors + 6 warnings pre-existing (unchanged)
  - `mini_app/`: untouched
  - `landing/`: untouched

## Phase B progress

- B.1 + B.2 + B.3 + B.4 ✅ merged into develop
- **B.5.1 (backend mediakit endpoint)** ✅ THIS COMMIT
- B.5 (mini_app frontend) ⏸ pending — PROMPT_28 next
- B.6 (docs sweep + ship — CHANGELOG, BACKLOG closeouts) ⏸ pending

🔍 Verified against: feature/b5-1-mediakit-advertiser-endpoint (pre-commit) | 📅 Updated: 2026-05-11
