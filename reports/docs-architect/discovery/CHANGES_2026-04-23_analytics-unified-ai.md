# CHANGES 2026-04-23 — Unified `/analytics` screen with AI insights

## Context

The Cabinet screen (`web_portal/src/screens/common/Cabinet.tsx`) has grown
into a rich dashboard (BalanceHero, PerformanceChart cashflow, RecentActivity,
ProfileCompleteness, RecommendedChannels). Meanwhile the two legacy analytics
screens — `advertiser/AdvAnalytics.tsx` (`/adv/analytics`) and
`owner/OwnAnalytics.tsx` (`/own/analytics`) — rendered four KPI tiles + a
bar chart + a channel table, largely duplicating the Cabinet's financial
summary. The "AI recommendation" shown in `AdvAnalytics.tsx:217` was
hardcoded, not a real model call. The same dual structure existed in
`mini_app/`.

This change unifies the two legacy screens into one `/analytics`, shifts
its purpose from "more KPIs" to "why and what to do", and adds a real
Mistral-backed insights pipeline with a deterministic rule-based fallback.

## Backend

### New files

- `src/api/schemas/analytics.py` — `AIInsightsUnifiedResponse` +
  `InsightsActionItem` / `InsightsForecast` / `InsightsAnomaly` /
  `InsightsChannelFlag` Pydantic models.

### Modified

- `src/core/services/analytics_service.py`:
  - `AnalyticsService.generate_unified_insights(user_id, role, session,
    force_refresh=False)` — orchestrator: Redis cache lookup → stats
    aggregation → Mistral JSON call (8 s timeout, strict JSON prompt) →
    Pydantic-shaped sanitisation → cache write. Any Mistral failure
    (missing key, timeout, invalid JSON, Pydantic rejection) falls through
    to deterministic `_rules_advertiser` / `_rules_owner` that mirror the
    same output shape. `ai_backend` in the response is `"mistral"` or
    `"rules"` — the frontend surfaces this as a small badge.
  - `_aggregate_insights_payload` / `_get_owner_channel_breakdown` — reuse
    existing `get_advertiser_stats` / `get_owner_stats` /
    `get_top_channels_by_reach` plus a new per-channel LEFT JOIN for owner
    data.
  - Module-level helpers: `_has_mistral_key`, `_get_redis` (lazy shared
    client), `_strip_json_fence`, `_build_insights_prompt`,
    `_sanitize_mistral_payload`, `_rules_advertiser`, `_rules_owner`.
  - Redis cache key: `ai_insights:{user_id}:{role}:v1`, TTL 900 s.

- `src/api/routers/analytics.py` — `GET /api/analytics/ai-insights`:
  - Query `role={advertiser|owner}` (regex-validated, 422 on junk).
  - Optional `nocache=1` forces a refresh (rate-limited on the FE).
  - JWT-only auth (no PRO gating, unlike
    `/campaigns/{id}/ai-insights`).

### Existing endpoints preserved

`GET /api/analytics/advertiser`, `GET /api/analytics/owner`,
`/summary`, `/activity`, `/cashflow`, `/top-chats`, `/topics`,
`/campaigns/{id}/ai-insights`, `/stats/public`, `/r/{short_code}` — all
untouched. The unified insights endpoint is purely additive.

### Contract snapshot

- `tests/unit/test_contract_schemas.py` registers
  `AIInsightsUnifiedResponse`.
- `tests/unit/snapshots/ai_insights_unified_response.json` — new snapshot
  generated via `UPDATE_SNAPSHOTS=1 poetry run pytest
  tests/unit/test_contract_schemas.py`.

## Tests

- `tests/unit/services/test_analytics_insights_service.py` — 15 tests for
  the pure helpers (rule-based engine outputs for both roles, Pydantic
  validation, JSON-fence stripping, Mistral payload sanitisation).
- `tests/unit/api/test_analytics_insights.py` — 5 tests for the HTTP
  layer (default role, `role=owner`, invalid role 422, nocache forwarding,
  rules badge preservation) with `AnalyticsService.generate_unified_insights`
  patched.

## Frontend — web_portal

### Added

- `web_portal/src/screens/common/Analytics.tsx` — unified screen.
  Detects roles from `useAdvertiserAnalytics()` / `useOwnerAnalytics()` /
  `useMyChannels()`; shows a role-switcher tab only when both roles are
  active; otherwise picks the single relevant role automatically.
- `web_portal/src/screens/common/analytics/AIInsightCard.tsx` — hero
  card: narrative summary, 3 action-items with per-kind icon +
  impact-estimate + CTA, optional forecast strip, anomalies feed, AI/Rules
  badge, rate-limited refresh button, "updated N min ago".
- `web_portal/src/screens/common/analytics/ChannelDeepDive.tsx` —
  role-aware table merging `/analytics/{role}` data with `channel_flags`
  from `/analytics/ai-insights` for the AI badge column.
