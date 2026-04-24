# IMPLEMENTATION_PLAN_ACTIVE.md — Consolidated session plan (rev 3)

> **Одноразовый рабочий план.** После завершения ВСЕХ фаз (0 → 7) исполнитель
> удаляет этот файл (`git rm IMPLEMENTATION_PLAN_ACTIVE.md`) в финальном
> коммите в `main`. Файл НЕ попадает в релизный `main`.
>
> **Проект не в production.** Критерий — не "правильно", а "архитектурно
> элегантно". Backward compatibility НЕ требуется. Мёртвый код, dev-only
> ветки, hardcoded значения — удаляются.
>
> **Каждая фаза = отдельная сессия.** Между фазами — stop-point. Новая сессия
> открывается копированием соответствующего раздела "Phase N" целиком в prompt.
>
> **Каждая фаза начинается с deep-dive research** (параллельные Explore-агенты)
> ДО написания кода. Implementation стартует только после того, как research
> подтверждён: фактическое состояние кода может отличаться от диагностики на
> момент составления плана.
>
> **После каждой фазы:**
> `reports/docs-architect/discovery/CHANGES_<YYYY-MM-DD>_<slug>.md` +
> `CHANGELOG.md [Unreleased]` + Conventional Commits + push в `feature/*` →
> merge в `develop` --no-ff → **STOP, ждать явного "ок"** перед следующей.
>
> **Общие правила (копируются в каждую сессию):**
> - CLAUDE.md, MEMORY.md, `src/config/settings.py` — обязательно перечитать.
> - **Research-фазы обязаны иметь секцию "Возражения и риски" перед "Вопросами
>   для подтверждения".** Если в плане замечены security-холы, противоречия,
>   упущенные граничные случаи или неудачные именования — поднимать явно, не
>   маскировать под уточняющие вопросы. Спорить с планом, когда есть основания.
> - **Phase-mode дисциплина:**
>   - Research / planning (0.A, N.A): «Будь критичным, ищи проблемы,
>     оспаривай решения с аргументацией.»
>   - Implementation (0.B–0.C, N.B–N.C): «Реализуй план как написано. Если
>     вылезла блокирующая проблема — останавливайся и сообщай. Не вноси
>     не предусмотренные планом улучшения.»
> - **Что поднимать явно vs что отложить:**
>   - **Поднимать (block / interrupt):** (а) проблемы безопасности,
>     (б) баги или потенциальные баги, (в) явные противоречия в плане
>     или требованиях, (г) решения, заметно усложняющие будущую поддержку.
>   - **Отложить одной строкой в конце отчёта** под заголовком
>     «возможные дальнейшие улучшения, не требуют действий сейчас»:
>     косметические рефакторы, стилистические придирки, test coverage
>     gaps в нетронутом коде, perf-оптимизации без замеров, naming
>     preferences без семантического mismatch.
> - S-48 transaction contract (сервис не открывает/не закрывает транзакции).
> - API convention: screen → hook → api-module (ESLint + grep-guard).
> - Pre-production migration rule: правим `0001_initial_schema.py`, новые
>   Alembic revisions НЕ создаём.
> - Git flow: feature/* → develop → main, --no-ff всегда, НИКОГДА `--no-verify`.
> - Хардкоды запрещены везде: значения в `settings.py` (env) или
>   `src/core/constants.py` (compile-time).
> - Mocks для runtime/test переиспользуют existing `tests/` infrastructure
>   (factories, fixtures, conftest). Новых директорий `src/mocks/` НЕ создаём.
> - Explicit transition function для `placement.status` — прямое присваивание
>   запрещено линтером (см. Phase 2).
> - ПД никогда не показываются и не принимаются через mini_app.
> - После изменений в `src/` или `mini_app/src/` — обязательный rebuild:
>   `docker compose up -d --build nginx api`.

---

## 0. Цель и мотивация

Подготовить проект к production-запуску так, чтобы исключить юридические и
финансовые риски (ФЗ-152, ФЗ-115, ФЗ-38, ГК РФ ст.432, НК РФ, УК ст.159 при
систематике). Механизм — **система блокирующих юр. gate'ов** на переходах
PlacementRequest, с идентичным flow в production и test-mode (runtime admin
override через моки для каждого gate-failure).

## 1. Архитектурные принципы плана (обязательны)

1. **Zero hardcoded values** — URLs, префиксы, TTL, timeouts, limits,
   magic numbers → `settings.py` (env) или `src/core/constants.py`.
   CI-guard в `scripts/check_forbidden_patterns.sh` расширяется правилом.
2. **Zero dev/prod divergence** — `ENVIRONMENT` переменная либо удаляется,
   либо формализуется в явные feature-flags. Разное поведение dev/prod
   недопустимо (тесты перестают отражать реальность).
3. **Mocks = test infrastructure** — `tests/factories/`, `tests/fixtures/`,
   `conftest.py`. Runtime admin mock-override в Phase 5 подтягивает
   сценарии из той же инфраструктуры. Новых `src/mocks/` директорий
   НЕ создавать.
4. **Explicit transition function** — `PlacementTransitionService.transition()`
   единственная точка смены `placement.status`. Линтер запрещает прямое
   присваивание. Sync путь, никаких SQLAlchemy event-hook'ов.
5. **Legal Compliance Gates first-class** — 18 gate'ов (Phase 3), enum
   `PlacementGate`, единый сервис `LegalComplianceService.check_gates()`.
   Каждый status-переход прогоняется через relevant gates.
6. **ФЗ-152 абсолютно** — ПД (паспорт, ИНН, реквизиты, сканы) в mini_app
   НЕ отображаются и НЕ принимаются. Backend отклоняет с 403 любой запрос
   с `aud != web_portal`.
7. **Test-mode = runtime, admin-only** —
   - Test-каналы невидимы non-admin (фильтр в репозитории).
   - Галочка "тестовая кампания" видна только admin.
   - При включении галочки channel-selector отдаёт только test-каналы.
   - Closed-loop: `placement.is_test == channel.is_test == owner.is_test`.
   - Flow идентичен production (все gate'ы применяются).
   - На каждом failed gate admin получает диалог:
     **"Выполнить реально"** (retry external call) **/** **"Подтянуть mock"**
     (fixture из tests/). Non-admin mock недоступен — только reality.

## 2. Findings (consolidated, 2026-04-25)

| # | Проблема | Критичность | Фаза |
|---|----------|-------------|------|
| 1 | Contracts/Acts в mini_app — экраны есть, навигации в меню нет | High UX | 6 |
| 2 | mini_app рендерит документы с ПД (contract/act detail) | 🔴 ФЗ-152 | 1, 6 |
| 3 | `/api/legal-profile/*` принимает любой JWT (нет `aud`) | 🔴 ФЗ-152 | 0, 1 |
| 4 | Нет `placement_status_history` и `PlacementTransitionService` | High | 2 |
| 5 | `ord_block_publication_without_erid=False` by default | 🔴 ФЗ-38 | 6 |
| 6 | UI не рендерит `scheduled_delete_at` в части экранов | Medium | 7 |
| 7 | `is_test` режет бизнес-логику вместо переключения провайдеров | High | 5 |
| 8 | **Нет единой системы юр. gate'ов на переходах** | 🔴 ФЗ-115/НК/ГК | 3 |
| 9 | Нет supplementary agreement (ДС) на размещение | 🔴 ГК 432 | 4 |
| 10 | `legal_type` compliance (ФЛ/самозанятый/ИП/ООО) не покрыто системно | 🔴 НК | 3 |
| 11 | `ENVIRONMENT` — dead variable | Hygiene | 0 |
| 12 | Hardcoded URLs, ERID-префиксы, magic numbers | Hygiene | 0 |

## 3. NEVER TOUCH — требуется явное "ок"

CLAUDE.md запрещает правку без спроса:
`field_encryption.py`, `audit_middleware.py`, `log_sanitizer.py`,
`audit_log.py`, `legal_profile.py`, `contract.py`, `ord_registration.py`.

План требует:

| Файл | Фаза | Что | Риск |
|------|------|-----|------|
| `contract.py` | 4 | Добавить `supplementary_agreement` в `ContractType`; FK `parent_contract_id` | Low (additive) |
| `legal_profile.py` | 3 | Возможно добавить `fns_verification_status`, `fns_verified_at`, `egrul_snapshot_at` (если отсутствуют) | Low (additive) |
| `0001_initial_schema.py` | 2, 3, 4, 5 | Новые таблицы/колонки | Ok per CLAUDE.md pre-prod rule |
| `audit_middleware.py` | — | **НЕ трогаем**. Новый `aud_audit_middleware.py` рядом | Zero |

Перед Phase 3 и Phase 4 — исполнитель СТОП и спрашивает явное "ок" на
`contract.py` / `legal_profile.py` edit.

## 3.bis. Cross-cutting concerns (применимы к КАЖДОЙ фазе)

Каждая фаза, затрагивающая публичный API / модель / UI, обязана закрыть
**все** слои ниже. Чеклист копируется в acceptance каждой фазы с
конкретными именами.

### Слой 1 — Repository layer
CLAUDE.md: *"All DB queries go here"*. Inline queries в сервисе запрещены.
- Новая таблица → новый `src/db/repositories/<name>_repo.py`.
- Изменение модели → обновить relevant repo методы (+ тесты).
- Gate-checkers (Phase 3) читают через existing repos, не напрямую
  через `session.execute(select(...))`.

### Слой 2 — Frontend hooks (`screen → hook → api-module`)
Правило S-46 / S-48, enforced ESLint + grep-guard.
- API-функция: `web_portal/src/api/<domain>.ts` и/или
  `mini_app/src/api/<domain>.ts` (единственное место с fetch/ky).
