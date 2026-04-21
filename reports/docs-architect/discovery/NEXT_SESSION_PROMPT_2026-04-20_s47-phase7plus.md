# Стартовый промт для следующей сессии — S-47 Phase 7+ (a11y / perf / stretch)

Скопируй блок ниже в новую Claude Code сессию (после `/clear`).

---

```text
Продолжаем S-47 (UI redesign per Design System v2).

План: reports/20260419_diagnostics/FIX_PLAN_07_ui_redesign_ds_v2.md
Ветка: feat/s-47-ui-redesign-ds-v2 (НЕ мёржить — merge только после
завершения §7.18–§7.21 и визуального review)

Что УЖЕ сделано (последний коммит 007d8ac):
- Phase 1: DS v2 tokens + icon sprite (132 symbols)
- Phase 2: PortalShell v2 (Sidebar + Topbar)
- Phase 3: 4 backend endpoints для Cabinet widgets
  (/billing/frozen, /analytics/cashflow, /users/me/attention,
  /channels/recommended) — §7.21.1–7.21.4 УЖЕ РЕАЛИЗОВАНЫ.
- Phase 4: Cabinet rewrite (7 widgets)
- Phase 5: 13 handoff-pixel-perfect screens (§7.5a)
- Phase 6 (§7.17): 30 design-from-tokens экранов — advertiser wizard +
  standalones, owner (10), shared disputes + common (6), admin panel (11).
  Разбор: reports/docs-architect/discovery/
  CHANGES_2026-04-20_s47-phase6-design-from-tokens.md

Что осталось в плане §7.18–§7.23:

§7.18 — Accessibility pass
  - Заменить все `<div onClick>` на `<button>` с keyboard focus.
  - `:focus-visible` из handoff-globals.css включить по умолчанию.
  - `prefers-reduced-motion` — отключить sparkline-анимации и
    pulse-ring в TopUpConfirm.
  - ARIA landmarks в PortalShell: `<main>`, `<aside role="complementary">`
    (Sidebar), `<nav>` внутри Sidebar, `role="tablist"` в табах
    (Tabs primitive, RecentActivity).
  - `aria-label` на icon-only кнопках: logout, bell, search,
    notifications, compare-toggle, close-dialog, sort-buttons.
  - Цветовая контрастность — прогнать secondary/tertiary на светлом
    фоне через Chrome DevTools Contrast. Если < 4.5:1 — поправить токены.

§7.19 — Performance & bundle
  - Измерить baseline ДО изменений: `npm run build` → размер dist/,
    `npm run preview` + Lighthouse (Performance / Accessibility).
    Сохранить скриншот или цифры в CHANGES.
  - Проверить Icon tree-shaking. Сейчас в Icon.tsx скорее всего
    подгружается весь sprite — убедиться, что при импорте одной
    иконки не тянется вся палитра. Если тянется — разбить на
    lazy paths-map или отдельные export.
  - `React.memo` для тяжёлых виджетов: PerformanceChart, Sparkline,
    AdvAnalytics чарты (Recharts). Проверить — не ломает ли это
    рендер-цикл в BalanceHero (там уже есть useMemo на spark-данные).
  - Повторить измерения после — в CHANGES положить before/after.

§7.20 — Storybook (stretch, делать только если успеваем)
  - Поставить Storybook 8 в web_portal/.storybook/.
  - Stories для primitives (§7.4): Button, ScreenHeader, FeeBreakdown,
    StepIndicator, Notification, Icon, Sparkline, Timeline.
  - Не обязательно — если времени нет, пропустить и зафиксировать
    в CHANGELOG как «deferred».

§7.21 — Backend endpoints
  Все 4 endpoint'а (§7.21.1–§7.21.4) УЖЕ РЕАЛИЗОВАНЫ в Phase 3.
  Осталось только §7.21.5 — проверить, что TS-типы и React Query
  hooks соответствуют бэк-контракту. Проверить:
    - web_portal/src/api/billing.ts (getFrozen)
    - web_portal/src/api/analytics.ts (getCashflow)
    - web_portal/src/api/users.ts (getAttention)
    - web_portal/src/api/channels.ts (getRecommended)
  и соответствующие hooks в web_portal/src/hooks/. Если всё ок —
  зафиксировать в CHANGES «§7.21 — verified, no drift».

§7.22 — Routing audit
  Проверить: все 13 handoff-screens и 30 design-from-tokens screens
  смонтированы в App.tsx на правильных роутах. Таблица расхождений
  README ↔ App.tsx — в плане §7.22. Добавить `/dev/icons` роут за
  `import.meta.env.DEV` guard (galley для design-ревью).

§7.23 — Lucide → rh-icon mapping
  Не трогаем, если migration уже прошла (мы не используем lucide-react
  во фронте). Проверить grep: `grep -r "from 'lucide-react'"
  web_portal/src/` — должно быть пусто. Если пусто — пропустить §7.23.

Правила работы:
- Каждый логический шаг — отдельный коммит с префиксом из §:
    chore(a11y): ...     (§7.18)
    chore(perf): ...     (§7.19)
    chore(storybook): ...(§7.20, optional)
    chore(contracts): ...(§7.21 verify)
    feat(web-portal): ...(§7.22 routing fixes)
    docs(design): ...    (§7.23 if needed)
- После КАЖДОГО коммита: `cd web_portal && npx tsc --noEmit` → exit 0.
- После group финиша (§7.18, §7.19): `docker compose up -d --build
  nginx api` + smoke-check в браузере на https://portal.rekharbor.ru/.
- Перед началом §7.18 сделать быструю проверку:
    grep -rn '<div[^>]*onClick' web_portal/src/screens/
  — это список div-кнопок, которые нужно превратить в <button>.
  Если список пустой — отлично, переходим сразу к focus-ring.

После завершения §7.18–§7.21 (minimum viable):
  1. Создать reports/docs-architect/discovery/
     CHANGES_<дата>_s47-phase7-a11y-perf.md.
  2. Обновить CHANGELOG.md [Unreleased] — добавить блок
     «S-47 Phase 7 — a11y + perf (YYYY-MM-DD)».
  3. Если §7.20 Storybook пропущен — явно зафиксировать в CHANGELOG
     как «deferred, not blocking».
  4. Предложить user'у запускать Phase 8 (merge feat/s-47-ui-redesign-ds-v2
     → develop → main) с кратким отчётом об оставшихся рисках.

НЕ мёржить feat/s-47-ui-redesign-ds-v2 в develop без явного запроса
user'а. Визуальный review DS v2 должен пройти ДО merge.

Начни с быстрого аудита:
  1. git log --oneline -5 — убедиться, что ты на 007d8ac.
  2. grep -rn '<div[^>]*onClick' web_portal/src/screens/ web_portal/src/components/
  3. grep -rn "from 'lucide-react'" web_portal/src/ | head -5
  4. ls web_portal/node_modules/@storybook 2>/dev/null || echo
     "Storybook не установлен"
  5. Доложить находки одним абзацем и предложить порядок работы.
```

---

## Контекст (для админа, не копировать)

- Ветка на момент написания промта: `feat/s-47-ui-redesign-ds-v2` @ `007d8ac`
- Последние 7 коммитов — Phase 6 (6.1–6.6 + fix + docs).
- `tsc --noEmit` clean, `docker compose up -d --build nginx api` работает.
- Предупреждение: в `reports/design/test-avatars-handoff-2026-04-20/` лежит
  handoff-бандл, он под git — не удалять.
- `project_fastapi_route_ordering.md` memory запомнен — динамические
  `/{int_id}` роуты идут ПОСЛЕ статических путей.
- §7.21 всё ещё заявлен в плане, но endpoint'ы были реализованы в Phase 3
  (коммит `0527d02` + `7fc050a`). В следующей сессии стоит только
  верифицировать, не переделывать.
