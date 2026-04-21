# CHANGES — 2026-04-21 · Docs sync deep-dive (README + docs/AAA-*)

## Scope

User request: deep research of `web_portal/`, `src/`, `mini_app/` and sync of `README.md` and every file in `docs/`.

Three parallel Explore agents produced factual inventories of backend, Mini App and Web Portal. Results cross-checked against the filesystem and fed back into `README.md` and the AAA reference set.

## Affected files

### Updated
- `README.md` — version badge, "What's New", architecture diagram, stack lists, Quick Start, project tree, DB section, dev workflow, Monitoring, Documentation index.
- `docs/AAA-01_ARCHITECTURE.md` — Key Metrics table rebuilt with verified counts; layer diagram labels updated (22 handlers, 11 FSM, 15 keyboards, 35 services, 26 repos, 12 task files / 66 tasks, 31 models / 1 migration).
- `docs/AAA-02_API_REFERENCE.md` — new router inventory table (27 routers · 131 endpoints); middleware note.
- `docs/AAA-03_DATABASE_REFERENCE.md` — header + overview rewritten for 31 models / 26 repos / 1 consolidated migration; added inventory list + models-without-repo note.
- `docs/AAA-04_SERVICE_REFERENCE.md` — header refreshed; 35-service inventory grouped by area (Billing, Placement, Reputation, Legal, Accounting, ORD, EDO, AI, Channels, Notifications).
- `docs/AAA-05_FSM_REFERENCE.md` — state group summary rewritten: 11 groups / 52 states; `CampaignCreateState` removed (merged into `PlacementStates`).
- `docs/AAA-06_CELERY_REFERENCE.md` — header, TOC counts (66 tasks, 18 beat), queue table rebuilt for the 9 real queues, worker commands corrected (`worker_critical,mailing,notifications,billing,placement`; `parser,cleanup,background`; `gamification,badges`).
- `docs/AAA-07_FRONTEND_REFERENCE.md` — Mini App and Web Portal inventories rewritten with verified counts (55 / 66 screens); Zustand store shapes updated; routing maps regenerated from `App.tsx`; new §13 *Landing Page*.
- `docs/AAA-08_ONBOARDING.md` — header + verified-numbers summary line.
- `docs/AAA-09_DEPLOYMENT.md` — header + nginx / domain mapping note (app/portal/landing).
- `docs/AAA-09_TESTING_QUALITY.md` — header + test inventory (37 pytest files + 126 Playwright specs + SonarQube scope).
- `docs/AAA-10_DISCREPANCY_REPORT.md` — header + fresh 2026-04-21 drift snapshot table (15 metrics: claim vs reality).

### Not touched (point-in-time artefacts)
- `docs/AAA-11_PRODUCTION_FIX_PLAN.md` — tied to S-29 sprint, date 2026-04-09.
- `docs/AAA-12_CONTAINER_STARTUP_DEEP_DIVE.md` — post-S-29 rebuild investigation, date 2026-04-10.

### Added
- `reports/docs-architect/discovery/CHANGES_2026-04-21_docs-sync-deep-dive.md` (this file).

## Business-logic impact

None. Documentation-only change. No code paths, API contracts, DB schema, FSM, or Celery routing were modified.

## New / changed contracts

None.

## Verified numbers (as of 2026-04-21)

Backend:
- API routers: **27** · endpoints: **131**
- Core services: **35**
- DB models: **31** · repositories: **26**
- Alembic migrations: **1** (`0001_initial_schema`, consolidated pre-prod)
- Bot handler files: **22** across 8 subdirs · FSM groups: **11** (52 states) · keyboards: **15** · middlewares: **4**
- Celery: **12 task files · 66 tasks · 9 queues · 18 periodic tasks**
- Tests: **37 pytest files** (unit 18 · integration 8 · e2e_api 7 · tasks 2 · mocks 2)

Frontend:
- Mini App: **55 screens** (common 16 · advertiser 17 · owner 11 · admin 10 · shared 1) · **45 components** · **4 Zustand stores** · **21 hooks** · **18 API modules**
- Web Portal: **66 screens** (auth 1 · common 22 · advertiser 15 · owner 10 · admin 11 · shared 6 · dev 1) · **107 `.tsx`** · **31 shared UI** · **3 Zustand stores** · **21 hooks** · **18 API modules** · **126 Playwright specs**
- Landing: static Vite + Tailwind v4 at `rekharbor.ru`.

Drift vs prior docs/CLAUDE.md is enumerated in AAA-10 §"2026-04-21 drift snapshot".

## Rationale

- The previous AAA set was last re-verified on 2026-04-08. Since then S-26/S-27/S-29, admin panel split, accounting module, Yandex ORD provider, and Web Portal expansion all shifted counts. Several claims (e.g. 137 `.tsx`, 22 Mini App screens, 33 migrations, 101 tests) no longer matched the filesystem.
- Goal of the pass: realign documentation with current code without rewriting business-logic sections that remain correct.

---

🔍 Verified against: 45bdb04 | 📅 Updated: 2026-04-21T00:00:00Z