- Hook: `web_portal/src/hooks/use<Name>.ts` и/или `mini_app/src/hooks/`.
  React Query или mutation. Screen импортирует только hook.
- Запрет прямого `import { api }` в screens/components/hooks из `api`.

### Слой 3 — Client-side types
- Pydantic schema → Python side: `src/api/schemas/*.py` + snapshot в
  `tests/unit/snapshots/` + `tests/unit/test_contract_schemas.py`.
- TypeScript side: `web_portal/src/lib/types.ts` и
  `mini_app/src/lib/types.ts` — ручная синхронизация (auto-gen вне scope).
- Каждая новая Pydantic-схема → regenerate snapshot:
  `UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py`
  → коммитить рядом со схемой.

### Слой 4 — Database indices
- JSONB поля с admin-query — GIN-индекс.
- Composite `(col_a, col_b)` для часто используемых `WHERE a = ? ORDER BY b`.
- Partial index для sparse (`WHERE deleted_at IS NULL`, `WHERE is_test = True`).
- Миграции → `0001_initial_schema.py` (pre-prod rule).

### Слой 5 — Frontend tests
- Playwright специ в `web_portal/tests/specs/`.
- Viewport'ы: **iPhone SE**, **Pixel 5**, **Desktop Chrome 1440x900**
  (конвенция проекта из `playwright.config.ts`).
- Новый flow → spec. Новый экран → axe-violations check.

### Слой 6 — Mini_app audit (после каждой фазы)
На каждой фазе ответить:
1. Затрагивает ли фаза mini_app? Если нет — OK, идём дальше.
2. Если да — какая именно часть (UI / data / navigation)?
3. ПД проходят через mini_app? Если да — **СТОП**, переделываем по правилу
   "mini_app never touches ПД".
4. Timeline в mini_app — реализуется в Phase 7 как **read-only компактный**
   компонент `PlacementTimelineCompact.tsx` (только статусы + schedule,
   без gates, без financial details, без legal_type info).

## 4. Граф фаз

```
Phase 0 (env + constants + JWT aud)
   │
   ├──► Phase 1 (ФЗ-152 guards + mini_app legal strip)
   │
   ├──► Phase 2 (PlacementTransitionService + status_history)
   │         │
   │         ├──► Phase 3 (Legal Compliance Gates — 18 gates)
   │         │         │
   │         │         ├──► Phase 4 (Supplementary Agreements / ДС)
   │         │         │         │
   │         │         │         └──► Phase 5 (Test-mode runtime + admin UI)
   │         │         │                   │
   │         │         │                   └──► Phase 6 (Contracts/Acts UX + ORD prod)
   │         │         │                             │
   │         │         │                             └──► Phase 7 (UI Timeline + overlay)
```

Каждая стрелка — stop-point, требующее явное "ок".

---

# Phase 0 — Environment + constants + JWT `aud` (3-4ч)

**Branch:** `feature/env-constants-jwt-aud`

## 0.A Deep-dive research (прежде чем писать код)

Запустить **параллельно 3 Explore-агента** с точечными задачами:

### Agent A — ENVIRONMENT usage audit
> Найти все использования `settings.environment`, `ENVIRONMENT`, `ENV=`,
> `os.environ.get("ENVIRONMENT")` в `src/`, `tests/`, `mini_app/`, `web_portal/`,
> `docker-compose*.yml`, `.env*`. По каждой точке определить: меняет ли
> поведение (feature-flag, if/else, log level), или dead code. Вернуть
> таблицу `file:line | context | behaviour-changing? (y/n) | dead-code?`.

### Agent B — Hardcoded values inventory
> Найти захардкоженные URL (`portal.rekharbor`, `app.rekharbor`,
> `api.rekharbor`, `landing.rekharbor`), префиксы (`STUB-ERID`, `TEST-ERID`,
> `ERID-`), magic TTL/timeouts/limits в `src/`, `mini_app/src/`,
> `web_portal/src/`. Исключить `.md`, тестовые snapshot'ы, comment'ы. Вернуть
> путь:линия + что именно.

### Agent C — JWT auth infrastructure
> Прочитать `src/api/auth_utils.py`, `src/api/routers/auth.py`,
> `src/api/dependencies.py`. Вернуть: (1) структуру JWT payload (все поля),
> (2) где создаётся токен (endpoints), (3) какие dependencies проверяют
> токен, (4) есть ли уже `aud`-claim или источник, (5) где бы оптимально
> вставить `aud` без ломания legacy-токенов.

**Stop after research** — свести findings в короткий отчёт (< 400 строк
в чате), согласовать с пользователем что менять, только потом кодить.

## 0.A.bis Research findings (зафиксированы 2026-04-25)

Research уже выполнен в первой сессии. Ключевые факты, на которых стоит
последующая реализация:

- **ENVIRONMENT**: единственная behaviour-changing точка —
  `src/api/main.py:193` (mount `auth_e2e_router` при `environment=="testing"`).
  Параллельный dead-code `src/config/__init__.py` (никем не импортируется).
  Properties `is_development/is_production/is_testing` не используются.
- **Hardcoded URLs**: 8 backend-сайтов на `rekharbor.ru/app.rekharbor.ru` +
  5 Jinja-templates (deferred to Phase 6) + 3 frontend-точки.
  Typo-баг: `src/constants/legal.py:53,83,107,108` содержат
  `rekhaborbot.ru` (лишнее `bot`) — фикс обязателен.
- **ERID-prefix**: единственный — `STUB-ERID-` в `stub_ord_provider.py:43`
  и в `tests/integration/test_placement_ord_contract_integration.py:127`.
  Никакого `TEST-ERID-` в коде нет.
- **JWT**: payload = `{sub, tg, plan, exp, iat}`. Никакого `aud`. Никакой
  audience-валидации в `decode_jwt_token`. Endpoints выпускающие JWT — 4
  (`/auth/telegram`, `/auth/telegram-login-widget`, `/auth/login-code`,
  `/auth/e2e-login`). Redis уже подключён к auth-пути через
  `src/api/dependencies.py:141` (`get_redis()`).
- **VITE_PORTAL_URL**: НЕ задан ни в одном `.env`, `.env.example`, CI или
  Dockerfile. То есть fallback `'https://rekharbor.ru/portal'` в
  `mini_app/src/screens/common/LegalProfile{Setup,Prompt}.tsx:8` — это
  фактический prod URL. Чинить.

## 0.B Implementation (revised после security-review)

### 0.B.1 ENVIRONMENT consolidation
- Удалить `src/config/__init__.py` целиком (dead code, нет импортов).
- В `src/config/settings.py`: удалить `environment` field, properties
  `is_development/is_production/is_testing`.
- Заменить `if settings.environment == "testing"` на `if settings.enable_e2e_auth`
  в `src/api/main.py:193`.
- Добавить в `settings.py`: `enable_e2e_auth: bool = Field(False, alias="ENABLE_E2E_AUTH")`.
- В `.env.test` и `.env.test.example`: `ENABLE_E2E_AUTH=true`.
- Удалить `ENVIRONMENT=` из `.env`, `.env.example`, `.env.test`, `.env.test.example`.
- В `/health` response (`src/api/main.py:260`): убрать ключ `environment`.
- Docstring `src/api/routers/auth_e2e.py:4` — переписать под новый флаг.

### 0.B.2 Hardcode hygiene
- Новый `src/constants/erid.py` (внутри существующего `src/constants/`
  пакета — НЕ создавать `src/core/constants.py`):
  - `ERID_STUB_PREFIX = "STUB-ERID-"` — оставляем «STUB», описывает
    *тип провайдера* (синтетический). «TEST» был бы про *режим placement-а*
    (это отдельный концепт для Phase 5). НЕ переименовывать.
- `src/config/settings.py` — добавить:
  - `web_portal_url: AnyHttpUrl = Field("https://rekharbor.ru/portal", alias="WEB_PORTAL_URL")`
  - `mini_app_url: AnyHttpUrl = Field("https://app.rekharbor.ru/", alias="MINI_APP_URL")`
  - `landing_url: AnyHttpUrl = Field("https://rekharbor.ru", alias="LANDING_URL")`
  - `api_public_url: AnyHttpUrl = Field("https://api.rekharbor.ru", alias="API_PUBLIC_URL")`
  - `tracking_base_url: AnyHttpUrl = Field("https://rekharbor.ru/t", alias="TRACKING_BASE_URL")`
  - `terms_url: AnyHttpUrl = Field("https://rekharbor.ru/terms", alias="TERMS_URL")`
  - `ticket_jwt_ttl_seconds: int = Field(300, alias="TICKET_JWT_TTL_SECONDS")`
  - `sandbox_telegram_channel_id: int | None = Field(None, alias="SANDBOX_TELEGRAM_CHANNEL_ID")`
- Backend замены (8 файлов) — каждый хардкод `rekharbor.ru` URL заменить
  на `settings.<нужное_поле>`:
  - `src/api/main.py:175,176` — CORS origins
  - `src/bot/main.py:65` — `WebAppInfo(url=settings.mini_app_url)`
  - `src/bot/handlers/shared/legal_profile.py:16` — `PORTAL_URL = settings.web_portal_url`
  - `src/bot/handlers/shared/start.py:34` — terms link
  - `src/bot/handlers/shared/login_code.py:26` — instructional message
  - `src/core/services/publication_service.py:126` — tracking URL
  - `src/core/services/link_tracking_service.py:137,170` — tracking URL
- Typo fix: `src/constants/legal.py:53,83,107,108` →
  `rekhaborbot.ru` → `rekharbor.ru` (4 замены).
