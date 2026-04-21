# Next-session prompt — post-S-45, ready for Stage 5/6/7

**Generated:** 2026-04-20 (end of S-45 session)
**Use:** paste the body below into a fresh Claude Code session.

---

Продолжаем работу по `/opt/market-telegram-bot/reports/20260419_diagnostics/`.

## Актуальное состояние (после сессии 2026-04-20, S-45 backend cleanup)

- `main` = **b914a32** `chore(main): merge develop — S-45 backend cleanup + LSP setup`
- `develop` = **efc814d** `chore(develop): merge chore/s-45-backend-cleanup — S-45 backend cleanup`
- `chore/s-45-backend-cleanup` = **6c926ad** (на origin, сохранена, не удаляем)
- `fix/s-48-prod-smoke-blockers` = **c05ec4d** (сохранена)
- `feat/s-44-missing-integration` = **e5e17e0** (сохранена)
- `feat/s-42`, `feat/s-43` — ранее сохранены, не удалять
- `Test Avatars-handoff.zip` — до сих пор в корне как untracked (ждёт Stage 7)
- `NEXT_SESSION_PROMPT_2026-04-20_v2.md` (от post-S48 сессии) — untracked, можно удалить после перехода на этот файл

### Что сделано в S-45 (reports/docs-architect/discovery/CHANGES_2026-04-20_s45-backend-cleanup.md)

**Backend cleanup (−271/+3):**
- Удалены 6 legacy placement POST + DELETE endpoints (`/accept`, `/reject`, `/counter`, `/accept-counter`, `/pay`, `DELETE /{id}`) — заменены unified PATCH ещё в S-35. Frontend везде уже использует PATCH, callers в `mini_app/`, `web_portal/`, `src/bot/handlers/` не найдено.
- Вместе с ними вычищены `RejectRequest`, `CounterOfferRequest`, `field_validator` import, `NOT_CHANNEL_OWNER`, `NOT_PLACEMENT_ADVERTISER` — всё использовалось только удалёнными хендлерами.
- `DisputeRepository.get_by_user` — удалён (все вызовы идут через `get_by_user_paginated`).
- Мёртвый `rating` queue listener удалён из `worker_background` в `docker-compose.yml` (`-Q parser,cleanup,rating,background` → `-Q parser,cleanup,background`). `rating_tasks.py` удалён в v4.3, `task_routes` не содержит правил для `rating`.
- `celery_config.py` — уже был чист (удалён в S-36), никаких действий не требовалось.

**Прицепом поехал `c4355ce` (LSP setup):**
- `pyrightconfig.json` (Python 3.14, `.venv`, include=src/tests/scripts/conftest.py)
- Секция `## LSP — Code Navigation` в `CLAUDE.md` (operations, usage policy, fallback signals)
- `CHANGES_2026-04-19_lsp-setup.md`
Это авто-коммит хука из предыдущей сессии — «висел» в рабочем дереве непокоммиченным, хук сгрёб и закоммитил перед S-45 flow. Cкрипт `git log --graph` показывает чисто.

**Смерджено `--no-ff`:** feature → develop → main, всё запушено в origin. Ветки не удалены.

### Ruff snapshot
- 0 ошибок в touched-файлах S-45
- 11 pre-existing ошибок в unrelated файлах (`document_validation.py`, `channel_owner.py`), **без регрессии** относительно pre-S-45 состояния (stash+recheck показал идентичные счётчики)

### Что осталось не закрытым из S-48 smoke-теста (напоминание)

- **A2** (P2): `useMyPlacements` page_size — в source чисто, только stale bundle.
- **A3** (P1): counter-offer wiring — требуется второй владелец-тестер для smoke.
- **B1/B2** (P2): UI таблицы каналов (owner/channel detail) не показывает `last_er`/`avg_views`, API их отдаёт.
- **C1** (P2): `GET /api/contracts/me` → 422 (фронт шлёт `/me`, бэк парсит как `{contract_id}`). **Тот же класс бага, что A1 в S-48** — нужна перестановка в `src/api/routers/contracts.py` (`/me` ДО `/{contract_id}`). Fallback на `/api/contracts/` работает.
- **F1 user side** (P2): роут `/disputes` не смонтирован в `App.tsx` (чанк `MyDisputes-DtTAt3bn.js` собран, но entry нет вне контекста `/adv/disputes` / `/own/disputes`).

Эти пункты можно прихватить попутно в любом из следующих stage'ей — все они — «один в один» с тем, что уже сделали.

## План на эту сессию — выбери ОДИН этап

Полный индекс: `reports/20260419_diagnostics/FIX_PLAN_00_index.md`. Готовы: 1, 2, 3, S-48, **S-45 (Stage 4)**. Осталось:

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

- **Вариант C.1 (robust, долго)** — переход на `api-generated.ts` из openapi-typescript.
- **Вариант C.2 (быстрый, 1 час)** — pytest snapshot `model_json_schema()` для 7 критичных схем (User, Placement, Payout, Contract, Dispute, LegalProfile, Channel).

Плюсы: навсегда убирает класс багов как D1/C1. Минусы: не чинит существующие проблемы.

### Вариант D — Этап 7 «UI redesign DS v2» (P1, 40–56 ч, ветка `feat/s-47-ui-redesign-ds-v2`) ⭐ **рекомендую**

`FIX_PLAN_07_ui_redesign_ds_v2.md`. Handoff-бандл (`Test Avatars-handoff.zip`) уже лежит в корне. План расписан в 8 фазах (7.0–7.7). Stage 7 — **самый большой и самый видимый impact**.

