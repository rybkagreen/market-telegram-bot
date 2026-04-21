# Next-session prompt — post-S-48, ready for Stage 4/5/6/7

**Generated:** 2026-04-19 (end of S-48 session)
**Use:** paste the body below into a fresh Claude Code session.

---

Продолжаем работу по `/opt/market-telegram-bot/reports/20260419_diagnostics/`.

## Актуальное состояние (после сессии 2026-04-19, S-48 hotfix)

- `main` = **70c2466** `chore(main): merge develop — S-48 prod smoke blockers hotfix (A1/D1/F1/A7)`
- `develop` = **b6fee1f** `chore(develop): merge fix/s-48-prod-smoke-blockers — prod hotfix (A1/D1/F1/A7 + drift)`
- `fix/s-48-prod-smoke-blockers` = **c05ec4d** (оставлена, не удаляем)
- `feat/s-44-missing-integration` = e5e17e0 (сохранена)
- `feat/s-42`, `feat/s-43` — ранее сохранены, не удалять
- `Test Avatars-handoff.zip` — до сих пор в корне как untracked (ждёт Stage 7)

### Что сделано в S-48 (reports/docs-architect/discovery/CHANGES_2026-04-19_s48-prod-smoke-blockers.md)

P0 блокеры закрыты:
- **A1**: переставил `/{channel_id}*` в конец `channels.py` → `/available`, `/stats`, `/preview` больше не ловят 422 int_parsing. Подтверждено: `GET /api/channels/available` теперь 401 (auth), не 422.
- **F1**: `selectinload(advertiser, owner)` в `DisputeRepository.get_all_paginated` + `Query(alias="status")` на админ-роуте → 500 исчез (теперь 401 до auth). Подтверждено курлом изнутри контейнера.
- **D1**: рендер уже был правильный (S-43 §2.5); добавил плашку `📇 Паспорт добавлен` в `LegalProfileView`. Прод-бандл был stale — rebuild nginx выполнен.

P1/P2 закрыто:
- **E1**: AdminPayouts уже был в source (366aafe + bcb56f6), 404 был от stale bundle. Rebuild сделан.
- **A7**: новый screen `ReputationHistory.tsx` на `/profile/reputation` + ссылка из Cabinet.
- **S-43 drift**: `owner_comment` → `owner_explanation` на read-side в 3 файлах (types.ts, MyDisputes.tsx, DisputeDetail.tsx). PATCH body оставлен (backend DisputeUpdate по-прежнему принимает `owner_comment`).

### Не входило в S-48 и осталось не закрытым (из smoke-теста)

- **A2** (P2): `useMyPlacements` — `page_size` drift, в source уже чисто, это только stale bundle, больше не всплывёт после Vite rebuild.
- **A3** (P1): counter-offer wiring проверить нельзя без второго владельца-тестера. В бандле `advertiser_counter_price` был 0 — нужен smoke с реальной сделкой.
- **B1/B2** (P2): UI таблицы каналов (owner/channel detail) не показывает `last_er`/`avg_views`, хотя API их отдаёт.
- **C1** (P2): `GET /api/contracts/me` → 422 (фронт шлёт `/me`, бэк парсит как `{contract_id}`). **Тот же класс бага, что A1 в S-48** — нужна такая же перестановка в `src/api/routers/contracts.py`. Fallback на `/api/contracts/` работает, но 422 шумит в сети.
- **F1 user side** (P2): роут `/disputes` не смонтирован (чанк `MyDisputes-DtTAt3bn.js` есть в билде, но нет entry в App.tsx для текущего пользователя вне контекста `/adv/disputes` / `/own/disputes`).

## План на эту сессию — выбери ОДИН этап

Полный индекс: `reports/20260419_diagnostics/FIX_PLAN_00_index.md`. Готовые: 1, 2, 3, S-48. Осталось:

### Вариант A — Этап 4 «Backend cleanup» (P1, 4–6 ч, ветка `chore/s-45-backend-cleanup`)

`FIX_PLAN_04_backend_cleanup.md`. Самое скучное и самое безопасное. Удаляем:
1. 6 legacy placement POST endpoints (accept/reject/counter/accept-counter/counter-reply/pay) — заменены unified PATCH ещё в S-35. **КРИТИЧНО** — перед удалением grep'нуть `mini_app/src/` и `src/bot/handlers/`: если ссылки есть, оставляем.
2. `DELETE /api/placements/{id}` если совпадает по функциональности с `PATCH action=cancel`.
3. Дохлая `rating` очередь в worker_background (исторический артефакт v4.3).
4. `celery_config.py` — был удалён в S-36, проверить что ссылок не осталось.
5. Потенциально — `get_by_user` в DisputeRepository, если никто не использует (только `get_by_user_paginated`).

Плюсы: быстро, низкий риск. Минусы: не даёт visible value.

### Вариант B — Этап 5 «Arch debt» (P2, 12–16 ч, ветка `refactor/s-46-api-module-consolidation`)