- Frontend (no fallbacks):
  - `mini_app/src/screens/common/LegalProfileSetup.tsx:8` и
    `LegalProfilePrompt.tsx:8` — убрать `|| 'https://rekharbor.ru/portal'`.
    Использовать `import.meta.env.VITE_PORTAL_URL` напрямую.
  - `mini_app/.env.example` и `mini_app/.env`: добавить
    `VITE_PORTAL_URL=https://rekharbor.ru/portal`.
  - `nginx/Dockerfile` (или где собирается mini_app): пробросить
    `ARG VITE_PORTAL_URL` + `ENV VITE_PORTAL_URL=$VITE_PORTAL_URL` перед
    `vite build`. Если уже есть paттерн для `VITE_API_URL` — копировать.
- Jinja templates (`src/templates/contracts/*.html`) — НЕ трогать в этой
  фазе. Перенос на render-time переменные — Phase 6.
- `scripts/check_forbidden_patterns.sh` — добавить:
  - Python check: pattern `https?://[a-z.\-]*rekharbor\.ru` в `src/`,
    исключения: `--exclude=settings.py`, `--exclude-dir=templates`.
  - TS check: тот же pattern в `mini_app/src/` и `web_portal/src/`,
    исключения: `--exclude-dir=lib`, `--exclude-dir=api`.

### 0.B.3 JWT `aud` claim — security-hardened

**`src/api/auth_utils.py`:**
- `create_jwt_token(user_id, telegram_id, plan, source: Literal["mini_app", "web_portal"]) -> str`
  — добавляем `"aud": source` в payload.
- `decode_jwt_token(token: str, audience: Literal["mini_app", "web_portal"] | None) -> dict`
  — `audience` без default value (обязательный позиционный аргумент).
  `None` оставляем как явный opt-out для `audit_middleware`-like helpers,
  но НЕ делаем default — кто пользует, обязан явно подумать.
- Legacy-токены без `aud`: в новых production-dependencies возвращают
  **401**, не WARN+accept. Pre-prod — окно миграции = одно перелогинивание
  юзера. Никаких "до конца TTL" компромиссов.

**Update token-issuing endpoints (4):**
- `src/api/routers/auth.py:90` — `source="mini_app"` (`/api/auth/telegram`).
- `src/api/routers/auth_login_widget.py:111` — `source="web_portal"`.
- `src/api/routers/auth_login_code.py:124` — `source="web_portal"`.
- `src/api/routers/auth_e2e.py:47` — `source="mini_app"` (test-only).

**`src/api/dependencies.py`:**
- `get_current_user` — теперь требует `aud in {"mini_app", "web_portal"}`.
  Tokens без aud → 401 InvalidToken.
- Новая `get_current_user_from_web_portal()` — обязательно передаёт
  `audience="web_portal"` в `decode_jwt_token`. Mini_app JWT → 403
  InvalidAudience. Никакого fallback.
- `get_current_admin_user` — без изменений (наследует от `get_current_user`).

**Bridge endpoints (`src/api/routers/auth.py`):**

`POST /api/auth/exchange-miniapp-to-portal`:
- Depends `get_current_user` (требует `aud="mini_app"`).
- Генерирует `jti = uuid4()`.
- Подписывает короткий ticket-JWT с `aud="web_portal"`, `jti`,
  `exp = now + settings.ticket_jwt_ttl_seconds`.
- Сохраняет в Redis: `auth:ticket:jti:{jti}` →
  JSON `{"user_id": int, "issued_at": "<ISO8601>", "ip": "<request.client.host>"}`.
  TTL = `settings.ticket_jwt_ttl_seconds`.
- Возвращает `TicketResponse {ticket: str, portal_url: AnyHttpUrl, expires_in: int}`.

`POST /api/auth/consume-ticket`:
- Без auth (но с защитой, см. ниже).
- **Rate-limit по IP**: 10 запросов / минута через Redis-counter
  `auth:ticket:rate:ip:{ip}` (INCR + EXPIRE 60). 11-й → 429.
- **Rate-limit по user_id**: 5 неудачных попыток / 5 минут через
  `auth:ticket:rate:user:{user_id}:fail` (INCR + EXPIRE 300). 6-й → 429
  + WARN-лог.
- Decode ticket с `audience="web_portal"`. На любой ошибке (expired,
  invalid signature, wrong aud, missing jti) — INCR fail-counter + 401
  + structured log: `event=ticket_consume_failed`, `reason=<...>`,
  `ip`, `jti_prefix=<first 8 chars of uuid>`.
- Verify `auth:ticket:jti:{jti}` exists в Redis. Нет → 401 (replay или
  Redis-flush).
- `redis.delete(...)` — one-shot.
- Issue full web_portal JWT: `create_jwt_token(..., source="web_portal")`.
- Возвращает `AuthTokenResponse {access_token: str, token_type: "bearer", source: Literal["web_portal"]}`.

**`audit_middleware.py` — НЕ трогаем в этой фазе:**
- Декодирует JWT без проверки подписи (читает `sub` для логов).
- Добавляем FIXME-комментарий с явной ссылкой на
  `reports/docs-architect/BACKLOG.md` запись (создать).
- Issue tracker entry: «refactor audit_middleware to read pre-validated
  payload from `request.state.user` instead of re-decoding».

**Pydantic schemas (`src/api/schemas/auth.py` — новый файл):**
- `class TicketResponse(BaseModel)`: `ticket: str`, `portal_url: AnyHttpUrl`, `expires_in: int`.
- `class AuthTokenResponse(BaseModel)`: `access_token: str`, `token_type: Literal["bearer"] = "bearer"`, `source: Literal["mini_app", "web_portal"]`.
- Snapshots в `tests/unit/snapshots/` — обе модели.
- `tests/unit/test_contract_schemas.py` — добавить обе.

## 0.C Acceptance

**Tests:**
- [ ] `tests/unit/api/test_jwt_aud_claim.py` (8 кейсов):
  1. mini_app JWT (`aud="mini_app"`) в `get_current_user` → 200.
  2. web_portal JWT (`aud="web_portal"`) в `get_current_user` → 200.
  3. legacy JWT без `aud` в `get_current_user` → **401** (НЕ WARN+200).
  4. mini_app JWT в `get_current_user_from_web_portal` → 403 InvalidAudience.
  5. Full ticket flow: exchange → consume → web_portal token works → 200 на каждом шаге.
  6. Expired ticket consumed → 401.
  7. Replay: consume того же ticket дважды → 1-й 200, 2-й 401 (jti уже удалён).
  8. Tampered: ticket с правильным aud, но JTI отсутствует в Redis → 401.
- [ ] `tests/unit/api/test_jwt_rate_limit.py` (2 кейса):
  1. 11-й `/consume-ticket` запрос с одного IP за минуту → 429.
  2. 6 неудачных consume для одного user_id за 5 минут → 429.

**Static checks:**
- [ ] `grep -rn "settings.environment" src/` → 0 результатов.
- [ ] `grep -rn "rekhaborbot" src/` → 0 результатов.
- [ ] `grep -rn "rekharbor.ru" src/ --include="*.py"` → только `settings.py` defaults
  (templates/ — отдельно, deferred to Phase 6).
- [ ] `scripts/check_forbidden_patterns.sh` → exit 0.
- [ ] `make lint`, `make test`, `make typecheck` → pass.

**Docs:**
- [ ] `reports/docs-architect/discovery/CHANGES_2026-04-25_phase0-env-constants-jwt.md`.
- [ ] `CHANGELOG.md` `[Unreleased]` — секции Added/Changed/Removed.
- [ ] `reports/docs-architect/BACKLOG.md` — запись про audit_middleware refactor.

### 0.D Cross-cutting checklist
- [ ] **Repo:** N/A (нет новых таблиц).
- [ ] **Hooks:** N/A (backend-only фаза).
- [ ] **Types (Python):** `TicketResponse`, `AuthTokenResponse` — +snapshot.
- [ ] **Types (TS):** обновить `mini_app/src/lib/types.ts` если есть `Auth*`-типы
  (Auth-flow в mini_app — Phase 1).
- [ ] **Indices:** N/A.
- [ ] **Frontend tests:** N/A (UI в Phase 1).
- [ ] **Mini_app audit:** `mini_app/src/api/client.ts` — глубокий аудит в Phase 1
  (storage ключа JWT, refresh-логика, обработка 401).

**STOP → ждать "ок" перед Phase 1.**

---

# Phase 1 — ФЗ-152 hardening + mini_app legal strip (2-3ч)

**Branch:** `feature/fz152-legal-hardening`

**Prerequisites:** Phase 0 merged в develop.

## 1.A Deep-dive research

Параллельно 2 агента:

### Agent A — Legal data endpoints on backend
> Прочитать `src/api/routers/legal_profile.py` (все endpoints) и
> `src/api/routers/documents.py` / `uploads.py` если есть. Вернуть: список
> URL/методов + какие поля ПД передаются + какие используют
> `get_current_user` (не защищены по source).

### Agent B — Mini_app legal screens audit
> Найти в `mini_app/src/` все упоминания: `legalProfile`, `DocumentUpload`,
> `passport_`, `ContractDetail`, `ActDetail`, `MyActsScreen`, `ContractList`.
> Вернуть: список файлов + какие из них показывают реквизиты/ПД + связанные
> API-клиенты.

## 1.B Implementation

### 1.B.1 Backend guard
- Все endpoints `/api/legal-profile/*` — заменить `Depends(get_current_user)`
  на `Depends(get_current_user_from_web_portal)`.