**Разбиение на суб-сессии (40–56 часов в одну не влезет):**

- **7.0–7.2** (6–10 ч) — фундамент:
  - **7.0** — вынести `Test Avatars-handoff.zip` в `reports/design/test-avatars-handoff-2026-04-19/` (распаковать, zip удалить, whitelist в `.gitignore` для `reports/design/**`).
  - **7.1** — Design tokens v2 (OKLCH, accent-2, light-mode) в `web_portal/src/styles/globals.css` + обновить `DESIGN.md`.
  - **7.2** — шрифты (Outfit/DM Sans/JetBrains Mono) + Icon-компонент из `handoff-icons.jsx` (≈50 линейных SVG 20×20 stroke 1.5, заменит весь lucide-react в screens/components).

- **7.3–7.5** (16–24 ч) — экраны:
  - **7.3** — кабинет + навигация под новые токены и Icon-компонент.
  - **7.4** — campaign/dispute flows под новую типографику и paddings.
  - **7.5** — админ-панель (AdminPayouts/AdminFeedback/AdminUserDetail) — совместимо с работой из Stage 5, если D идёт после B.
  - Попутно можно прихватить **A2** (бандл-только), **B1/B2** (last_er/avg_views в UI).

- **7.6–7.7** (10–14 ч) — polish + QA:
  - **7.6** — motion (`motion/react` — не `framer-motion`), микро-анимации.
  - **7.7** — dark-mode/light-mode параллель, accessibility pass, Tailwind `@theme`.

**Зависимость:** если хочется сделать чисто, сначала Stage 5 (B) — тогда Stage 7 не будет спотыкаться о прямые `api.*` вызовы в редизайняемых экранах. Если «и так нормально» — можно Stage 7 сразу.

## Ключевые напоминалки (перечитать перед началом)

- **После backend/frontend правок:** `docker compose up -d --build nginx api` — обязательно `--build`, иначе Vite не пересоберёт `dist/` внутри nginx-образа. Для S-45-style изменений `worker_background` — `docker compose up -d --build worker_background`.
- **Lint/Typecheck:**
  - Backend: `/root/.vscode-server/extensions/charliermarsh.ruff-2026.40.0-linux-x64/bundled/libs/bin/ruff check src/`
    (ruff в api-контейнере не установлен; `poetry` в корне не работает — используется pipx-установленный)
  - Frontend (web_portal): `cd /opt/market-telegram-bot/web_portal && npx tsc --noEmit -p tsconfig.app.json`
  - Frontend (mini_app): `cd /opt/market-telegram-bot/mini_app && npx tsc --noEmit`
  - Frontend (landing): `cd /opt/market-telegram-bot/landing && npx tsc --noEmit`
- **LSP доступен.** Перед `grep`-ом по символам — используй `LSP goToDefinition` / `findReferences` / `documentSymbol` / `workspaceSymbol`. Grep остаётся для текста/regex/не-кода.
- **Semantic commits per-группа:** `fix(api)`, `feat(web_portal)`, `docs(sXX)`, `chore(docker)`, `refactor(db)`, etc. Никогда `git add .`.
- **Git flow из CLAUDE.md:** feature → develop (`--no-ff`) → main (`--no-ff`), ветку сохранять, на конфликте merge — STOP + report.
- **Хук может авто-коммитить** «висячие» untracked docs между твоими коммитами (как случилось с `c4355ce` в S-45). Не пугаться — просто учитывать что scope merge расширится. Предупреди пользователя если поехал прицеп.
- **Memory содержит** (`/root/.claude/projects/-opt-market-telegram-bot/memory/MEMORY.md`):
  - `project_fastapi_route_ordering.md` — правило «static paths before `/{int_id}`» (S-48 A1, S-45 подтвердил на C1 ожидание — такой же паттерн)
  - `project_s39a_schema_gaps.md` — аудит схем S-39a
  - `feedback_deploy.md` — правило `docker compose up -d --build`
- **NEVER TOUCH:** `src/core/security/field_encryption.py`, `src/api/middleware/audit_middleware.py`, `src/api/middleware/log_sanitizer.py`, `src/db/models/audit_log.py`, `src/db/models/legal_profile.py`, `src/db/models/contract.py`, `src/db/models/ord_registration.py`, `src/db/migrations/versions/*` (read-only).
- **Рекомендация перед стартом** — прогнать прод-smoke рекурсивно (те же запросы, что в `SMOKE_TEST_2026-04-19_portal-prod.md`), чтобы убедиться что S-45 не задел boundary-кейсы (не должен был, но perекатная страховка).

## Стартовая команда

```bash
# Для варианта B (Stage 5 — arch debt):
git checkout main && git pull origin main && git checkout -b refactor/s-46-api-module-consolidation

# Для варианта C (Stage 6 — tests & guards):
git checkout main && git pull origin main && git checkout -b test/s-47-contract-guards

# Для варианта D (Stage 7 — UI redesign, рекомендую):
git checkout main && git pull origin main && git checkout -b feat/s-47-ui-redesign-ds-v2
```

Спроси пользователя какой вариант. По умолчанию — **D** (UI redesign, handoff-бандл уже ждёт). Если пользователь выбирает D — предложи начать с под-блока **7.0–7.2** (фундамент токенов и иконок), остальное — в следующих суб-сессиях.

---

🔍 Verified against: b914a32 | 📅 Updated: 2026-04-20T00:20:00+03:00
