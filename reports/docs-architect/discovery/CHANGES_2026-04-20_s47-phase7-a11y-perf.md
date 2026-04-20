# S-47 Phase 7 — a11y + perf + routing audit + contract verify

**Branch:** `feat/s-47-ui-redesign-ds-v2`
**Commits:** `007d8ac` → `4a2dd6f` (3 commits on top of Phase 6)
**Plan reference:** `reports/20260419_diagnostics/FIX_PLAN_07_ui_redesign_ds_v2.md` §§7.18, 7.19, 7.21, 7.22, 7.23

## Scope

Phase 7 is the wrap-up pass before merging DS v2 into `develop`:
accessibility, performance, contract sync, routing audit, and
deprecated-dependency verification. Storybook (§7.20, stretch) deferred.

## §7.23 — Lucide migration verify (no code change)

```bash
$ grep -rn "from 'lucide-react'" web_portal/src/
# → 0 matches
```

`lucide-react` was removed in an earlier S-47 phase; there is no remaining
import to migrate. Recorded as N/A.

## §7.21 — Backend contract verify (no code change)

All four Cabinet widget endpoints (implemented in Phase 3) checked
field-by-field against the web_portal TS clients and React Query hooks.
**Zero drift.**

| Endpoint | Pydantic (backend) | TS (web_portal) |
|----------|--------------------|-----------------|
| `GET /billing/frozen` | `FrozenBalanceResponse{total_frozen:Decimal, escrow_count:int, pending_payment_count:int, items:[FrozenPlacementItem]}` | `FrozenBalanceResponse{total_frozen:string, ..., items:[FrozenPlacementItem]}` |
| `GET /analytics/cashflow?days=7\|30\|90` | `CashflowResponse{period_days, total_income:Decimal, total_expense:Decimal, net:Decimal, points:[{date,income,expense}]}` | `CashflowResponse` — matches |
| `GET /users/me/attention` | `AttentionFeedResponse{items:[AttentionItem{type,severity,title,subtitle?,url?,created_at}], total:int}` | matches; all 7 `AttentionType` literals align |
| `GET /channels/recommended?limit=&category=` | `RecommendedChannelsResponse{items:[ChannelResponse], algorithm:str}` | matches |

Hooks (`useFrozenBalance`, `useCashflow`, `useAttentionFeed`,
`useRecommendedChannels`) all wired and used from the corresponding Cabinet
widgets. No refactor required.

## §7.22 — Routing audit + `/dev/icons`

**Commit** `563aabb feat(web-portal): routing audit + /dev/icons gallery (§7.22)`.

- Cross-checked `src/screens/**/*.tsx` (63 files, excluding `cabinet/*`
  widgets) against `src/App.tsx`. All 60+ route-backed screens mounted;
  no orphan screens, no dead imports.
- Added `/dev/icons` route under `import.meta.env.DEV` guard — stripped
  from prod bundle by Vite tree-shake. Gallery lists all 132
  `ICON_NAMES`, supports name filter, outline/fill toggle, size slider
  (16–48), and click-to-copy via `navigator.clipboard`.
- New file: `web_portal/src/screens/dev/DevIcons.tsx`.

## §7.18 — Accessibility pass

**Commit** `d093ec4 chore(a11y): ARIA landmarks + icon-button labels (§7.18)`.

Audited and fixed:

- **No `<div onClick>` to replace.** `grep '<div[^>]*onClick'
  web_portal/src/` returned 0 matches — all click targets are already
  proper `<button>` or `<a>` elements.
- **`:focus-visible`** was already globalised in
  `web_portal/src/styles/globals.css:143` (2px accent outline,
  2px offset). Verified; no change.
- **`prefers-reduced-motion`** was already globalised in
  `web_portal/src/styles/globals.css:111` (1ms animation + transition
  overrides). Applies to `pulse-ring` in TopUpConfirm and any
  Framer Motion usage. Verified; no change.
- **Tabs primitive** (`src/shared/ui/Tabs.tsx`) now carries
  `role="tablist"`, `role="tab"`, `aria-selected`, and a tabIndex
  roving pattern so keyboard users can land on the active tab via
  one Tab press and move via arrows (browser default for the roving
  pattern pairs with `role=tab`).
- **RecentActivity** inline tab switcher (transactions / campaigns)
  uses the same `tablist`/`tab`/`aria-selected` roles.
- **Modal** now declares `role="dialog"`, `aria-modal="true"`, and
  `aria-labelledby` tied to the title heading via `useId()`. The
  backdrop was simplified from a `div[role=button]` with custom
  keydown handling to a plain `<button>` (semantic). Close ✕ button
  gains `aria-label="Закрыть"`.
- **Topbar**: search stub button gains `aria-label="Открыть глобальный
  поиск"`; bell `aria-label` reports the unread count when the red
  dot is visible (otherwise "Уведомления"); the dot itself is
  `aria-hidden`.
- **Sidebar**, **PortalShell** landmarks (`<aside aria-label>`,
  `<nav>`, `<main>`, `<header>`) were already correct — verified.