- Решение по legacy токенам (нет `aud`) — **отклонять 426 Upgrade Required**
  (pre-prod, юзеров мало, заставить re-login).
- Если найдутся `documents.py`/`uploads.py` с ПД — то же самое.

### 1.B.2 Mini_app legal strip
- **Удалить** из `mini_app/src/`:
  - `screens/common/LegalProfileSetup.tsx` (и связанные)
  - `screens/common/DocumentUpload.tsx` (если есть)
  - `screens/common/ContractDetail.tsx` (detail содержит реквизиты)
  - `screens/common/MyActsScreen.tsx` (detail содержит реквизиты)
  - `screens/common/ContractList.tsx` (оставить только badge — см. Phase 6)
  - `api/legalProfile.ts`, `api/contracts.ts`, `api/acts.ts`
- Удалить роуты `/legal-profile*`, `/documents*`, `/contracts*`, `/acts*`
  из `mini_app/src/App.tsx`.

### 1.B.3 Ticket-based redirect (инфраструктура для Phase 6)
- Новый компонент `mini_app/src/components/OpenInWebPortal.tsx`:
  - Вызывает `POST /api/auth/exchange-miniapp-to-portal`.
  - Получает `{ticket, portal_url}`.
  - Открывает `{portal_url}/login?ticket={ticket}&redirect=<target>` через
    `window.Telegram.WebApp.openLink(url)`.
- Web_portal:
  - `screens/auth/TicketLogin.tsx` — извлекает `?ticket=`, вызывает
    `POST /api/auth/consume-ticket`, сохраняет JWT, редиректит на `redirect=`.
- В `Cabinet.tsx` (mini_app) и menu-шах добавить **временную заглушку**
  "Юридический профиль → Открыть в портале" (компонент
  `OpenInWebPortal` с target=`/legal-profile`). Меню документов — в Phase 6.

### 1.B.4 `aud` audit
- **НЕ править** `audit_middleware.py`.
- Новый `src/api/middleware/aud_audit_middleware.py`:
  - На каждом запросе к `/api/legal-profile/*` логирует `aud` claim
    и user-id в отдельный structured log (`fz152.access`).
- Зарегистрировать в `src/api/main.py`.

## 1.C Acceptance

- [ ] `grep -r "legalProfile\|DocumentUpload\|passport_" mini_app/src/` → 0.
- [ ] `curl -X POST /api/legal-profile -H "Authorization: Bearer <miniapp_jwt>"`
  → 403.
- [ ] Legacy JWT без `aud` → 426.
- [ ] Ticket flow E2E (manual): mini_app → "Открыть в портале" → залогинен
  в web_portal → на нужном экране.
- [ ] Playwright: `legal-profile-requires-web-portal.spec.ts`.
- [ ] `make lint`, `make test`, `make typecheck` — pass.
- [ ] `CHANGES_<date>_phase1-fz152.md` + `CHANGELOG.md`.
- [ ] `docker compose up -d --build nginx api`.

### 1.D Cross-cutting checklist
- [ ] **Repo:** N/A (нет новых таблиц).
- [ ] **Hooks:**
  - mini_app: `useOpenInWebPortal(target: string)` — получает ticket, вызывает `Telegram.WebApp.openLink`.
  - web_portal: `useConsumeTicket(ticket: string)` — обменивает на JWT.
- [ ] **API modules:**
  - mini_app: `api/auth.ts` — `exchangeMiniappToPortal()`.
  - web_portal: `api/auth.ts` — `consumeTicket()`.
- [ ] **Types (Python):** `ExchangeTicketRequest`, `TicketResponse`, `ConsumeTicketRequest` + snapshot.
- [ ] **Types (TS):** обновить `web_portal/src/lib/types.ts`, удалить из `mini_app/src/lib/types.ts` типы `LegalProfile*`, `Passport*`, `Contract*`, `Act*`.
- [ ] **Indices:** N/A.
- [ ] **Frontend tests:**
  - Playwright `web_portal/tests/specs/legal-profile-requires-web-portal.spec.ts` — на 3 viewport'ах.
  - Playwright `web_portal/tests/specs/ticket-login.spec.ts` — обмен ticket → JWT.
- [ ] **Mini_app audit:** ПД удалены (UI + API + types) — grep подтверждает 0.

**STOP → ждать "ок" перед Phase 2.**

---

# Phase 2 — PlacementTransitionService + status_history (4-5ч)

**Branch:** `feature/placement-transition-service`

**Prerequisites:** Phase 1 merged.

## 2.A Deep-dive research

Параллельно 2 агента:

### Agent A — Status mutation audit
> Найти все точки изменения `placement.status` в `src/`:
> `grep -rn "placement\.status\s*=\|PlacementRequest.*status" src/`. Для
> каждой — назвать сервис/task/handler, кто actor, из какого статуса в
> какой, вызывается ли через ORM (`flush`) или bulk UPDATE
> (`session.execute(update())`). Вернуть таблицу
> `file:line | from → to | context | mutation_type`.

### Agent B — Related timestamp fields
> Прочитать `src/db/models/placement_request.py`. Перечислить все
> timestamp-колонки (created_at, published_at, scheduled_delete_at и т.д.)
> и их текущий смысл. Проверить присутствие связки "статус → timestamp-поле"
> (например published_at заполняется при переходе в `published`).

## 2.B Implementation

### 2.B.1 Модель `PlacementStatusHistory`
- Новый `src/db/models/placement_status_history.py`:
  ```python
  class PlacementStatusHistory(Base, TimestampMixin):
      __tablename__ = "placement_status_history"
      id: int (pk)
      placement_id: int (FK → placement_requests, on_delete=CASCADE)
      from_status: PlacementStatus | None
      to_status: PlacementStatus
      changed_at: datetime (default now)
      actor_user_id: int | None (FK → users)
      reason: TransitionReason (enum: user_action, admin_action,
                                system_event, celery_task, gate_retry,
                                admin_mock_override)
      metadata_json: dict | None (JSONB)
      __table_args__ = (Index("ix_psh_placement_changed",
                              "placement_id", "changed_at"),)
  ```
- `src/db/migrations/versions/0001_initial_schema.py` — добавить таблицу.

### 2.B.2 `PlacementTransitionService`
- Новый `src/core/services/placement_transition_service.py`:
  ```python
  class PlacementTransitionService:
      async def transition(
          session, placement, new_status, actor_user_id=None,
          reason=TransitionReason.system_event, metadata=None,
      ) -> None:
          old_status = placement.status
          if old_status == new_status:
              return
          placement.status = new_status
          # timestamp-поля: published_at при → published, и т.д.
          _sync_status_timestamps(placement, new_status)
          session.add(PlacementStatusHistory(
              placement_id=placement.id,
              from_status=old_status, to_status=new_status,
              actor_user_id=actor_user_id, reason=reason,
              metadata_json=metadata,
          ))
  ```
- Service НЕ открывает/не закрывает транзакцию (S-48 contract).

### 2.B.3 Рефакторинг всех точек из research Agent A
- Каждое прямое `placement.status = ...` — заменить на
  `await transition_service.transition(session, placement, new_status, ...)`.
- Bulk UPDATE (`session.execute(update())`) — заменить на loop + transition,
  либо на явный helper `bulk_transition()` с явным insert в history.

### 2.B.4 Линтер-правило
- Ruff custom rule либо `scripts/check_forbidden_patterns.sh`:
  запретить `placement.status = ` и `PlacementRequest\(.*status=` (присваивание)
  вне `placement_transition_service.py`.

### 2.B.5 Backend endpoint + schema
- `GET /api/placements/{id}/timeline` → `list[PlacementStatusHistoryResponse]`
  (access: advertiser-own / owner-of-channel / admin).
- `PlacementStatusHistoryResponse` в `src/api/schemas/placement.py`.
- Snapshot в `tests/unit/snapshots/` + `test_contract_schemas.py`.

## 2.C Acceptance

- [ ] Migration применяется чисто, `alembic check` → "No new upgrade ops".
- [ ] Linter ловит прямое присваивание `placement.status = ` (тест на ловлю).
- [ ] Integration: создать placement → transition → в history запись с
  правильным `actor_user_id`, `reason`, `metadata`.
- [ ] Integration: Celery task меняет статус → reason=`celery_task` +
  metadata={"task_name": ...}.
- [ ] GET timeline endpoint отдаёт правильный порядок.
- [ ] Snapshot для `PlacementStatusHistoryResponse` зафиксирован.
- [ ] `make lint`, `make test`, `make typecheck` — pass.
- [ ] `CHANGES_<date>_phase2-transition-service.md` + `CHANGELOG.md`.

### 2.D Cross-cutting checklist
- [ ] **Repo:** новый `src/db/repositories/placement_status_history_repo.py`:
  - `add(history: PlacementStatusHistory) -> None`
  - `list_by_placement(placement_id: int) -> list[PlacementStatusHistory]`
  - `list_recent_for_admin(limit: int, offset: int) -> list[PlacementStatusHistory]`
  - `count_by_reason(reason: TransitionReason) -> int`
- [ ] **Hooks:**
  - web_portal: `usePlacementTimeline(placementId: number)` — React Query (используется в Phase 7 UI, но вводим сейчас).
- [ ] **API modules:** `web_portal/src/api/placements.ts` — добавить `getPlacementTimeline(id)`.
- [ ] **Types (Python):** `PlacementStatusHistoryResponse`, `TransitionReason` (string enum) + snapshot в `test_contract_schemas.py`.
- [ ] **Types (TS):** `PlacementStatusHistoryResponse`, `TransitionReason` в `web_portal/src/lib/types.ts`. В `mini_app/src/lib/types.ts` — добавить только для Phase 7 компактного timeline.
- [ ] **Indices:**
  - Уже есть: `ix_psh_placement_changed (placement_id, changed_at)`.
  - Дополнительно: `ix_psh_actor_changed (actor_user_id, changed_at)` для admin-запросов.
