# CHANGES 2026-05-14 — BL-107 Phase B.5b (Admin review frontend + owner submission UI)

## Context

Frontend half of BL-107 manual evidence path. Consumes Phase B.5a backend
contracts (5 endpoints, 9 Pydantic schemas, 21 tests pinning shape) and
delivers full UI workflow for both administrators and channel owners.

**What this enables:**
- Admins navigate `/admin/channel-verifications` to see pending submission queue.
- Admins drill into detail view to read submission + history + approve/reject
  with required reason and optional internal notes.
- Channel owners (member_count ≥ 10k) navigate from existing `OwnChannelDetail`
  screen → "Реестр блогеров (ФЗ-303)" entry → submission form (application_number
  required + optional registry_url + optional notes).
- All UI strings hardcoded Russian per existing convention (no i18n keys
  exist в repo).

After this commit BL-107 manual evidence path is end-to-end live in both
backend (B.5a) и frontend (B.5b).

Built atop Phase B.5a (`59cf1ef`). Backend contracts unchanged.

## Changes

### New file — `web_portal/src/api/admin_channel_verifications.ts`

API client module mirroring Phase B.5a Pydantic schemas:

| Export | Purpose |
|---|---|
| `ChannelVerificationStatus` (type) | `'pending_review' | 'verified'` |
| `ChannelVerificationSubmitRequest` | (unused в web_portal — owner submit path) |
| `ChannelVerificationSubmitResponse` | (unused) |
| `ChannelVerificationListItem` | List item |
| `ChannelVerificationListResponse` | Paginated list wrapper |
| `ChannelVerificationHistoryEntry` | Audit log entry |
| `ChannelVerificationDetailResponse` | Detail view |
| `ChannelVerificationVerifyRequest/Response` | Verify pair |
| `ChannelVerificationRejectRequest/Response` | Reject pair |
| `listChannelVerifications(params)` | GET /admin/channel-verifications |
| `getChannelVerificationDetail(channelId)` | GET /admin/channel-verifications/{id} |
| `verifyChannelManually(channelId, body)` | POST .../verify |
| `rejectChannelVerification(channelId, body)` | POST .../reject |

`api` instance imported from `@shared/api/client` per existing convention
(matches `admin.ts`, `disputes.ts`, etc.). Query params via `URLSearchParams`.

### New file — `web_portal/src/hooks/useChannelVerificationQueries.ts`

React Query hooks (mirror `useFeedbackQueries.ts` pattern):
- `useAdminChannelVerifications(params)` — list query, staleTime 30s.
- `useAdminChannelVerificationDetail(channelId | null)` — detail query
  с `enabled: channelId != null` guard.
- `useVerifyChannelManually()` — mutation; on success invalidates both
  detail и list query keys.
- `useRejectChannelVerification()` — same pattern с reject mutation.

### New file — `web_portal/src/screens/admin/AdminChannelVerificationsList.tsx`

Paginated admin queue (pattern parallel `AdminDisputesList.tsx`):
- Filter chips: `pending_review` (default) / `verified`
- Pagination: page × limit=20, prev/next buttons disabled appropriately
- Row click → `/admin/channel-verifications/:id`
- Empty state via `EmptyState` (icon=`channels`)
- Loading/error states via `Skeleton` / `Notification`
- UI: `@shared/ui` components (`Button`, `Icon`, `ScreenHeader`, etc.)
- Strings: hardcoded Russian per existing convention

### New file — `web_portal/src/screens/admin/AdminChannelVerificationDetail.tsx`

Detail view + inline verify/reject forms:
- Two-column layout (channel info | status meta) с full audit fields
- History section rendering audit log entries (3 action types translated
  to Russian labels)
- Action buttons visible only when applicable:
  - Verify: `submitted && !verified`
  - Reject: `submitted` (allows reject of already-verified — backend will 409
    but parsed gracefully)
- Inline forms (no separate modal component — match dispute resolve pattern):
  - Verify form: optional notes textarea + confirm/cancel
  - Reject form: required reason textarea (validated inline) + optional
    internal_notes + confirm/cancel
- After action: success → navigate back to list; error → red Notification
- Mutations from hooks; `isPending` disables buttons

### Modified — `web_portal/src/components/layout/Sidebar.tsx`

Added admin sidebar entry positioned between Споры и Обращения:
```typescript
{ id: 'admin-channel-verifications', label: 'Проверка каналов',
  path: '/admin/channel-verifications', icon: 'channels', adminOnly: true }
```

### Modified — `web_portal/src/App.tsx`

Added 2 lazy imports + 2 routes:
- `admin/channel-verifications` → `AdminChannelVerificationsList`
- `admin/channel-verifications/:id` → `AdminChannelVerificationDetail`

### Modified — `web_portal/src/components/layout/Topbar.tsx`

Added breadcrumb entries для both routes (matches existing pattern для
admin/disputes, admin/feedback, etc.).

### Modified — `mini_app/src/api/channels.ts`

Added `submitRegistryEvidence(channelId, data)` + 2 type aliases
(`RegistryEvidenceSubmitRequest`, `RegistryEvidenceSubmitResponse`).
Co-located с existing channel API per mini_app convention.

### Modified — `mini_app/src/hooks/queries/useChannelQueries.ts`

Added `useSubmitRegistryEvidence` mutation hook с standard mini_app pattern:
- Invalidates `['channels', 'my']` + `['channels', id, 'settings']`
- Success toast: "Заявка отправлена на проверку"
- Error toast: "Ошибка при отправке заявки" + Sentry capture