`FIX_PLAN_05_arch_debt.md`. Рефакторинг 22 прямых `api.*`-вызовов в screens/components/hooks на унифицированную `screen → hook → api-module`. Конкретные цели:
- AdminUserDetail (balance top-up)
- AdminFeedbackDetail (3 вызова)
- AdminAccounting (KUDiR download — уже частично поправлен в S-44)
- DisputeResponse, OpenDispute, CampaignCounterOffer (прямые `api.patch` в handlers)

Добавить `no-restricted-imports` ESLint-правило, запрещающее `@shared/api/client` из `screens/**` и `components/**`. Это даст guard на уровне CI.

Плюсы: **зависимость для Stage 7** (редизайн будет чище если архитектура унифицирована). Минусы: много рутинного кода, риск сломать mutations.

### Вариант C — Этап 6 «Tests and guards» (P2, 6–8 ч, ветка `test/s-47-contract-guards`)

`FIX_PLAN_06_tests_and_guards.md`. Contract-drift checker: экспорт OpenAPI из FastAPI + `openapi-typescript` → сравнение с ручными типами. Это единственная защита от повторения S-43 drift.

Вариант A (robust, долго) — переход на `api-generated.ts` из openapi-typescript.
Вариант B (быстрый, 1 час) — pytest snapshot `model_json_schema()` для 7 критичных схем (User, Placement, Payout, Contract, Dispute, LegalProfile, Channel).

Плюсы: навсегда убирает класс багов как D1/C1. Минусы: не чинит существующие проблемы.

### Вариант D — Этап 7 «UI redesign DS v2» (P1, 40–56 ч, ветка `feat/s-47-ui-redesign-ds-v2`) ⭐ **рекомендую**

`FIX_PLAN_07_ui_redesign_ds_v2.md`. Handoff-бандл уже лежит в корне. План расписан в 8 фазах (7.0–7.7). Стартовать с:
- **7.0** — вынести `Test Avatars-handoff.zip` в `reports/design/test-avatars-handoff-2026-04-19/` (распаковать, zip удалить, whitelist в .gitignore для `reports/design/**`).
- **7.1** — Design tokens v2 (OKLCH, accent-2, light-mode) в `web_portal/src/styles/globals.css` + обновить `DESIGN.md`.
- **7.2** — шрифты (Outfit/DM Sans/JetBrains Mono) + Icon-компонент из `handoff-icons.jsx` (≈50 линейных SVG 20×20 stroke 1.5, заменит весь lucide-react в screens/components).

Stage 7 — **самый большой и самый видимый impact**. Рекомендую его как Вариант D, но согласовать с пользователем, потому что 40–56 часов в одну сессию не влезет (нужно разбить на суб-сессии 7.0–7.2, 7.3–7.5, 7.6–7.7).

## Ключевые напоминалки (перечитать перед началом)

- **После backend/frontend правок:** `docker compose up -d --build nginx api` — обязательно `--build`, иначе Vite не пересоберёт `dist/` внутри nginx-образа.
- **Lint/Typecheck:**
  - Backend: `/root/.vscode-server/extensions/charliermarsh.ruff-2026.40.0-linux-x64/bundled/libs/bin/ruff check src/`
    (ruff в api-контейнере не установлен; `poetry` в корне не работает)
  - Frontend: `cd /opt/market-telegram-bot/web_portal && npx tsc --noEmit -p tsconfig.app.json`
- **Semantic commits per-группа:** `fix(api)`, `feat(web_portal)`, `docs(sXX)`, etc. Никогда `git add .`.
- **Git flow из CLAUDE.md:** feature → develop (`--no-ff`) → main (`--no-ff`), ветку сохранять, на конфликте merge — STOP + report.
- **Memory уже содержит** (`/root/.claude/projects/-opt-market-telegram-bot/memory/MEMORY.md`):
  - `project_fastapi_route_ordering.md` — правило «static paths before `/{int_id}`» (S-48 A1)
  - `project_s39a_schema_gaps.md` — аудит схем S-39a
  - `feedback_deploy.md` — правило `docker compose up -d --build`
- **NEVER TOUCH:** `src/core/security/field_encryption.py`, `src/api/middleware/audit_middleware.py`, `src/api/middleware/log_sanitizer.py`, `src/db/models/audit_log.py`, `src/db/models/legal_profile.py`, `src/db/models/contract.py`, `src/db/models/ord_registration.py`, `src/db/migrations/versions/*` (read-only).
- **Рекомендация перед стартом** — прогнать прод-smoke рекурсивно (те же запросы, что в `SMOKE_TEST_2026-04-19_portal-prod.md`), чтобы убедиться что S-48 hotfix реально работает в prod. Если что-то не закрылось — сначала добиваем S-48 fix-pack, потом идём дальше.

## Стартовая команда

```bash
# Для варианта A (Stage 4):
git checkout main && git pull origin main && git checkout -b chore/s-45-backend-cleanup

# Для варианта B (Stage 5):
git checkout main && git pull origin main && git checkout -b refactor/s-46-api-module-consolidation

# Для варианта C (Stage 6):
git checkout main && git pull origin main && git checkout -b test/s-47-contract-guards

# Для варианта D (Stage 7) — рекомендую:
git checkout main && git pull origin main && git checkout -b feat/s-47-ui-redesign-ds-v2
```

Спроси пользователя какой вариант. По умолчанию — D (UI redesign, handoff-бандл уже ждёт).