- [ ] **Frontend tests:** N/A (UI в Phase 7).
- [ ] **Mini_app audit:** затрагивает? Нет — только endpoint. UI добавится в Phase 7.

**STOP → ждать "ок" перед Phase 3.**

---

# Phase 3 — Legal Compliance Gates (8-10ч, самая объёмная)

**Branch:** `feature/legal-compliance-gates`

**Prerequisites:** Phase 2 merged. **ЯВНОЕ "ок" на правку `legal_profile.py`**
(если research покажет что нужно добавить поля).

## 3.A Deep-dive research

Параллельно 3 агента:

### Agent A — legal_profile current structure
> Прочитать `src/db/models/legal_profile.py`, `src/api/routers/legal_profile.py`,
> `src/api/schemas/legal_profile.py`. Вернуть: (1) все текущие поля LegalProfile,
> (2) существующий enum legal_type и его значения (individual, self_employed,
> ie, llc?), (3) какие поля обязательны для каждого legal_type, (4) есть ли
> поля `fns_verification_status`, `egrul_snapshot_at`, `inn_validated_at`.

### Agent B — Existing gate-like checks scattered
> Найти точечные проверки legal-requirements в коде: `grep -rn
> "legal_profile\|framework_contract\|is_signed\|contract_signed" src/core/`.
> Вернуть: какие проверки уже есть (erid, framework contract signed и т.п.),
> где они вызываются, в какой момент flow.

### Agent C — Financial/payout existing infrastructure
> Прочитать `src/core/services/payout_service.py`, `billing_service.py`,
> `src/db/models/payout.py`. Вернуть: текущие payout methods (card, sbp,
> счёт), как связаны с legal_type owner, есть ли валидация реквизитов.

## 3.B Implementation

### 3.B.1 `PlacementGate` enum — 18 точек

`src/core/enums/placement_gate.py`:

**Pre-creation (перед созданием placement):**
- G01_ADVERTISER_LEGAL_PROFILE_COMPLETE
- G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED
- G03_ADVERTISER_LEGAL_TYPE_COMPLIANT

**Pre-escrow (перед оплатой, статус → pending_payment):**
- G04_OWNER_LEGAL_PROFILE_COMPLETE
- G05_OWNER_FRAMEWORK_CONTRACT_SIGNED
- G06_OWNER_PAYOUT_METHOD_VALID
- G07_SUPPLEMENTARY_AGREEMENT_SIGNED *(реализация ДС — Phase 4; здесь —
  заготовка gate'а с TODO и возвратом `fail + reason="phase4 pending"`
  пока. При Phase 4 gate заработает полностью.)*

**Pre-publication (escrow → published):**
- G08_ERID_REGISTERED
- G09_ORD_CONTRACT_REPORTED
- G10_PLACEMENT_TEXT_MARKED

**Post-publication (published → completed):**
- G11_PUBLICATION_VERIFIED
- G12_PUBLICATION_REPORTED_TO_ORD *(в течение 72ч per ФЗ-38)*

**Pre-payout (completed → payout_processing):**
- G13_PUBLICATION_PERIOD_ELAPSED
- G14_ACT_GENERATED
- G15_ACT_SIGNED_BOTH_SIDES
- G16_TAX_RECEIPT_ISSUED *(для self_employed owner — чек в "Мой налог")*
- G17_VAT_OBLIGATION_HANDLED *(для llc owner — счёт-фактура)*
- G18_PAYOUT_REPORTED_TO_ORD *(если оборот рекламы за месяц >N per ФЗ-38)*

### 3.B.2 `LegalComplianceService`

`src/core/services/legal_compliance_service.py`:
```python
@dataclass
class GateResult:
    gate: PlacementGate
    passed: bool
    blocker: bool        # True → нельзя проходить без resolve
    reason_code: str     # i18n key
    remediation_url: str | None  # куда отправить пользователя
    remediation_data: dict | None

class LegalComplianceService:
    def gates_for_transition(
        self, from_status: PlacementStatus, to_status: PlacementStatus
    ) -> list[PlacementGate]: ...

    async def check_gate(
        self, session, gate: PlacementGate, placement: PlacementRequest
    ) -> GateResult: ...

    async def check_gates_for_transition(
        self, session, placement, to_status
    ) -> list[GateResult]: ...
```

### 3.B.3 Отдельные gate-checkers
- `src/core/services/gates/` — по файлу на группу:
  - `advertiser_gates.py` (G01-G03)
  - `owner_gates.py` (G04-G06)
  - `agreement_gates.py` (G07 — заглушка)
  - `publication_gates.py` (G08-G10)
  - `post_publication_gates.py` (G11-G12)
  - `payout_gates.py` (G13-G18)
- Каждый gate-checker — чистая функция `async def check(session, placement) -> GateResult`.
- legal_type-specific логика в `G03`, `G16`, `G17`:
  - `individual` → валидный паспорт + checksum ИНН; налоговый агент удерживает
    НДФЛ в payout — flag для Phase 4 billing.
  - `self_employed` → статус НПД в ФНС активен (`fns_verification_status`);
    G16 обязателен при payout.
  - `ie` → ОГРНИП валиден + ЕГРИП snapshot свежее чем N дней.
  - `llc` → ОГРН валиден + ЕГРЮЛ snapshot + G17 обязателен.

### 3.B.4 Интеграция в `PlacementTransitionService`
- Перед каждым переходом:
  ```python
  gates = await compliance.check_gates_for_transition(session, placement, new_status)
  blockers = [g for g in gates if not g.passed and g.blocker]
  if blockers:
      raise TransitionBlockedError(blockers, placement_id=placement.id)
  ```
- Если `placement.is_test` и actor is admin: **не raise**, а сохранить
  blocker'ы в `placement.pending_gate_resolutions` (JSONB) и вернуть
  контролируемый результат — runtime pause (Phase 5 строит UI поверх).

### 3.B.5 API: эндпоинт статуса gate'ов
- `GET /api/placements/{id}/gates` → `list[GateResult]` (для UI фазы 5 и 7).

### 3.B.6 legal_profile доп. поля (ТОЛЬКО если Agent A покажет отсутствие)
- `fns_verification_status: Enum["unchecked", "active", "inactive"]`
- `fns_verified_at: datetime | None`
- `egrul_snapshot_at: datetime | None`
- `inn_checksum_valid: bool`
- Миграция в `0001_initial_schema.py`.

## 3.C Acceptance

- [ ] Все 18 gate-checkers имеют unit-тесты.
- [ ] Integration: попытка перехода без заполненного legal_profile —
  `TransitionBlockedError` с G01.
- [ ] Integration: test-placement (admin) проходит с blocker'ами в
  `pending_gate_resolutions` (без exception).
- [ ] legal_type-matrix тесты: individual / self_employed / ie / llc —
  каждый с соответствующими required gates.
- [ ] `GET /api/placements/{id}/gates` отдаёт все applicable gates.
- [ ] Snapshot для `GateResult` schema зафиксирован.
- [ ] `make lint`, `make test`, `make typecheck` — pass.
- [ ] `CHANGES_<date>_phase3-legal-gates.md` + `CHANGELOG.md`.

### 3.D Cross-cutting checklist
- [ ] **Repo:** gate-checkers читают через existing repos (inline queries запрещены):
  - `UserRepository.get_with_legal_profile(user_id)` — обогатить если нет.
  - `ContractRepository.has_signed_framework(user_id, role) -> bool` — новый метод.
  - `LegalProfileRepository.get_verification_status(user_id) -> FnsStatus` — новый.
  - `PayoutMethodRepository.get_valid_for_owner(owner_id)` — новый.
  - Inline `session.execute(select(...))` в gate-checkers → ❌.
- [ ] **Hooks:**
  - web_portal: `usePlacementGates(placementId: number)` — React Query, polling при `pending_gate_resolutions != {}`.
- [ ] **API modules:** `web_portal/src/api/placements.ts` — `getPlacementGates(id)`.
- [ ] **Types (Python):** `GateResult`, `PlacementGate` (string enum, 18 значений), `GateReason` + snapshot.
- [ ] **Types (TS):** те же в `web_portal/src/lib/types.ts`. В mini_app — НЕ добавляем (mini_app не рендерит gates — может содержать financial/legal_type детали).
- [ ] **Indices:**
  - **GIN** на `placement_requests.pending_gate_resolutions` (JSONB).
  - **Partial**: `ix_pr_pending_gates WHERE pending_gate_resolutions != '{}'::jsonb` — для admin panel query в Phase 5.
- [ ] **Frontend tests:** N/A (UI в Phase 5 admin + Phase 7 timeline events).
- [ ] **Mini_app audit:** gates НЕ отображаются в mini_app (ПД + legal_type info). Подтверждено.

**STOP → ждать "ок" перед Phase 4.**

---

# Phase 4 — Supplementary Agreements / ДС (4-5ч)

**Branch:** `feature/supplementary-agreements`

**Prerequisites:** Phase 3 merged. **ЯВНОЕ "ок" на правку `contract.py`.**

## 4.A Deep-dive research

Параллельно 2 агента:

### Agent A — Current contract model + service
> Прочитать `src/db/models/contract.py`, `src/core/services/contract_service.py`,
> `src/api/routers/contracts.py`. Вернуть: (1) все enum-values ContractType,
> (2) как генерируются рамочные (endpoints, вызовы), (3) поле `parent_contract_id`
> уже есть?, (4) методы подписи (click, КЭП, sms).

