# 2026-05-11 — B.5 advertiser mediakit preview screen (mini_app frontend)

## What

Adds advertiser-facing mediakit preview screen в mini_app Telegram WebApp.
Consumer of B.5.1 backend endpoint `GET /api/channels/{channel_id}/mediakit`.

Triggered by ⓘ icon button on `ChannelCard` (preserves existing card-body
select-toggle behavior via `e.stopPropagation()` on the info button).
Drills into new sibling route `/adv/channels/:channelId/mediakit` showing
`description` / `audience_description` / `avg_post_reach` / `updated_at`
with loading (Skeleton) and 404 → EmptyState ("Медиакит недоступен")
fallbacks.

## Files

### Frontend

- `mini_app/src/api/mediakit.ts` (new) — ky wrapper + TS interface
  `MediakitAdvertiserResponse` mirroring backend B.5.1 schema verbatim.
- `mini_app/src/hooks/queries/useMediakitQueries.ts` (new) —
  `useChannelMediakit` TanStack Query hook (`retry: false` для 404 finality,
  `staleTime: 2min`, queryKey `['channels', channelId, 'mediakit']`).
- `mini_app/src/hooks/queries/index.ts` (extended) — re-export new hook.
- `mini_app/src/screens/advertiser/ChannelMediakitView.tsx` (new) — screen.
- `mini_app/src/App.tsx` (extended) — lazy import + new sibling route
  `adv/channels/:channelId/mediakit`.
- `mini_app/src/components/ui/ChannelCard.tsx` (modified) — new optional
  `onInfoClick?: () => void` prop, renders `<button>` с lucide-react `Info`
  icon в header. `handleInfoClick` calls `e.stopPropagation()` before
  invoking caller to preserve card-body select-toggle.
- `mini_app/src/components/ui/ChannelCard.module.css` (modified) — new
  `.infoButton` class (32×32 circle, accent hover, focus-visible outline).
- `mini_app/src/screens/advertiser/campaign/CampaignChannels.tsx` (modified)
  — pass `onInfoClick` callback navigating to mediakit route с route state
  `{ channelTitle, channelUsername }` для optional header display.

### Docs

- `reports/docs-architect/discovery/CHANGES_2026-05-11_b5-mediakit-advertiser-preview.md`
  (this file).

## Architecture

- **Screen → hook → api-module path discipline**: screen calls
  `useChannelMediakit`, hook calls `getChannelMediakit` in `api/mediakit.ts`.
  Single source of truth для backend contract.
- **404 graceful handling** — query error rendered as EmptyState
  "Медиакит недоступен. Владелец канала ещё не опубликовал медиакит."
  Parity между unpublished-draft / not-exists / no-mediakit (no draft leak).
- **Wizard state preservation**: new route is **sibling** to
  `/adv/campaigns/new/channels`, not nested. Wizard Zustand store
  `useCampaignWizardStore` is `create()` без persist middleware
  (in-memory singleton) — navigation away и back preserves
  `selectedChannels` and всё другое state. Verified в Phase A.
- **Auth**: reuses existing ky `beforeRequest` Bearer injection. No
  auth code touched.
- **ChannelCard non-regression**: new optional prop `onInfoClick` is
  additive. ⓘ button uses `e.stopPropagation()`; existing card-body
  `onClick` (used as select-toggle в `CampaignChannels`) behavior unchanged.
- **Channel name display**: route state from ChannelCard click passes
  `{ channelTitle, channelUsername }`. Screen renders it via
  `<Text variant="sm" color="muted">` под heading. На page refresh state
  is lost → screen falls back to generic "Медиакит" title only
  (no backend endpoint exists для advertiser to fetch channel basics —
  `GET /channels/{id}` is owner-only, returns 403).

## Component prop adaptations (vs prompt example)

Prompt example used several non-existent prop names. Verified actual
component APIs в Phase A и adapted:

- `ScreenShell` has NO `title` prop — render own `<Text variant="lg"
  weight="semibold" as="h1">` as first child for screen heading.
- `Text` variants: actual `xs|sm|md|lg|xl` (NOT `heading-sm`/`body`/`caption`)
  — used `variant="lg" weight="semibold"` для headings, `variant="sm"
  color="muted"` для caption (updated_at).
- `Card` has built-in `title` prop — used it directly для section headers
  ("Описание канала", "Аудитория", "Средний охват поста").
- Layout: inline `style={{ display: 'flex', flexDirection: 'column',
  gap: 'var(--rh-space-3)' }}` — gives access к design tokens without
  introducing a new CSS module file (within sub-block scope per P1).

## Verification

### Frontend gates

- `cd mini_app && npm run lint`: **1 error + 1 warning** —
  identical к pre-edit baseline (Analytics.tsx:115:46 `Date.now` impure;
  OwnAddChannel.tsx:27:3 unused-disable). No new lint issues
  introduced by B.5.
- `cd mini_app && npm run build` (`tsc -b && vite build`):
  **clean**, exit 0, 900ms.

### Backend baseline preserved bit-for-bit

- `make format-check`: 0
- `make lint`: 7 (BL-024 — known baseline)
- `make typecheck` (mypy): 0 errors in 293 source files
- `make ci-local` pytest: **0F / 1013P / 2S / 0E** (identical к pre-B.5)

`make ci-local` exit code: 1 — caused by BL-024 ruff baseline as expected.

### Other frontends

- `web_portal/`: 2 errors + 6 warnings preserved (untouched).
- `landing/`: untouched (no diff).

## Phase B progress

- B.1 + B.2 + B.3 + B.4 + B.5.1 ✅ merged
- **B.5 (mini_app frontend)** ✅ THIS COMMIT
- B.6 (docs sweep + ship — CHANGELOG, BACKLOG closeouts) ⏸ pending

## Deferred to B.6 / BACKLOG

- **Logo display** — backend returns `logo_file_id` (Telegram file_id),
  но no frontend image proxy / resolver exists today. BACKLOG candidate:
  "Mediakit logo resolver — Telegram file_id image proxy endpoint" (BL-086 ?).
- **theme_color tinting** — `MediakitAdvertiserResponse.theme_color`
  not applied as background tint. Current screen uses neutral
  Tailwind tokens. BACKLOG candidate: "Mediakit theme_color tinting" (BL-087 ?).
- **Frontend test infrastructure** — mini_app has no Vitest/Playwright,
  no tests added (auto-defer per PROMPT_26 probe surprise #3).
- **mini_app dep hygiene** (PROMPT_26 surprise #1):
  `@telegram-apps/sdk-react` imported never — untouched в B.5.
