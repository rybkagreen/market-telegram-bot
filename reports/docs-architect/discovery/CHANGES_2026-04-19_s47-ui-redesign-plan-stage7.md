# Changes: S-47 Stage 7 fix-plan chapter — UI/UX redesign per Design System v2
**Date:** 2026-04-19T00:00:00Z
**Author:** Claude Code
**Sprint/Task:** S-47 planning deliverable (Stage 7 of the 6→7 fix plan)
**Branch:** `feat/s-44-missing-integration` (doc-only commit, merged forward
to `develop` and `main`)

## Scope
Дополнение к fix-плану `reports/20260419_diagnostics/` после получения
handoff-бандла `Test Avatars-handoff.zip` от Claude Design. Добавлен Этап 7
«UI/UX redesign по Design System v2» и обновлён индекс плана. Кодовых
изменений нет — это планирующий артефакт для следующего спринта.

## Affected Files

### Plan chapters (вне git — `reports/20260419_diagnostics/` под `.gitignore`)
- `reports/20260419_diagnostics/FIX_PLAN_07_ui_redesign_ds_v2.md` — **новый**.
  20 подэтапов (7.0–7.20):
  - 7.0 перенос handoff-бандла в `reports/design/...` под git
  - 7.1 Design tokens v2 (OKLCH, accent-2, light-mode) в `@theme`
  - 7.2 Outfit / DM Sans / JetBrains Mono + Icon-компонент (миграция с
    `lucide-react`)
  - 7.3 PortalShell v2 (Sidebar grouped nav + Topbar breadcrumb/search/role/bell)
  - 7.4 Shared primitives (`Card` v2, `Sparkline`, `StatTile`, `Pill`,
    `ProgressBar`, `LinkButton`, `NotificationIcon`)
  - 7.5 Cabinet полный редизайн (greeting + hero + 2×2 grid + feeds)
  - 7.6 BalanceHero × 3 варианта (split/unified/rail)
  - 7.7 PerformanceChart dual-line income/expense
  - 7.8 QuickActions 6-tile grid
  - 7.9 NotificationsCard «Требует внимания»
  - 7.10 ProfileCompleteness (ring + checklist)
  - 7.11 RecommendedChannels row
  - 7.12 RecentActivity tabs (transactions + campaigns)
  - 7.13 Role switcher (Zustand store)
  - 7.14 Command palette stub (⌘K)
  - 7.15 Density toggle
  - 7.16 Light-mode polish
  - 7.17 **редизайн всех 30+ экранов** web_portal (per-screen чек-лист)
  - 7.18 A11y pass (focus, ARIA, reduced-motion)
  - 7.19 Performance & bundle (icon tree-shake, memo)
  - 7.20 Storybook + visual regression (stretch)
- `reports/20260419_diagnostics/FIX_PLAN_00_index.md` — добавлена строка
  «7. UI/UX redesign (DS v2) — P1 — 40–56 ч», итого по плану 86–118 ч;
  добавлен go/no-go критерий после Этапа 7 (Lighthouse a11y ≥ 95,
  0 импортов `lucide-react` из screens/components, docker prod-образ
  собирается).

### Tracked deliverables (`reports/docs-architect/discovery/` — whitelist)
- `reports/docs-architect/discovery/CHANGES_2026-04-19_s47-ui-redesign-plan-stage7.md`
  — **этот файл**.
- `reports/docs-architect/discovery/NEXT_SESSION_PROMPT_2026-04-20.md` — уже
  закоммичен (d8dede7); ссылается на Stage 7 как опциональный Этап B
  следующей сессии.

### Handoff bundle (Untracked, обработается в §7.0 следующего спринта)
- `/opt/market-telegram-bot/Test Avatars-handoff.zip` (~329KB).
- Распакованный снимок содержимого использовался при составлении плана:
  `globals.css` (DS tokens), `tokens.jsx`, `App.jsx`, `Sidebar.jsx`,
  `Shared.jsx` (Topbar/Sparkline/Card/LinkButton), `Balance.jsx`,
  `Chart.jsx`, `QuickActions.jsx`, `RightColumn.jsx`, `BottomSections.jsx`,
  `icons.jsx`.

## Business Logic Impact
Нет — документ планирующий. Будущие реализации §§ 7.1–7.20 затронут все
экраны web_portal (визуальный редизайн + частично новые backend-endpoints
для Balance «Заморожено», cashflow-chart, attention-feed, recommended
channels — см. секцию «Backend touchpoints» в FIX_PLAN_07).

## API / FSM / DB Contracts
Нет. Stage 7 **может** ввести 4 новых GET-endpoint'а (см. Backend
touchpoints в FIX_PLAN_07), но конкретные контракты утверждаются на
этапе реализации.

## Migration Notes
Нет. Имплементация Stage 7 пойдёт по git-flow `CLAUDE.md` (feature →
develop → main, --no-ff).

## Verification
- Handoff-бандл прочитан целиком: 10 `.jsx` + `Cabinet.html` scaffold +
  `globals.css` — все компоненты покрыты подэтапами 7.3–7.12.
- Индекс обновлён синхронно с новым файлом (86–118 ч total).
- Порядок Stage 7 относительно Stage 4/5/6 — P1, зависит от Stages 1–3 (в
  develop) + желательно Stage 5.
- Следующая сессия: `NEXT_SESSION_PROMPT_2026-04-20.md` предписывает
  сначала закрыть Stage A (prod smoke блокеры, S-48), и только потом
  опционально стартовать `feat/s-47-ui-redesign-ds-v2`.

## Known Follow-ups
- **§7.0** — перенос `Test Avatars-handoff.zip` из корня в
  `reports/design/test-avatars-handoff-2026-04-19/` должен быть **первым
  коммитом** ветки `feat/s-47-ui-redesign-ds-v2`.
- Решение по `lucide-react` → custom Icon: миграция постепенная, ESLint
  сначала warn, потом error.
- Mini-app (отдельный набор UI-компонентов в `mini_app/src/components/ui/`)
  **не входит** в Stage 7 — выравнивание токенов между web_portal и
  mini_app обсуждается отдельным спринтом после завершения S-47.
- Срок 40–56 ч амбициозный; §§ 7.14, 7.20 — первые кандидаты в вынос,
  если Stage 7 не укладывается.

🔍 Verified against: `main` HEAD (1f49f57) | 📅 Updated: 2026-04-19