### New files — mini_app submission screen

- `mini_app/src/screens/owner/OwnSubmitRegistryEvidence.tsx`:
  - 3 form fields (application_number required + 2 optional)
  - Vanilla validation (no zod here — keeps screen self-contained per
    existing mini_app pattern for simple forms)
  - Inline error messages под каждым input
  - Haptic feedback на tap + success
  - Success: navigate to `/own/channels/{id}`
  - Cancel button → same destination
- `mini_app/src/screens/owner/OwnSubmitRegistryEvidence.module.css`:
  - CSS modules per mini_app convention (matches `OwnAddChannel.module.css`)
  - `.field`, `.label`, `.input`, `.textarea`, `.invalid`, `.error`, `.hint`

### Modified — `mini_app/src/App.tsx`

Added lazy import + route `/own/channels/:id/submit-registry-evidence`.

### Modified — `mini_app/src/screens/owner/OwnChannelDetail.tsx`

Added entry-point button (visible когда `channel.member_count >= 10000`):
```typescript
<MenuButton icon="🪪" iconBg="var(--rh-accent-muted)"
  title="Реестр блогеров (ФЗ-303)"
  subtitle="Подать заявление о регистрации"
  onClick={() => navigate(`/own/channels/${channel.id}/submit-registry-evidence`)}
/>
```

**Note on visibility heuristic:** entry button shows for any channel ≥10k.
The mini_app `Channel` type doesn't expose `is_blogger_registry_verified`
(backend `ChannelResponse` schema doesn't include the field), so already-verified
channels would still see the button. The backend 409 response is parsed
gracefully through existing error toast pattern. Exposing the verification
flag в `ChannelResponse` is out-of-scope for B.5b (backend schema change);
deferred to a future B.5b polish PR if UX impact is reported.

## Untouched (deferred к subsequent phases)

- **Component tests (vitest)** — DEVIATION #9 acknowledged: neither web_portal
  nor mini_app has vitest infrastructure (only Playwright in web_portal/tests/).
  Component test coverage deferred к Phase B.9 alongside Playwright E2E
  unblock (BL-002 mock infrastructure ships in Phase B.8). API contract
  shape is already pinned by Phase B.5a's 21 backend tests.
- **Phase B.6** — Celery periodic task для re-verification.
- **Phase B.7** — O.7 carve-out (bot handler `is_test` FSM step).
- **Phase B.8** — BL-002 mock infrastructure (custom aiohttp stub +
  docker-compose.test.yml).
- **Phase B.9** — E2E + Playwright unblock.
- **Backend schema** — `ChannelResponse` could expose
  `is_blogger_registry_verified` для better UX (button gating), but adding
  it is a backend change outside B.5b scope. Documented above.
- BACKLOG.md updates (deferred to BL-107 closure).

## Verification

- Backend `make typecheck`: 0/304 ✓
- Backend `make lint`: 7 baseline preserved ✓
- Backend `pytest tests/unit/test_bl107_*.py`: 78/78 ✓ (all B.1-B.5a tests)
- web_portal `tsc -b`: clean ✓
- web_portal `npm run lint`: **2 errors + 6 warnings (BL-024 baseline preserved)** ✓
- mini_app `tsc -b`: clean ✓
- mini_app `npm run lint`: **1 error + 1 warning (baseline preserved)** ✓
- `alembic check`: drift-free ✓ (Phase B.5b doesn't touch schema)

## Decisions echoed (Phase A2 design + empirical)

- **Q11:** Stack identical между web_portal/mini_app — ky + react-query +
  react-hook-form + zod + react-router v7. Empirically confirmed via
  `package.json` comparison.
- **Q12:** Pattern reuse — `AdminDisputesList` → `AdminChannelVerificationsList`,
  `AdminDisputeDetail` → `AdminChannelVerificationDetail`, `useFeedbackQueries`
  → `useChannelVerificationQueries`. No new abstractions introduced.
- **Q13:** Form library — vanilla state + manual validation для mini_app
  submission screen (3 fields, simple enough). react-hook-form available
  but unused — matches mini_app `OwnAddChannel` pattern (also vanilla).
- **Q14:** UI components — web_portal uses `@shared/ui` (Button, Textarea,
  Icon, etc.); mini_app uses `@/components/ui` + CSS modules. Empirically
  divergent — different design systems, intentional.
- **Q15:** Sidebar position — between Споры and Обращения (semantically
  groups admin-driven moderation tasks).
- **Q16:** No vitest infrastructure → no component tests added in this phase.
  Surface gap documented; defers to Phase B.9.

## What BL-107 Phase B.5b delivers (end-to-end live)

After this commit ships:
- **Admin workflow live:** /admin/channel-verifications list →
  /admin/channel-verifications/:id detail → verify (with notes) / reject
  (with reason + internal notes) → owner notified via Phase B.5a Celery
  enqueue → audit trail recorded.
- **Owner workflow live:** OwnChannelDetail (≥10k channels) → entry button →
  submission form → POST evidence → admins notified → owner sees toast →
  waits for admin decision.
- **Manual evidence path complete (backend + frontend)** for channels that
  cannot be auto-verified through @Trustchannelbot admin presence (Phase
  B.4 primary path).

🔍 Verified against: branch HEAD pre-commit | 📅 Created: 2026-05-14