- `web_portal/src/screens/common/analytics/TrendComparison.tsx` —
  Recharts bar chart: reach-by-channel (advertiser) or earnings-by-channel
  (owner).
- `web_portal/src/screens/common/analytics/RoleTabs.tsx` — pill tabs.

### Modified

- `web_portal/src/App.tsx` — registers `/analytics`; old `/adv/analytics`
  and `/own/analytics` become `<Navigate replace />` redirects with the
  role preserved as a query param.
- `web_portal/src/components/layout/Sidebar.tsx` — two "Аналитика" items
  collapsed into one under a new "Аналитика" group.
- `web_portal/src/components/layout/Topbar.tsx` — breadcrumb entries for
  `/adv/analytics` and `/own/analytics` replaced by a single entry for
  `/analytics`.
- `web_portal/src/screens/common/Cabinet.tsx` — header "Отчёт" button now
  goes to `/analytics` (and label changed to "Аналитика").
- `web_portal/src/screens/common/cabinet/QuickActions.tsx` — owner quick
  action `href` updated.
- `web_portal/src/screens/advertiser/campaign/CampaignPublished.tsx` —
  post-campaign "В статистику" navigates to `/analytics?role=advertiser`.
- `web_portal/src/api/analytics.ts` — new `getAIInsights(role, {nocache})`
  plus TS types (`InsightsActionItem`, `InsightsForecast`,
  `InsightsAnomaly`, `InsightsChannelFlag`, `AIInsightsUnifiedResponse`).
- `web_portal/src/hooks/useAnalyticsQueries.ts` — `useAIInsights(role)`
  with `staleTime: 10 min`, `refetchOnWindowFocus: false`.
- `web_portal/tests/fixtures/routes.ts` — replaces two `/{adv,own}/analytics`
  entries with a single `/analytics` under `common` routes.

### Deleted

- `web_portal/src/screens/advertiser/AdvAnalytics.tsx`
- `web_portal/src/screens/owner/OwnAnalytics.tsx`

## Frontend — mini_app

### Added

- `mini_app/src/screens/common/Analytics.tsx` — single-file equivalent
  (mini_app has no Recharts, tighter layout for Telegram WebApp). Same
  AI card + role-aware channel list.

### Modified

- `mini_app/src/App.tsx` — new `/analytics` route; `/adv/analytics` and
  `/own/analytics` become `<Navigate replace />`.
- `mini_app/src/api/analytics.ts` — `getAIInsights` + typed response.
- `mini_app/src/hooks/queries/useAnalyticsQueries.ts` — `useAIInsights`.
- `mini_app/src/screens/advertiser/AdvMenu.tsx` — menu entry navigates to
  `/analytics?role=advertiser`.
- `mini_app/src/screens/owner/OwnMenu.tsx` — menu entry navigates to
  `/analytics?role=owner`.
- `mini_app/src/screens/advertiser/campaign/CampaignPublished.tsx` — same
  redirect.

### Deleted

- `mini_app/src/screens/advertiser/AdvAnalytics.tsx` + `.module.css`
- `mini_app/src/screens/owner/OwnAnalytics.tsx` + `.module.css`

## Out of scope (by design)

- **Bot in-chat analytics** — `src/bot/handlers/advertiser/analytics.py`,
  `src/bot/handlers/owner/analytics.py`, keyboards and their
  `main:analytics` / `main:owner_analytics` callbacks. Different surface
  (text in Telegram chat, not WebApp). No changes.
- **Orphaned notification callback** (`analytics:by_campaign:{id}` sent
  in `src/tasks/notification_tasks.py:660` with no handler anywhere) —
  pre-existing bug, not in scope; noted here for future cleanup.
- **PRO/BUSINESS gated endpoints** (`/top-chats`, `/topics`,
  `/campaigns/{id}/ai-insights`) — unchanged.
- **Day-of-week × hour heatmap** — deferred to a second iteration.

## FSM / DB / Celery impact

None. No new tables, no migrations, no Celery tasks, no FSM transitions.
Redis is used for read-through caching only; no persistent state.

## Business logic impact

- New user-visible screen: "Аналитика" (`/analytics`). Shows AI-generated
  narrative summary, up to three actionable items with CTAs, a forecast,
  anomalies, a per-channel table with AI flags, and a bar chart
  (`web_portal` only).
- `/adv/analytics` and `/own/analytics` now redirect — bookmarks and
  external links continue to work.
- Mistral cost: bounded by 15-minute per-user-per-role Redis cache; a
  single active user triggers at most 96 calls/day × 2 roles = ~192 calls.
- When `MISTRAL_API_KEY` is not configured or Mistral fails / times out
  (8 s), the UI stays up with the rules-based narrative and shows a
  "Rules" badge.

---

🔍 Verified against: _will be committed — commit hash recorded in git log_
📅 Updated: 2026-04-23T22:00:00+00:00