- **Icon-only buttons audit** via
  `grep '<Icon name="(x|close|trash|edit|sort|arrow-up|arrow-down|more|filter|search)"'`
  — all non-trivial cases already had `aria-label` or `title`. The
  only addition was the Topbar search button.

**Deferred to visual review before merge:** Chrome DevTools contrast
check on secondary/tertiary text on light surfaces (`bg-harbor-card`).
Can't run headless; listed in §7.0 merge checklist.

## §7.19 — Performance & bundle

**Commit** `4a2dd6f chore(perf): memoize PerformanceChart + document bundle baseline (§7.19)`.

### Icon tree-shaking — verified non-issue

`Icon.tsx` renders `<svg><use href="/icons/rh-sprite.svg#rh-<name>"/></svg>`.
The sprite is a 37 KB static SVG in `web_portal/public/icons/`, fetched
once lazily via `IconSpriteLoader` and injected into `<body>`. No icons
are inlined into JS chunks, so an unused icon costs zero bytes per route.
No splitting needed.

### React.memo applied

- **PerformanceChart** (`src/screens/common/cabinet/PerformanceChart.tsx`):
  wrapped with `React.memo`. Props are empty, so memo becomes a stable
  "don't re-render from parent" pass. Avoids re-running the SVG-building
  JSX block (~200 lines) when Cabinet re-renders for unrelated reasons
  (`useMe` refetch, `useNavigate` invalidation, other widget state).

### React.memo NOT applied, with reasoning

- **Sparkline** — callsites in `BalanceHero.tsx:102` and
  `ReputationHistory.tsx:361` both pass `data={spark.length ? spark : [0, 0]}`
  inline. That literal `[0, 0]` is a new array on every render, which would
  defeat shallow-prop comparison, making memo a no-op. Fixing the callsites
  (module-level constant or stable-ref `useMemo`) is 2 small edits, but the
  Sparkline body is ~20 lines of O(n) SVG path building that runs in well
  under 1 ms; the cost to achieve memo safety exceeds the expected gain.
- **Recharts charts** in `AdvAnalytics` / `OwnAnalytics` — already lazy-
  loaded per-route (the 346 KB `BarChart-*.js` chunk only ships when the
  screen is visited). Memoizing the screen doesn't reduce bundle; it
  would only deduplicate renders, which are infrequent on these pages.

### Bundle totals (production build)

|                       | Before (007d8ac) | After (4a2dd6f) | Δ     |
|-----------------------|-----------------:|----------------:|------:|
| dist/ total           | 1,341,586 B       | 1,341,602 B      | +16 B |
| All JS (raw)          | 1,232,696 B       | 1,232,712 B      | +16 B |
| JS chunk count        | 92                | 92                | — |

### Largest chunks (gzip), after Phase 7

| Chunk              | Raw kB | gzip kB |  Notes |
|--------------------|-------:|--------:|--------|
| `BarChart-*.js`    | 346.06 | 101.89 | Recharts, lazy (/adv/analytics, /own/analytics only) |
| `index-*.js`       | 184.57 |  58.40 | entry chunk |
| `chunk-QFMPRPBF-*` |  92.25 |  30.34 | framer-motion (shared) |
| `App-*.js`         |  38.54 |  11.45 | App router + PortalShell eager deps |
| `Cabinet-*.js`     |  30.34 |   8.45 | unchanged post-memo |

### Lighthouse / preview

Not captured headless in this session. Visual Lighthouse run is part of
the pre-merge §7.0 checklist.

## §7.20 — Storybook

**Deferred.** Not blocking. Listed in CHANGELOG under "deferred" because
the primitives library (§7.4) is stable and there is no Storybook gap
blocking design review — `/dev/icons` covers the most-requested gallery.

## Lint / type-check

- `npx tsc --noEmit` — 0 errors after every commit (3/3).
- Pre-existing `BalanceHero.tsx` React Compiler warning unchanged.
- `docker compose up -d --build nginx api` — not run in this session
  (a11y + routing + memo changes are pure frontend; the Vite build is
  consumed by nginx at the next rebuild cycle).

## Commits

| § | Commit | Subject |
|---|--------|---------|
| 7.22 | `563aabb` | `feat(web-portal): routing audit + /dev/icons gallery (§7.22)` |
| 7.18 | `d093ec4` | `chore(a11y): ARIA landmarks + icon-button labels (§7.18)` |
| 7.19 | `4a2dd6f` | `chore(perf): memoize PerformanceChart + document bundle baseline (§7.19)` |

## Next steps (before merge)

1. Visual review on `https://portal.rekharbor.ru/` against DS v2 handoff.
2. Chrome DevTools contrast audit on secondary/tertiary text — update
   tokens in `globals.css` if any pair falls under 4.5:1.
3. Lighthouse run (Performance / Accessibility) — record scores in the
   merge PR description.
4. Merge plan per `CLAUDE.md` Git Flow:
   `feat/s-47-ui-redesign-ds-v2` → `develop` (`--no-ff`) → `main` (`--no-ff`).
5. Mark Storybook (§7.20) as a follow-up ticket in the next sprint.

🔍 Verified against: 4a2dd6f | 📅 Updated: 2026-04-20T00:00:00Z