### Agent B — Act generation parallel
> Прочитать `src/db/models/act.py`, `src/core/services/` для act-generation.
> Вернуть: как генерируется закрывающий акт при завершении placement
> (template engine, PDF generation). Это модель для ДС генерации.

## 4.B Implementation

### 4.B.1 Расширение `Contract` модели
- В `ContractType` enum добавить `supplementary_agreement`.
- Добавить колонку `parent_contract_id: int | None` FK → contracts.id
  (самоссылка): `SELF-FK`.
- Добавить `placement_id: int | None` FK → placement_requests.id
  (только для ДС, для рамочных NULL).
- Миграция в `0001_initial_schema.py`.

### 4.B.2 `SupplementaryAgreementService`
`src/core/services/supplementary_agreement_service.py`:
- `async def generate_for_placement(session, placement) -> Contract`:
  - Создаёт Contract с `contract_type=supplementary_agreement`,
    `parent_contract_id=<advertiser's framework>`, `placement_id=<id>`,
    `user_id=<advertiser.id>`, `status=draft`.
  - Template: инкорпорирует условия placement (канал, цена, время, текст,
    erid, период) + ссылку на рамочный.
  - Аналогично для owner — вторая сущность Contract с тем же
    `placement_id`, но `parent_contract_id=<owner's framework>`,
    `user_id=<owner.id>`.
- Двух-стороннее подписание: placement считается "ДС подписано" когда
  оба Contract получили `status=signed`.

### 4.B.3 Hook в placement flow
- При переходе placement в `pending_payment` (после одобрения owner'ом
  условий) — `PlacementTransitionService` вызывает
  `supplementary_agreement_service.generate_for_placement()`.
- Gate `G07_SUPPLEMENTARY_AGREEMENT_SIGNED` проверяет существование
  двух Contract'ов с `placement_id=X, contract_type=supplementary_agreement,
  status=signed`.

### 4.B.4 API endpoints
- `GET /api/placements/{id}/supplementary-agreements` → оба ДС (advertiser + owner).
- `POST /api/contracts/{id}/sign` — уже есть, работает для ДС тоже (метод
  `click_accept` для ФЛ/самозанятых, `sms_code` fallback для остальных
  если КриптоПро не готов — НЕ откладываем, делаем fallback).
- Уведомления: при создании ДС — notification владельцу/рекламодателю.

### 4.B.5 UI (web_portal only per ФЗ-152)
- В `CampaignWaiting.tsx` (статус `pending_payment`): секция
  "Доп. соглашение — подпишите" с кнопкой перехода на ContractDetail.
- `OwnRequestDetail.tsx`: аналогично.
- Mini_app: НЕ показывает (ДС содержит реквизиты = ПД).

## 4.C Acceptance

- [ ] Переход placement в `pending_payment` → созданы 2 Contract'а с
  `contract_type=supplementary_agreement`.
- [ ] G07 gate: оба не подписаны → fail; оба подписаны → pass.
- [ ] Integration: не подписав ДС нельзя перейти в escrow.
- [ ] UI: advertiser видит кнопку "Подписать ДС" на CampaignWaiting.
- [ ] PDF generation работает (можно скачать ДС).
- [ ] `make lint`, `make test`, `make typecheck` — pass.
- [ ] `CHANGES_<date>_phase4-supplementary-agreements.md` + `CHANGELOG.md`.

### 4.D Cross-cutting checklist
- [ ] **Repo:** `ContractRepository` дополнить:
  - `list_supplementary_for_placement(placement_id: int) -> list[Contract]`
  - `get_by_placement_and_role(placement_id: int, role: UserRole) -> Contract | None`
  - `count_unsigned_supplementary_for_user(user_id: int) -> int` (для badge в P6)
  - `exists_signed_supplementary_both_sides(placement_id: int) -> bool` (для G07)
- [ ] **Hooks:**
  - web_portal: `useSupplementaryAgreements(placementId)`, `useSignSupplementary(contractId)`.
- [ ] **API modules:** `web_portal/src/api/contracts.ts` — `getSupplementaryForPlacement()`, reuse `signContract()`.
- [ ] **Types (Python):** `SupplementaryAgreementResponse` + snapshot; `ContractType` enum расширить `supplementary_agreement`; `ContractResponse` snapshot обновить (добавились `parent_contract_id`, `placement_id`).
- [ ] **Types (TS):** обновить `Contract`, `ContractType` в `web_portal/src/lib/types.ts`. Mini_app не содержит Contract-типа (удалён в P1).
- [ ] **Indices:**
  - `ix_contract_placement_type (placement_id, contract_type)` — для поиска ДС конкретного placement.
  - `ix_contract_parent (parent_contract_id)` — для навигации ДС→рамочный.
- [ ] **Frontend tests:**
  - Playwright `web_portal/tests/specs/sign-supplementary-agreement.spec.ts` — advertiser подписывает, owner подписывает, G07 становится pass, placement переходит в escrow. 3 viewport'а.
- [ ] **Mini_app audit:** ДС не отображается в mini_app (реквизиты). Подтверждено.

**STOP → ждать "ок" перед Phase 5.**

---

# Phase 5 — Test-mode runtime + admin UI (5-7ч)

**Branch:** `feature/test-mode-runtime`

**Prerequisites:** Phase 4 merged.

## 5.A Deep-dive research

Параллельно 3 агента:

### Agent A — Channel repository + current is_test usage
> Прочитать `src/db/repositories/channel_repo.py`, все места где
> используется `channel.is_test`, `User.is_test`. Вернуть: (1) как сейчас
> фильтруются каналы для advertiser'а, (2) где `is_test` меняет логику
> (что конкретно bypass'ится), (3) структура admin-role check.

### Agent B — Existing tests fixtures + factories
> Прочитать `tests/conftest.py`, найти `tests/factories/`, `tests/fixtures/`,
> `tests/unit/**/conftest.py`. Вернуть: (1) есть ли factory_boy / pytest
> fixtures для PlacementRequest, Channel, User, (2) есть ли готовые сценарии
> для mock external services (ORD response, YooKassa webhook), (3) как
> организован единый источник истины для mock-данных.

### Agent C — External service providers
> Прочитать `src/core/services/ord_provider.py`, `stub_ord_provider.py`,
> `src/utils/telegram/sender.py`, `src/core/services/yookassa_service.py`
> (если есть). Вернуть: (1) есть ли уже provider pattern у каждого, (2) как
> выбирается реализация (env var? factory?), (3) список внешних сервисов
> требующих mock: ORD, Telegram Bot API (публикация), YooKassa, КриптоПро,
> ФНС ("Мой налог"), ЕГРЮЛ/ЕГРИП.

## 5.B Implementation

### 5.B.1 Closed-loop validation
- `PlacementRequestService.create()`:
  ```python
  if channel.is_test != advertiser.is_test or channel.is_test != channel.owner.is_test:
      raise IsTestMismatchError()
  placement.is_test = channel.is_test  # наследование, не user input
  ```
- В `PlacementCreateRequest` схеме — удалить поле `is_test` из public API.

### 5.B.2 Channel visibility filter
- `ChannelRepository.list_available_for(user)`:
  ```python
  query = select(Channel).where(Channel.status == ChannelStatus.active)
  if not user.is_admin:
      query = query.where(Channel.is_test == False)
  ```
- Frontend: channel-selector эндпоинт автоматически возвращает отфильтрованный
  список. Для admin — в UI добавлен toggle "Показать только тестовые"
  (галочка `is_test` на placement creation).

### 5.B.3 Admin-only `is_test` галочка
- `PlacementCreateRequest` — добавить `is_test_run: bool = False`.
- Backend: если `is_test_run and not user.is_admin` → 403.
- Backend: если `is_test_run=True` → channel-selector фильтр
  `Channel.is_test == True only`.
- Frontend (web_portal, NOT mini_app): в campaign-creation wizard
  добавить `<IsTestRunToggle />` — виден только если `user.is_admin`.
  При включении — channel dropdown rerender'ится с test-only.

### 5.B.4 Provider pattern + admin override API
Каждый внешний провайдер получает единый интерфейс:
```python
class ExternalProvider(Protocol):
    async def call(self, request: ProviderRequest, placement_id: int) -> ProviderResult: ...
```
Провайдеры:
- `OrdProvider` (`RealYandexOrdProvider` | `StubOrdProvider`)
- `TelegramPublisher` (`RealTelegramPublisher` | `SandboxTelegramPublisher` —
  отправка в `settings.sandbox_telegram_channel_id`)
- `PaymentProvider` (`RealYookassaProvider` | `MockPaymentProvider`)
- `ContractSigner` (`RealKepSigner` | `ClickSimulationSigner` |
  `SmsCodeSigner` — fallback для pre-КриптоПро эры)
- `FnsProvider` (`RealFnsProvider` | `MockFnsProvider`)
- `EgrulProvider` (`RealEgrulProvider` | `MockEgrulProvider`)

Выбор через factory:
```python
def get_ord_provider(placement: PlacementRequest) -> OrdProvider:
    if placement.is_test and settings.ord_provider == "stub":
        return StubOrdProvider()
    return _real_ord_provider()  # per settings.ord_provider
