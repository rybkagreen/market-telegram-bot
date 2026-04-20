# CHANGES — S-47 pre-merge — deduplicate breadcrumbs

**Sprint:** S-47 (UI redesign DS v2), Phase 8 pre-merge follow-up.

## Symptom

After the Topbar breadcrumb work landed (commits `c916cf9`, `52b50e3`,
`dd5ae04`), every screen in the portal showed **two** breadcrumb chains
— one in the header Topbar and a second inside the screen body,
directly above the page title.

## Root cause

`ScreenHeader` (`web_portal/src/shared/ui/ScreenHeader.tsx`) had always
exposed an optional `crumbs?: string[]` prop that rendered a small
breadcrumb chain above the title. Most screens populated it with
hand-written arrays (`crumbs={['Реклама', 'Мои кампании']}`). When the
Topbar gained its own route-driven breadcrumb renderer, these in-screen
chains were not removed and the UI ended up duplicating the same
information.

## Fix

Single-source the breadcrumbs in the Topbar. The Topbar chain is the
production one: it handles dynamic-route normalisation (`/own/channels/42`
→ `/own/channels/:id`), collapses intermediate crumbs on mobile, and
renders parent-path crumbs as clickable `<Link>`s. In-screen chains
are removed wholesale:

- `ScreenHeader.tsx` — `crumbs` prop and its render block deleted;
  component is now just title + subtitle + action.
- `components/admin/TaxSummaryBase.tsx` — the pass-through `crumbs` prop
  and its `['Администратор', 'Бухгалтерия']` default removed.
- `stores/portalUiStore.ts` — the `breadcrumbs` / `setBreadcrumbs`
  slice was never read by any component (Topbar uses a static map),
  removed as dead code.
- **50 screen files** under `screens/{admin,advertiser,owner,common,
  shared}/` — every `crumbs={[…]}` JSX attribute stripped. Text values
  were identical to what the Topbar now derives from the route path,
  so no information is lost.
- `screens/advertiser/campaign/_shell.tsx` — removed the now-unused
  `currentLabel` local that was only used by the deleted crumbs slot.

## Files

See the commit `2d700c8 refactor(web-portal): single-source breadcrumbs
in Topbar` — 53 files changed, +1 / −84.

## Quality gates

- `npx tsc -b --noEmit` (project-references strict build) → clean
- `docker compose up -d --build nginx` → build succeeded (initial
  build caught an unused `currentLabel` variable; fix included in the
  same commit before push)
- `curl -sk https://portal.rekharbor.ru/` → 200 / 38 755 B (unchanged
  sprite + style block from the iOS fix)

## Not changed

- Topbar `BREADCRUMB_MAP` and normalisation logic — untouched.
- Every screen's title / subtitle / action — unchanged.
- Route definitions in `App.tsx` — unchanged.
- Backend, DB, Celery.

🔍 Verified against: `aa767b0` | 📅 Updated: 2026-04-20