```

### 5.B.5 Runtime admin override (ключевая механика)

Когда gate возвращает `fail + blocker` И `placement.is_test` И actor admin:
- Placement приостанавливается (transition НЕ выполнен, статус остаётся).
- В `placement.pending_gate_resolutions` (JSONB):
  `[{"gate": "G08_ERID_REGISTERED", "reason": "ord_unreachable", ...}]`.
- Новый endpoint:
  ```
  POST /api/admin/placements/{id}/gates/{gate_code}/resolve
  body: {
    action: "retry" | "mock",
    mock_fixture_id?: string   // id fixture из tests/factories/
  }
  ```
- `retry`: повторный вызов real provider (с соответствующим provider-switch).
- `mock`: загружает fixture из `tests/factories/*` через helper
  (см. 5.B.6) — те же сценарии что используются в pytest. Применяет
  результат (например: placement.erid = "TEST-ERID-<id>-<ts>"), перезапускает
  gate-check, если pass → продолжает flow.

### 5.B.6 Mock fixtures через test infrastructure
- НЕ создаём отдельный каталог `src/mocks/`.
- Создаём модуль `src/core/testing/fixture_loader.py` (имя намеренно
  содержит "testing" — это scope):
  ```python
  def list_fixtures_for_gate(gate: PlacementGate) -> list[FixtureMetadata]: ...
  def load_fixture(fixture_id: str) -> dict: ...
  ```
- Эти функции читают из `tests/factories/` / `tests/fixtures/` (путь
  относительно project root), используя тот же factory_boy API что pytest.
- Важное: `tests/` остаётся test directory; модуль `fixture_loader`
  импортирует оттуда только при runtime admin override (не для prod flow).
- CI: для prod build убираем `tests/` из docker image — значит runtime
  override доступен **только в dev/test docker сборке**. В prod admin UI
  показывает только кнопку "retry", mock кнопка недоступна.

### 5.B.7 Admin UI для gate resolution
- `web_portal/src/screens/admin/PlacementGatesPanel.tsx`:
  - Список placement'ов с `pending_gate_resolutions`.
  - Для каждого gate: описание проблемы + remediation_url + 2 кнопки:
    - **"Выполнить реально"** — `POST ... /resolve body={action:retry}`.
    - **"Подтянуть mock"** — выпадашка fixture'ов (из
      `GET /api/admin/fixtures?gate={code}`) + кнопка apply.
- Встроить в CampaignWaiting/OwnRequestDetail для admin-просмотра: badge
  "N gates pending" + ссылка на панель.

## 5.C Acceptance

- [ ] Advertiser не видит test-каналы; admin видит всё.
- [ ] Non-admin не может создать placement с `is_test_run=True`.
- [ ] Closed-loop mismatch → 422.
- [ ] Integration: test-placement → провайдеры все stub/mock; real-placement
  → провайдеры все real.
- [ ] Gate failure в test-mode → placement в `pending_gate_resolutions`;
  admin через API resolve(mock) → placement продвигается.
- [ ] Fixture loader: та же factory что и в pytest.
- [ ] В production docker image `tests/` отсутствует → admin UI не показывает
  mock кнопку.
- [ ] Playwright: admin gate-resolution flow desktop + mobile.
- [ ] `make lint`, `make test`, `make typecheck` — pass.
- [ ] `CHANGES_<date>_phase5-test-mode.md` + `CHANGELOG.md`.
- [ ] `docker compose up -d --build nginx api`.

### 5.D Cross-cutting checklist
- [ ] **Repo:**
  - `ChannelRepository.list_available_for(user)` — с фильтром `is_test` по роли (упомянуто в 5.B.2).
  - `PlacementRepository.list_with_pending_gates_for_admin(limit, offset) -> list[PlacementRequest]` — использует partial index из P3.
  - Inline queries в endpoints admin-панели → ❌.
- [ ] **Hooks:**
  - web_portal: `useTestChannels()`, `useAdminPendingGates()`, `useResolveGate(placementId, gateCode)`, `useGateFixtures(gateCode)`, `useIsAdmin()`.
- [ ] **API modules:** `web_portal/src/api/admin.ts` — `listPendingGates()`, `resolveGate()`, `listFixtures()`; `web_portal/src/api/channels.ts` — фильтр test.
- [ ] **Types (Python):** `ResolveGateRequest`, `FixtureMetadata`, `AdminPendingGatesResponse` + snapshots; `IsTestMismatchError` — новое исключение.
- [ ] **Types (TS):** те же + `IsTestRunToggle` prop types. Mini_app — НЕ содержит admin types.
- [ ] **Indices:**
  - Partial `ix_pr_pending_gates` (из P3) переиспользуется.
  - `ix_channel_is_test (is_test)` — если admin часто фильтрует.
- [ ] **Frontend tests:**
  - Playwright `admin-gate-resolution.spec.ts` — retry и mock flow, desktop + mobile.
  - Playwright `test-channel-visibility.spec.ts` — non-admin не видит test-каналов.
  - Playwright `is-test-run-toggle.spec.ts` — галочка видна только admin.
- [ ] **Mini_app audit:** НЕ затрагивается (test-mode admin-only, admin работает только в web_portal).

**STOP → ждать "ок" перед Phase 6.**

---

# Phase 6 — Contracts/Acts UX + ORD production hardening (3-4ч)

**Branch:** `feature/contracts-acts-ord-prod`

**Prerequisites:** Phase 5 merged.

## 6.A Deep-dive research

Параллельно 2 агента:

### Agent A — mini_app navigation map
> Прочитать `mini_app/src/App.tsx`, `screens/advertiser/AdvMenu.tsx`,
> `screens/owner/OwnMenu.tsx`, `screens/common/Cabinet.tsx`. Вернуть: все
> пункты меню, их иконки, порядок. Определить оптимальное место для
> "Документы" с badge'ем.

### Agent B — Current ERID rendering + prod-block logic
> Прочитать `src/core/services/publication_service.py`, `_build_marked_text`,
> `web_portal/src/screens/advertiser/campaign/CampaignWaiting.tsx`,
> `CampaignPublished.tsx`. Вернуть: (1) текущая логика ERID-проверки,
> (2) где ERID визуализируется, (3) как `settings.ord_provider` будет
> влиять на реальный блок.

## 6.B Implementation

### 6.B.1 mini_app документы как badge + deep-link
- `mini_app/src/api/client.ts` (или где ax/ky инстанс) — оставляем, но без
  contracts/acts endpoints (уже удалены в Phase 1).
- Backend: новые lightweight endpoints:
  - `GET /api/contracts/unread-count` → `{count: N}`
  - `GET /api/acts/unread-count` → `{count: N}`
  - (оба без ПД в response)
- Компонент `mini_app/src/components/DocumentsBadge.tsx`:
  - Показывает сумму unread contracts + acts.
  - onClick → `OpenInWebPortal` (`target=/documents` — новый "landing"
    экран в web_portal со списками contracts+acts).
- В `AdvMenu.tsx` и `OwnMenu.tsx` добавить пункт "Документы" с
  `<DocumentsBadge />`. `Cabinet.tsx` аналогично.

### 6.B.2 Web_portal `/documents` landing
- `web_portal/src/screens/common/DocumentsHub.tsx`:
  - Две вкладки: "Договоры" / "Акты".
  - Переиспользует существующие `ContractList`, `MyActsScreen` (уже
    есть в web_portal).

### 6.B.3 ORD production hardening
- `src/config/settings.py`:
  - `ord_provider: Literal["stub", "yandex", "vk", "ozon"] = "stub"`.
  - **Удалить** `ord_block_publication_without_erid` (замена —
    детерминированная логика).
- `src/core/services/publication_service.py::_build_marked_text`:
  ```python
  if not placement.erid:
      if settings.ord_provider == "stub":
          # dev/sandbox — публикуем без маркера или с TEST-меткой
          text = base_text + ("\n[ТЕСТОВАЯ ПУБЛИКАЦИЯ]"
                              if placement.is_test else base_text)
      else:
          # production — без ERID нельзя
          raise PublicationBlockedError(
              "ERID required: ord_provider={settings.ord_provider}"
          )
  else:
      text = f"{base_text}\n\nРеклама. {advertiser_name}\nerid: {placement.erid}"
  ```
- Gate G08 (Phase 3) использует ту же детерминированную логику.
- UI: в `CampaignWaiting.tsx` секция "ОРД" — убираем вручную; всё видно
  через Timeline (Phase 7) как event.

### 6.B.4 КЭП fallback (чтобы не blocker для pre-launch)
- `ContractSigner` провайдер (из Phase 5) имеет три реализации:
  - `ClickSimulationSigner` — для `individual`/`self_employed` (click accept
    юридически достаточно).
  - `SmsCodeSigner` — для `ie`/`llc` (enhanced, SMS code на зарегистрированный
    номер) — **временный fallback** до интеграции КриптоПро.
  - `RealKepSigner` — когда подключен реальный КриптоПро (отдельный тикет
    вне плана, но интерфейс готов).
- Сервис `ContractService.sign` выбирает метод по `legal_type` пользователя
  + `signature_method` в запросе + флага `settings.kep_available`.

## 6.C Acceptance

- [ ] mini_app: в AdvMenu и OwnMenu виден пункт "Документы" с badge.
- [ ] Клик на "Документы" → web_portal `/documents` с залогиненным
  пользователем.
- [ ] `settings.ord_provider=yandex` + placement.erid=None → 
  `PublicationBlockedError`.
- [ ] `settings.ord_provider=stub` + is_test=True + erid=None → публикация
  с "[ТЕСТОВАЯ ПУБЛИКАЦИЯ]".
- [ ] `ie` пользователь: sign через SMS code — работает end-to-end.
- [ ] `make lint`, `make test`, `make typecheck` — pass.
- [ ] `CHANGES_<date>_phase6-docs-ord.md` + `CHANGELOG.md`.
- [ ] `docker compose up -d --build nginx api`.

### 6.D Cross-cutting checklist
- [ ] **Repo:**
  - `ContractRepository.unread_count_for_user(user_id: int) -> int` — считает supplementary + framework с `status in (draft, pending)`.
  - `ActRepository.unread_count_for_user(user_id: int) -> int` — аналогично.
  - Inline COUNT query → ❌.
- [ ] **Hooks:**
  - mini_app: `useDocumentsBadge()` — poll every 60s (или websocket, если в проекте есть).
  - web_portal: `useDocumentsHub()` — агрегированный для `/documents` экрана.
- [ ] **API modules:**
  - mini_app: `api/documents.ts` — `getUnreadCount()`.
  - web_portal: `api/documents.ts` — `getDocumentsHub()` (комбо: contracts + acts).
- [ ] **Types (Python):** `UnreadCountResponse {count: int}`, `DocumentsHubResponse` + snapshot.
- [ ] **Types (TS):** `UnreadCountResponse` в обоих `types.ts`. Mini_app НЕ импортирует полные `Contract`/`Act` типы (только count).
- [ ] **Indices:**
  - `ix_contract_user_status (user_id, contract_status)` — для COUNT WHERE status IN (...).
  - `ix_act_signer_status (signer_user_id, sign_status)` — аналогично.
- [ ] **Frontend tests:**
  - Playwright `mini-app-documents-badge.spec.ts` — badge показывает count, клик → web_portal login.
  - Playwright `ord-prod-block.spec.ts` — установить `ord_provider=yandex`, erid=None → blocked.
- [ ] **Mini_app audit:** в AdvMenu/OwnMenu/Cabinet добавлен пункт "Документы" с badge. ПД не проходят через mini_app (только count числом).

**STOP → ждать "ок" перед Phase 7.**

---

# Phase 7 — UI Timeline + schedule gaps + educational overlay (3-4ч)

**Branch:** `feature/placement-timeline-ui`

**Prerequisites:** Phase 6 merged.

## 7.A Deep-dive research

Параллельно 2 агента:

### Agent A — Existing timeline-like components
> Найти в `web_portal/src/` и `mini_app/src/` компоненты с ключами
> `Timeline`, `Stepper`, `History`, `Status`. Вернуть: что есть, какой
> уровень переиспользуемости, tailwind/CSS conventions в проекте.

### Agent B — Schedule field rendering audit
> В `web_portal/src/screens/advertiser/campaign/CampaignWaiting.tsx`,
> `CampaignPublished.tsx`, `_shell.tsx`, `screens/owner/OwnRequestDetail.tsx`
> найти все рендеры `final_schedule`, `proposed_schedule`, `published_at`,
> `scheduled_delete_at`, `expires_at`. Таблица: компонент × поле × статус
> (в каком статусе рендерится).

## 7.B Implementation

### 7.B.1 Backend: единый timeline endpoint
`GET /api/placements/{id}/timeline` (уже есть skeleton из Phase 2) —
вернуть агрегированный поток событий:
- Status transitions (из `placement_status_history`, Phase 2).
- Scheduled events (из timestamp-полей): `final_schedule`,
  `scheduled_delete_at`, `expires_at`.
- Gate events (из Phase 3): "G08 ERID registered at T", fail/pass/resolved
  by admin.
- Контракты: создан / подписан (advertiser → owner).

Response: `list[TimelineEvent]` с полями `timestamp`, `event_type`,
`actor`, `description`, `status_meta`.

### 7.B.2 Frontend компонент `<PlacementTimeline />`
- `web_portal/src/components/placement/PlacementTimeline.tsx`:
  - Vertical stepper.
  - Event types: `status_transition`, `gate_passed`, `gate_failed`,
    `gate_resolved_admin_mock`, `scheduled_publication`,
    `scheduled_deletion`, `contract_signed`, `act_signed`, ...
  - Цветовое кодирование: completed / current / scheduled /
    blocked (gate failure).
  - Responsive: на mobile horizontal scroll или compact vertical.

### 7.B.3 Educational overlay для admin
- Если `placement.is_test and user.is_admin` — каждому событию timeline
  добавляется info-callout:
  - "В production на этом шаге вызывается YooKassa webhook → freeze_escrow
    Celery task → ..."
  - Тексты в `src/core/constants.py::TIMELINE_EDUCATIONAL_NOTES` (enum-key
    → текст).
- Non-admin или non-test placement: overlay не рендерится.

### 7.B.4 Интеграция в экраны + schedule gap fixes
- `CampaignWaiting.tsx` — добавить `<PlacementTimeline />` ниже основной
  информации. Убедиться что `scheduled_delete_at` рендерится в статусе
  `escrow` (через Timeline, не inline) — gap из findings закрыт.
- `CampaignPublished.tsx` — inline-таймлайн (если был) заменить на компонент.
- `OwnRequestDetail.tsx` — добавить Timeline.
- Все inline-ERID-блоки удалить: ERID только как event в Timeline.

### 7.B.5 Playwright tests
- `placement-timeline.spec.ts` — на iPhone SE, Pixel 5, Desktop Chrome.
- Проверка educational overlay для admin (role switch).
- Проверка всех schedule-полей рендерятся как events.

## 7.C Acceptance

- [ ] Timeline виден на CampaignWaiting, CampaignPublished, OwnRequestDetail.
- [ ] `scheduled_delete_at` рендерится в статусе `escrow` (как event).
- [ ] Admin в test-placement видит educational overlay, обычный user — нет.
- [ ] Gate failure/resolution — отдельный event type в timeline.
- [ ] Playwright: mobile + desktop — green.
- [ ] `make lint`, `make test`, `make typecheck` — pass.
- [ ] `CHANGES_<date>_phase7-timeline-ui.md` + `CHANGELOG.md`.
- [ ] `docker compose up -d --build nginx api`.

### 7.D Cross-cutting checklist
- [ ] **Repo:** aggregator-endpoint переиспользует existing repos:
  - `PlacementStatusHistoryRepo.list_by_placement` (P2)
  - `ContractRepository.list_supplementary_for_placement` (P4)
  - `ActRepository.list_by_placement` — новый метод.
  - Новый **сервис-агрегатор** `PlacementTimelineService.build_timeline(placement_id) -> list[TimelineEvent]` собирает все источники и сортирует по времени.
- [ ] **Hooks:**
  - web_portal: `usePlacementTimelineEvents(placementId)` — заменяет/обёртка `usePlacementTimeline` из P2.
  - mini_app: `usePlacementTimelineCompact(placementId)` — упрощённая версия, только status + schedule.
- [ ] **API modules:**
  - web_portal: `api/placements.ts::getTimelineEvents(id)`.
  - mini_app: `api/placements.ts::getTimelineCompact(id)` — отдельный эндпоинт `GET /api/placements/{id}/timeline/compact` возвращает subset без legal_type/financial данных.
- [ ] **Types (Python):** `TimelineEvent`, `TimelineEventType` enum, `TimelineCompactResponse` (для mini_app) + snapshots.
- [ ] **Types (TS):** те же в обоих `types.ts`; mini_app получает narrow subset.
- [ ] **Indices:** N/A (переиспользуем созданные в P2, P3, P4).
- [ ] **Frontend tests:**
  - Playwright `web_portal/tests/specs/placement-timeline.spec.ts` — desktop + mobile, все event types рендерятся.
  - Playwright `placement-timeline-admin-overlay.spec.ts` — admin видит educational callouts, non-admin нет.
  - Playwright `placement-timeline-compact-miniapp.spec.ts` — compact timeline без legal/financial.
- [ ] **Mini_app audit:** `PlacementTimelineCompact.tsx` — новый компонент, показывает только status transitions + schedule events. Gates и financial details отсутствуют. ПД-утечка исключена.

**STOP → итоговый merge.**

---

# 5. Финальный merge и удаление плана

После всех 8 фаз:

1. Все feature-ветки смержены в `develop` через `--no-ff`.
2. `git checkout develop && git pull`.
3. Убедиться: `make lint && make test && make typecheck` — pass.
4. Прогнать Playwright полностью: `cd web_portal && npx playwright test`.
5. `git checkout main && git pull`.
6. `git merge develop --no-ff -m "chore(main): merge develop — legal gates +
   transition service + test-mode runtime (v4.4.0)"`.
7. Tag `v4.4.0`.
8. **Удалить этот файл**:
   ```bash
   git checkout -b chore/remove-active-plan
   git rm IMPLEMENTATION_PLAN_ACTIVE.md
   git commit -m "chore: remove active plan after implementation"
   git checkout develop && git merge chore/remove-active-plan --no-ff
   git checkout main && git merge develop --no-ff
   git push origin develop main
   ```

# 6. Что НЕ делаем (и почему)

- **Отдельный `src/mocks/`** — моки и так в `tests/`, переиспользуем.
- **SQLAlchemy event-hook на status** — магия, ломается на Celery/bulk.
  Используем explicit transition function.
- **`run_mode` enum** — лишняя сущность; is_test достаточно.
- **Runtime правка `audit_middleware.py`** — новый `aud_audit_middleware.py`.
- **`sandbox_step` отдельный режим** — runtime pause происходит естественно
  на gate-failure; явный step-mode не нужен.
- **Миграция legacy placement в `placement_status_history`** — pre-prod,
  БД пересоздаётся; history начнёт заполняться с момента listener'а.
- **Реальные интеграции (ОРД/КриптоПро/Мой налог)** — отдельные тикеты;
  план готовит архитектуру под них (provider pattern), но фактические
  контракты с провайдерами вне scope.
- **`test.fixme(true, ...)` Playwright BL-001/002/003** — остаются как
  есть, они deferred per CLAUDE.md.
