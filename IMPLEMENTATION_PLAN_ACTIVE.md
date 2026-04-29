# IMPLEMENTATION_PLAN_ACTIVE.md — Consolidated session plan (rev 4)

_Last updated: 2026-04-28 (post Phase 2 closure, серия 15.x active, BL-037 codified)_

> **Одноразовый рабочий план.** После завершения ВСЕХ фаз (0 → 7) + серий 15.x / 16.x исполнитель удаляет этот файл (`git rm IMPLEMENTATION_PLAN_ACTIVE.md`) в финальном коммите в `main`. Файл НЕ попадает в релизный `main`.
>
> **Проект не в production.** Критерий — не "правильно", а "архитектурно элегантно". Backward compatibility НЕ требуется. Мёртвый код, dev-only ветки, hardcoded значения — удаляются.
>
> **Каждая фаза = отдельная сессия.** Между фазами — stop-point. Новая сессия открывается копированием соответствующего раздела "Phase N" целиком в prompt.
>
> **Каждая фаза начинается с deep-dive research** (параллельные Explore-агенты) ДО написания кода. Implementation стартует только после того, как research подтверждён.
>
> **После каждой фазы:** `reports/docs-architect/discovery/CHANGES_<YYYY-MM-DD>_<slug>.md` + `CHANGELOG.md [Unreleased]` + Conventional Commits + push в `feature/*` → merge в `develop` --no-ff → **STOP, ждать явного "ок"** перед следующей.
>
> **Общие правила (копируются в каждую сессию):**
> - CLAUDE.md, MEMORY.md, `src/config/settings.py`, `PROJECT_KNOWLEDGE.md` — обязательно перечитать.
> - **Research-фазы обязаны иметь секцию "Возражения и риски" перед "Вопросами для подтверждения".** Спорить с планом, когда есть основания.
> - **Phase-mode дисциплина:**
>   - Research / planning (0.A, N.A): «Будь критичным, ищи проблемы, оспаривай решения с аргументацией.»
>   - Implementation (0.B–0.C, N.B–N.C): «Реализуй план как написано. Если вылезла блокирующая проблема — останавливайся и сообщай. Не вноси не предусмотренные планом улучшения.»
> - **Что поднимать явно vs что отложить:**
>   - **Поднимать (block / interrupt):** (а) проблемы безопасности, (б) баги или потенциальные баги, (в) явные противоречия в плане или требованиях, (г) решения, заметно усложняющие будущую поддержку.
>   - **Отложить одной строкой в конце отчёта** под заголовком «возможные дальнейшие улучшения, не требуют действий сейчас»: косметические рефакторы, стилистические придирки, test coverage gaps в нетронутом коде, perf-оптимизации без замеров, naming preferences без семантического mismatch.
> - S-48 transaction contract (сервис не открывает/не закрывает транзакции).
> - **BL-037 sub-stage tracking** (Phase 3+ design rule): каждый flow проектируется с явным sub-stage tracking + fail-fast STOP. См. секцию ниже.
> - API convention: screen → hook → api-module (ESLint + grep-guard).
> - Pre-production migration rule: правим `0001_initial_schema.py`, новые Alembic revisions НЕ создаём.
> - Git flow: feature/* → develop → main, --no-ff всегда, НИКОГДА `--no-verify`.
> - Хардкоды запрещены везде: значения в `settings.py` (env), `src/core/constants.py` (compile-time) или `src/constants/fees.py` (financial rates).
> - Mocks для runtime/test переиспользуют existing `tests/` infrastructure (factories, fixtures, conftest). Новых директорий `src/mocks/` НЕ создаём.
> - Explicit transition function для `placement.status` — прямое присваивание запрещено линтером (Phase 2 закрыто).
> - ПД никогда не показываются и не принимаются через mini_app.
> - После изменений в `src/` или `mini_app/src/` — обязательный rebuild: `docker compose up -d --build nginx api`.

---

## Status overlay (обновляется по мере работы)

| Этап | Статус | Дата | Branch / merge | Эффект |
|------|--------|------|----------------|--------|
| Phase 0 | ✅ DONE | 2026-04-25 | merged develop+main | ENABLE_E2E_AUTH, JWT `aud`, ticket bridge, centralized URLs |
| Phase 1 | ✅ DONE | 2026-04-25 | merged develop+main | ФЗ-152 hardening — 23 PII endpoints на web_portal-only auth, mini_app legal strip |
| Phase 2 | ✅ DONE | 2026-04-27 | `9adaef2` merge | `PlacementTransitionService`, `placement_status_history`, forbidden-patterns lint, dead code cleanup |
| **15.x серия** | 🟡 IN FLIGHT | 2026-04-28+ | rolling | Centralized Fee Model + Legal Consistency rewrite. См. отдельную секцию ниже |
| **16.x серия** | ⏸ Pending (open) | — | — | PII Hardening (closes findings из `PII_AUDIT_2026-04-28.md`). Не начата |
| Phase 3 | ⏸ Pending | — | — | Legal Compliance Gates (18 точек) |
| Phase 4 | ⏸ Pending | — | — | Supplementary Agreements (ДС) |
| Phase 5 | ⏸ Pending | — | — | Test-mode runtime + admin UI + provider pattern |
| Phase 6 | ⏸ Pending | — | — | Contracts/Acts UX + ORD production hardening |
| Phase 7 | ⏸ Pending | — | — | UI Timeline + sub-stage events + educational overlay (BL-037 visualization) |

**Branch HEADs (на момент обновления):**
- `main` = `68d570d`
- `develop` = `6539552`

---

## 0. Цель и мотивация

Подготовить проект к production-запуску так, чтобы исключить юридические и финансовые риски (ФЗ-152, ФЗ-115, ФЗ-38, ГК РФ ст.432, НК РФ, УК ст.159 при систематике). Механизм — **система блокирующих юр. gate'ов** на переходах PlacementRequest, с идентичным flow в production и test-mode (runtime admin override через моки для каждого gate-failure).

---

## 1. Архитектурные принципы плана (обязательны)

1. **Zero hardcoded values** — URLs, префиксы, TTL, timeouts, limits, magic numbers → `settings.py` (env), `src/core/constants.py` (compile-time) или `src/constants/fees.py` (financial rates). CI-guard в `scripts/check_forbidden_patterns.sh` (17/17 patterns, post-Phase-2).
2. **Zero dev/prod divergence** — `ENVIRONMENT` переменная удалена в Phase 0 (заменена на `enable_e2e_auth`). Разное поведение dev/prod недопустимо (тесты перестают отражать реальность).
3. **Mocks = test infrastructure** — `tests/factories/`, `tests/fixtures/`, `conftest.py`. Runtime admin mock-override в Phase 5 подтягивает сценарии из той же инфраструктуры. Новых `src/mocks/` директорий НЕ создавать.
4. **Explicit transition function** — `PlacementTransitionService.transition()` единственная точка смены `placement.status`. Линтер запрещает прямое присваивание (Phase 2 done).
5. **Legal Compliance Gates first-class** — 18 gate'ов (Phase 3), enum `PlacementGate`, единый сервис `LegalComplianceService.check_gates()`. Каждый status-переход прогоняется через relevant gates.
6. **ФЗ-152 абсолютно** — ПД (паспорт, ИНН, реквизиты, сканы) в mini_app НЕ отображаются и НЕ принимаются. Backend отклоняет с 403 любой запрос с `aud != web_portal` на PII endpoints (Phase 1 done — 23 endpoints; Phase 16.x закроет оставшиеся payouts/admin endpoints).
7. **Test-mode = runtime, admin-only** —
   - Test-каналы невидимы non-admin (фильтр в репозитории).
   - Галочка "тестовая кампания" видна только admin.
   - При включении галочки channel-selector отдаёт только test-каналы.
   - Closed-loop: `placement.is_test == channel.is_test == owner.is_test`.
   - Flow идентичен production (все gate'ы применяются).
   - На каждом failed gate admin получает диалог: **"Выполнить реально"** (retry external call) **/** **"Подтянуть mock"** (fixture из tests/). Non-admin mock недоступен — только reality.
8. **Sub-stage tracking + fail-fast STOP (BL-037)** — каждый flow design'ится с явным sub-stage state machine. Любой failed sub-stage → STOP, не continues. См. секцию BL-037 ниже.
9. **Owner-side hard preconditions** — добавление канала возможно только при заполненном legal_profile + подписанном framework contract (`owner_service_<legal_status>`). Иначе **DECLINE**, не warning. Применяется в Phase 3 G04/G05/G06.

---

## 2. Domain: Placement Lifecycle Flow (authoritative)

Это business flow платформы. Каждое размещение проходит 8 главных этапов. Этот раздел — single source of truth для timeline UI (Phase 7), gate enforcement (Phase 3), document generation (Phase 4, 6).

### 8 главных этапов

| # | Этап | Триггер | Документ(ы) | Применимо к |
|---|------|---------|-------------|-------------|
| 1 | Регистрация | Первый login | `platform_rules` | Все, mandatory |
| 2 | Юр. статус | Заполнение профиля | _декларация в профиле, без подписей_ | Все. `FL / NP / IE / LE → User.legal_status` |
| 3 | Старт работы | Первое действие в роли | `advertiser_campaign` (при первой заявке)<br>`owner_service_{fl,np,ie,le}` (при добавлении канала) | По роли |
| 4 | Принятие заявки | Owner принимает + escrow frozen | `act_placement` (единый шаблон) | Все размещения |
| 5 | ОРД регистрация | Перед публикацией | `ord_registration → ERID` (обязательно per ФЗ-38) | Все размещения |
| 6 | Публикация | Bot отправляет пост с ERID-маркировкой | `invoice_b2b` (только если `advertiser.legal_status == LE`) | Все размещения |
| 7 | Завершение | Период публикации истёк, escrow released | `act_advertiser` + `act_owner_{fl,np,ie,le}` | Все размещения |
| 8 | Выплата | Owner запросил вывод | `kudir_book` (авто-запись для УСН) | Все размещения |

### Hard preconditions (DECLINE если не выполнены)

**Owner-side, перед добавлением канала:**
1. `User.legal_status` заполнен (FL / NP / IE / LE).
2. Юр. профиль заполнен полностью (поля по `legal_status`).
3. Верификация данных юр. профиля прошла (ИНН checksum + ФНС статус для NP / ЕГРИП для IE / ЕГРЮЛ для LE).
4. Подписан основной договор (`owner_service_{legal_status}`).

Если 1-4 не выполнены при попытке добавить канал → DECLINE. Канал не может быть добавлен. Phase 3 enforces (G04/G05/G06).

**Advertiser-side, перед первой заявкой:**
1. `User.legal_status` заполнен.
2. Подписан `advertiser_campaign` (рамочный договор рекламодателя).
3. Если `legal_status == LE` — реквизиты для счёт-фактуры (`invoice_b2b`).

Phase 3 enforces (G01/G02/G03).

**Pre-publication, этап 5 → 6:**
- ERID получен и валиден.
- Без ERID публикация в production невозможна (ФЗ-38 violation). Phase 6 hardening enforces.

---

## 3. BL-037 — Sub-stage tracking + fail-fast STOP (cross-cutting requirement)

**Принципиальное требование к timeline visualization (Phase 7) и flow execution design (Phase 3-7, серия 15.x, серия 16.x).**

### Правило

Timeline в UI отображает **не только 8 главных этапов, но и все промежуточные sub-stages внутри каждого этапа**. Если **любой** sub-stage упал — flow **STOP** на текущем этапе, статус явно зафиксирован как `<stage>_failed:<sub_stage>:<reason>`, требует ручного / автоматического recovery либо rollback. **Никакого partial state advancement.**

Это противоположность "best-effort" pattern'у где Celery task мог частично выполниться, оставив flow в неопределённом состоянии (escrow frozen но Transaction не записана, ERID получен но publication не произошла, и т.д.).

### Зачем

1. **Audit trail completeness** — каждый sub-stage оставляет след (Transaction row, status update, structured log).
2. **Recovery without forensics** — явный state позволяет resume с конкретного места без угадывания.
3. **Legal compliance** — если flow остановился до получения ERID, гарантированно НЕ опубликовали без маркировки.
4. **Money safety** — silent partial flows главный источник ledger drift (CRIT-2 в Промте-12). Atomic STOP исключает класс таких багов.

### Sub-stages по этапам (пример — не исчерпывающий)

**Stage 4 (Принятие заявки):** 4a. owner click accept; 4b. `freeze_escrow_for_placement` (lock + balance check + decrement advertiser → increment `platform_account.escrow_reserved`); 4c. `Transaction(type=escrow_freeze)` + `idempotency_key`; 4d. `PlacementRequest.status → escrow`; 4e. `act_placement.html` generated; 4f. notification dispatched. Если 4b succeeded но 4c failed (DB constraint violation) — STOP, escrow rollback, status revert. Не continue к 4d.

**Stage 5 (ОРД регистрация):** 5a. submit creative payload; 5b. receive ERID; 5c. persist ERID на PlacementRequest; 5d. verify ERID format. Если 5a timed out или 5b returned error — STOP. Не continue к publication. Status → `erid_pending` или `erid_failed:<reason>`. Никогда publication без verified ERID.

**Stage 7 (Завершение):** 7a. trigger condition met; 7b. `release_escrow` (advertiser unchanged, owner.earned_rub +788, platform escrow_reserved -1000, +212 commission + service fee); 7c. Transaction × 2; 7d. `act_advertiser.html`; 7e. `act_owner_<status>.html` (по owner.legal_status); 7f. KUDIR records appended; 7g. notifications. Любой из 7b-7g failed → STOP, status `release_failed:<sub_stage>`, PlacementRequest stays in `published`, manual review.

### Implementation hints

- **State machine с явными transitions:** PlacementTransitionService уже задаёт паттерн (Phase 2). Расширить для всех stages, sub-stages как explicit state transitions (не inline mutations внутри одной Celery task).
- **Atomic units:** каждый sub-stage — caller-controlled session boundary с явным commit / rollback.
- **Status enum granularity:** `escrow_freeze_pending`, `escrow_frozen`, `escrow_freeze_failed:<reason>`, `erid_pending`, `erid_received`, `erid_failed:<reason>`, `published`, `release_pending`, `released`, `release_failed:<sub_stage>`. Текущий narrow enum (10 statuses post-Phase-2) недостаточен для full sub-stage tracking. Расширение — Phase 3+ design.
- **Recovery jobs:** Celery beat tasks per `*_pending` status, retry с backoff + max attempts → escalate to admin.
- **Observability:** structured logs с `placement_id`, `stage`, `sub_stage`, `status`, `error_class`, `error_message`, `retry_count`.

### Applies to

- Phase 3 — `LegalComplianceService` каждый из 18 gates atomic, blocker chain explicit.
- Phase 4 — ДС flow sub-stages: gen → notify → sign advertiser → sign owner → activate.
- Phase 5 — ProviderResolution каждый external call atomic, retry/mock fallback explicit.
- Phase 6 — ORD hardening sub-stages.
- Phase 7 — Timeline UI visual representation всех sub-stages, не только 8 главных этапов.
- Серия 15.9 — acceptance infrastructure: version compare → invalidate cache → force re-accept → confirm new acceptance.
- Серия 16.x — payout flow sub-stages (request → admin approve → real bank transfer → KUDIR record).

При дизайне нового сервиса спросить: "если sub-stage X упал, flow STOP или continues to Y?". Default — STOP.

---

## 4. Findings (consolidated, unchanged from rev 3)

| # | Проблема | Критичность | Фаза |
|---|----------|-------------|------|
| 1 | Contracts/Acts в mini_app — экраны есть, навигации в меню нет | High UX | 6 |
| 2 | mini_app рендерит документы с ПД (contract/act detail) | 🔴 ФЗ-152 | 1 ✅ |
| 3 | `/api/legal-profile/*` принимает любой JWT (нет `aud`) | 🔴 ФЗ-152 | 0 ✅ |
| 4 | Нет `placement_status_history` и `PlacementTransitionService` | High | 2 ✅ |
| 5 | `ord_block_publication_without_erid=False` by default | 🔴 ФЗ-38 | 6 |
| 6 | UI не рендерит `scheduled_delete_at` в части экранов | Medium | 7 |
| 7 | `is_test` режет бизнес-логику вместо переключения провайдеров | High | 5 |
| 8 | **Нет единой системы юр. gate'ов на переходах** | 🔴 ФЗ-115/НК/ГК | 3 |
| 9 | Нет supplementary agreement (ДС) на размещение | 🔴 ГК 432 | 4 |
| 10 | `legal_type` compliance (ФЛ/самозанятый/ИП/ООО) не покрыто системно | 🔴 НК | 3 |
| 11 | `ENVIRONMENT` — dead variable | Hygiene | 0 ✅ |
| 12 | Hardcoded URLs, ERID-префиксы, magic numbers | Hygiene | 0 ✅ |

### Findings добавленные после rev 3 (2026-04-28)

| # | Проблема | Критичность | Серия |
|---|----------|-------------|-------|
| 13 | Fee model drift между code (15/85), legal templates (20/80), frontend hardcodes | High | 15.x ✅ partially (15.7) |
| 14 | Bot payout FSM accepts card/phone via `message.text`, plaintext echo + at rest | 🔴 ФЗ-152 | 16.x |
| 15 | `/api/payouts/*` принимает mini_app JWT | 🔴 ФЗ-152 | 16.x |
| 16 | `DocumentUpload.ocr_text` plaintext (10K chars passport OCR) | 🟠 ФЗ-152 | 16.x |
| 17 | `PayoutRequest.requisites` plaintext at rest | 🟠 ФЗ-152 | 16.x |
| 18 | `/api/admin/*` endpoints не pinned к web_portal | 🟡 ФЗ-152 | 16.x |
| 19 | Sub-stage tracking absent — silent partial flows possible | 🔴 архитектура | Phase 3+ (BL-037) |

---

## 5. NEVER TOUCH — требуется явное "ок"

CLAUDE.md запрещает правку без спроса:
`field_encryption.py`, `log_sanitizer.py`, `audit_log.py`, `legal_profile.py`, `contract.py`, `ord_registration.py`.

`audit_middleware.py` — **снят с NEVER TOUCH в Phase 1 PF.4** после refactor in place.

План требует:

| Файл | Фаза | Что | Риск |
|------|------|-----|------|
| `contract.py` | 4 | Добавить `supplementary_agreement` в `ContractType`; FK `parent_contract_id` | Low (additive) |
| `legal_profile.py` | 3 | Возможно добавить `fns_verification_status`, `fns_verified_at`, `egrul_snapshot_at`, `inn_checksum_valid` (если отсутствуют) | Low (additive) |
| `0001_initial_schema.py` | 2, 3, 4, 5 | Новые таблицы/колонки | Ok per CLAUDE.md pre-prod rule |

Перед Phase 3 и Phase 4 — исполнитель СТОП и спрашивает явное "ок" на `contract.py` / `legal_profile.py` edit.

---

## 6. Cross-cutting concerns (применимы к КАЖДОЙ фазе)

Каждая фаза, затрагивающая публичный API / модель / UI, обязана закрыть **все** слои ниже. Чеклист копируется в acceptance каждой фазы с конкретными именами.

### Слой 1 — Repository layer
CLAUDE.md: *"All DB queries go here"*. Inline queries в сервисе запрещены.
- Новая таблица → новый `src/db/repositories/<name>_repo.py`.
- Изменение модели → обновить relevant repo методы (+ тесты).
- Gate-checkers (Phase 3) читают через existing repos, не напрямую через `session.execute(select(...))`.

### Слой 2 — Frontend hooks (`screen → hook → api-module`)
Правило S-46 / S-48, enforced ESLint + grep-guard.
- API-функция: `web_portal/src/api/<domain>.ts` и/или `mini_app/src/api/<domain>.ts` (единственное место с fetch/ky).
- Hook: `web_portal/src/hooks/use<Name>.ts` и/или `mini_app/src/hooks/`. React Query или mutation. Screen импортирует только hook.
- Запрет прямого `import { api }` в screens/components/hooks из `api`.

### Слой 3 — Client-side types
- Pydantic schema → Python side: `src/api/schemas/*.py` + snapshot в `tests/unit/snapshots/` + `tests/unit/test_contract_schemas.py`.
- TypeScript side: `web_portal/src/lib/types.ts` и `mini_app/src/lib/types.ts` — ручная синхронизация (auto-gen вне scope).
- Каждая новая Pydantic-схема → regenerate snapshot: `UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py` → коммитить рядом со схемой.

### Слой 4 — Database indices
- JSONB поля с admin-query — GIN-индекс.
- Composite `(col_a, col_b)` для часто используемых `WHERE a = ? ORDER BY b`.
- Partial index для sparse (`WHERE deleted_at IS NULL`, `WHERE is_test = True`).
- Миграции → `0001_initial_schema.py` (pre-prod rule).

### Слой 5 — Frontend tests
- Playwright специ в `web_portal/tests/specs/`.
- Viewport'ы: **iPhone SE**, **Pixel 5**, **Desktop Chrome 1440x900** (конвенция проекта из `playwright.config.ts`).
- Новый flow → spec. Новый экран → axe-violations check.

### Слой 6 — Mini_app audit (после каждой фазы)
На каждой фазе ответить:
1. Затрагивает ли фаза mini_app? Если нет — OK.
2. Если да — какая именно часть (UI / data / navigation)?
3. ПД проходят через mini_app? Если да — **СТОП**, переделываем по правилу "mini_app never touches ПД".
4. Timeline в mini_app — реализуется в Phase 7 как **read-only компактный** компонент `PlacementTimelineCompact.tsx` (только статусы + schedule, без gates, без financial details, без legal_type info).

### Слой 7 — Sub-stage tracking (BL-037 — добавлено rev 4)
Каждая фаза которая вводит новый flow или модифицирует existing проверяет:
1. Все sub-stages enumerated (не abstracted в "service.do_thing()" единым blackbox).
2. Каждый sub-stage atomic (caller-controlled session, явный commit/rollback).
3. Status enum granularity достаточна для resume after failure.
4. Recovery path documented (Celery beat retry / admin manual / rollback).
5. Observability: structured logs с `stage`, `sub_stage`, `error_class`.

---

## 7. Граф фаз и серий

```
Phase 0 ✅ (env + constants + JWT aud)
   │
   ├──► Phase 1 ✅ (ФЗ-152 guards + mini_app legal strip)
   │
   ├──► Phase 2 ✅ (PlacementTransitionService + status_history)
   │         │
   │         ├──► [Серия 15.x] 🟡 (Centralized Fee Model + Legal Consistency)
   │         │              │
   │         │              ├──► [Серия 16.x] ⏸ (PII Hardening — payouts/admin/bot)
   │         │              │              │
   │         │              │              ├──► Phase 3 ⏸ (Legal Compliance Gates — 18 gates)
   │         │              │              │              │
   │         │              │              │              ├──► Phase 4 ⏸ (Supplementary Agreements / ДС)
   │         │              │              │              │              │
   │         │              │              │              │              └──► Phase 5 ⏸ (Test-mode runtime + admin UI)
   │         │              │              │              │                          │
   │         │              │              │              │                          └──► Phase 6 ⏸ (Contracts/Acts UX + ORD prod)
   │         │              │              │              │                                    │
   │         │              │              │              │                                    └──► Phase 7 ⏸ (UI Timeline + sub-stage events + overlay)
```

Каждая стрелка — stop-point, требующее явное "ок".

**Note:** Серии 15.x и 16.x могут идти параллельно logically (не code-параллельно — one active session rule), порядок их относительно Phase 3 — Marina decision. Default: 15.x → 16.x → Phase 3.

---

# Phase 0 — ✅ DONE (2026-04-25)

**Branch:** `feature/env-constants-jwt-aud` (merged develop+main).

**Что сделано:**
- `ENABLE_E2E_AUTH` flag (replaces `ENVIRONMENT == "testing"` check).
- JWT carries explicit `aud` claim (`mini_app` / `web_portal`).
- Ticket bridge endpoints: `POST /api/auth/exchange-miniapp-to-portal`, `POST /api/auth/consume-ticket`.
- Centralized URLs в `settings.py` (`web_portal_url`, `mini_app_url`, `landing_url`, `api_public_url`, `tracking_base_url`, `terms_url`).
- `STUB-ERID-` prefix в `src/constants/erid.py`.
- 8 hardcoded URLs в `src/` заменены на `settings.*`.
- 4 typo fixes `rekhaborbot.ru → rekharbor.ru` в `src/constants/legal.py`.
- Tests: `test_jwt_aud_claim.py` (9 cases), `test_jwt_rate_limit.py` (2 cases).
- `legacy aud-less JWT → HTTP 426 + WWW-Authenticate: Bearer` (post-Phase-1 PF.2 refinement).
- `audit_middleware.py` refactored in place (PF.4) — снят с NEVER TOUCH.

**Detail:** `reports/docs-architect/discovery/CHANGES_2026-04-25_phase0-env-constants-jwt.md`.

---

# Phase 1 — ✅ DONE (2026-04-25)

**Branch:** `feature/fz152-legal-hardening` (merged develop+main).

**Что сделано:**
- 23 PII endpoints на web_portal-only auth (`legal_profile.py` 7, `contracts.py` 7, `acts.py` 4, `document_validation.py` 5).
- Mini_app legal strip: 20 файлов deleted (5 PII screens + components + api modules + hooks + store + 13 types).
- `OpenInWebPortal` bridge: 4 placeholders + 2 hooks (web_portal `useConsumeTicket`, mini_app `useOpenInWebPortal`).
- `safeRedirect()` allowlist (close open-redirect risk per PHASE1_RESEARCH §1.A.3).
- `POST /api/contracts/accept-rules` carve-out — non-PII, both audiences (FZ-152 scope policy).
- `POST /api/users/skip-legal-prompt` removed (0 calls in 14 days).
- `audit_middleware.py` refactor in place (PF.4) — `request.state.user_id` + `aud` flow.

**Detail:** `reports/docs-architect/discovery/CHANGES_2026-04-25_phase1-fz152.md` (см. CHANGELOG entries).

---

# Phase 2 — ✅ DONE (2026-04-27)

**Branch:** `feature/placement-transition-service` (merged develop+main `9adaef2`).

**Что сделано:**
- `placement_status_history` table — append-only audit trail.
- `PlacementTransitionService.transition()` — strict allow-list state machine.
- `PlacementTransitionService.transition_admin_override()` — explicit reason enum.
- `TransitionMetadata` Pydantic schema (closed model, frozen, Literal enums).
- 22+ placement status mutation sites consolidated через service.
- `PlacementRequestRepository` теперь read-only API (mutation helpers deleted).
- 3 dead code modules removed: `dispute_tasks.py` (120 LOC), `retry_failed_publication`, `process_publication_success`.
- Forbidden-patterns lint extended (17/17): direct `placement.status =`, setattr-style, `published_at` mutation.
- `_sync_status_timestamps` extended: `expires_at +24h` on `pending_owner` (Surprise 5), `failed_permissions` distinguished.
- `_ALLOW_LIST` extended: `escrow → cancelled` (advertiser cancel-after-escrow with 50% refund).
- Schema cleanup: `ord_blocked` removed from `placementstatus` enum.
- Sync dispute resolution path canonical (Decision 11). S-48 violation `disputes.py:706` fixed.
- 9 unit tests for transition service.

**State machine post-Phase-2** (10 statuses):
```
pending_owner → counter_offer | pending_payment | cancelled
counter_offer → pending_owner | pending_payment | cancelled
pending_payment → escrow | cancelled
escrow → published | failed | failed_permissions | refunded | cancelled
published → completed | failed | refunded | cancelled
failed → refunded
failed_permissions → refunded
completed, refunded, cancelled — terminal
```

**Detail:** `reports/docs-architect/discovery/CHANGES_2026-04-27_phase2-merge-and-baseline-fix.md` + предыдущие `CHANGES_2026-04-27_phase2-*.md`.

---

# Серия 15.x — Centralized Fee Model + Legal Consistency rewrite (🟡 IN FLIGHT)

**Origin:** `PLAN_centralized_fee_model_consistency.md` (2026-04-28).

**Why:** Fee model drift между code (15/85), legal templates (20/80), frontend hardcodes (3.5%/6%) обнаружен после Phase 2. Side-quest перед Phase 3.

**Final fee model (LOCKED — source: `src/constants/fees.py`):**
- Topup: user pays `desired × 1.035` (3.5% YooKassa pass-through).
- Placement release: owner 78.8%, platform 21.2% (= 80% × 99.5% / 1.5% service fee из owner share).
- Cancel post-escrow pre-publish: 50/40/10 advertiser/owner/platform.
- Cancel post-publish: 0% refund.

| Промт | Статус | Эффект |
|-------|--------|--------|
| 15.5 | ✅ Deployed | Bot `topup_pay` migration на `YooKassaService.create_topup_payment` |
| 15.6 | ✅ Closed | Read-only legal templates inventory (14 HTML templates) |
| 15.7 | ✅ Deployed | `src/constants/fees.py` + `/api/billing/fee-config` endpoint |
| 15.8 | ✅ Deployed | Legal templates Jinja2 injection + version bump 1.0 → 1.1, `§ 18 (115-ФЗ)` + `§ 19 (юрисдикция)` |
| 15.9 | ✅ Deployed | Acceptance infrastructure — re-accept loop при `CONTRACT_TEMPLATE_VERSION` bump |
| 15.10 | ✅ Deployed (combined с 15.11.5) | Frontend `/fee-config` consume + bot UI cancel scenario fix + middleware fail-closed |
| 15.11 | ✅ Deployed (combined с 15.12) | Dead act-templates wire через `legal_status` — 5 templates routed via `get_act_template(party, legal_status)` |
| 15.11.5 | ✅ Deployed (with 15.10) | Bot handler передавал wrong scenario string (UI lies) — one-line fix; BillingService logic was correct (semantic mismatch was prompt-side) |
| 15.12 | ✅ Deployed (combined с 15.11) | Documentation cleanup — BACKLOG hygiene, PII findings surfaced (BL-041..BL-051), Status overlay aligned |
| 15.13 | ⏸ Deferred | Webhook consolidation 14b — отдельная сессия в billing rewrite plan |

**Acceptance criterion:** после серии — `code ↔ legal templates ↔ frontend` consistent. AST lint forbids hardcoded fees in `src/`, `mini_app/src/`, `web_portal/src/`, `landing/src/`, `src/templates/`. `CONTRACT_TEMPLATE_VERSION = "1.1"` rendered, re-acceptance loop active.

**Sub-stage tracking** (BL-037 applies — особенно к 15.9):
- 15.9 acceptance flow sub-stages: detect version mismatch → invalidate cache → block routes → present accept screen → record acceptance → unblock. Atomic, fail-fast STOP.

---

# Серия 16.x — PII Hardening (⏸ Pending, не начата)

**Origin:** `reports/docs-architect/discovery/PII_AUDIT_2026-04-28.md`.

**Why:** PII audit (read-only, 2026-04-28) выявил CRIT/HIGH/MED findings в payouts, admin endpoints, bot FSM. Phase 1 закрывал legal_profile/contracts/acts (23 endpoints), но pay-out path и admin endpoints в enumeration не попали.

**Findings (записаны как BL-044..BL-051 после 15.12 — см. BACKLOG.md):**

**Группа A — Pin endpoints к web_portal (повтор Phase 1 паттерна):**
- CRIT-2: `/api/payouts/*` принимает mini_app JWT, `requisites` уходит в mini_app heap.
- MED-5: `/api/admin/*` (legal-profiles, users, platform-settings, payouts) через `AdminUser → get_current_user` без `aud` pin.

**Группа B — Encrypt at rest (existing `EncryptedString` infrastructure):**
- HIGH-4: `PayoutRequest.requisites` plaintext в БД.
- HIGH-3: `DocumentUpload.ocr_text` (10K chars passport OCR) plaintext.

**Группа C — Bot inbound surface (architectural):**
- CRIT-1: `payout.py:281-351` принимает 16-digit card / phone через `message.text`, plaintext echo в Telegram chat (line 347), plaintext at rest. Тройной хит. **Architectural decision:** должен ли bot вообще принимать payout requisites? По правилу "mini_app never touches ПД" — bot тоже не должен. Решение → bot payout flow удаляется, web_portal становится единственным местом для payout setup, в bot — кнопка "Открыть в портале" по образцу `OpenInWebPortal`.

**Группа D — Schema response cleanup:**
- MED-6: `UserResponse.first_name/last_name` уходит в referral list (чужие имена).

**LOW (defer to BACKLOG):**
- Dead `LegalProfileStates` (15 states, 0 handlers).
- `mini_app payouts.ts createPayout` loaded gun (exported but unused).
- `log_sanitizer` (11 keys) ↔ Sentry scrub (16 keys) divergence.
- `notify_admins_new_feedback` echoes user-typed feedback text.
- YooKassa webhook stores full payload (over-collection).
- `src/bot/handlers/shared/login_code.py:50` logs one-time login code in plaintext.

**Промт sequence (предварительный):**
- 16.0 — Surface findings as BL entries (BL-038...BL-04X) в BACKLOG. Closes the gap.
- 16.1 — Группа A: pin `/api/payouts/*` + `/api/admin/*` к web_portal-only (Phase 1 pattern, mechanical).
- 16.2 — Группа B: encrypt `PayoutRequest.requisites` + `DocumentUpload.ocr_text` (existing `EncryptedString`).
- 16.3 — Группа C: bot payout flow removal + `OpenInWebPortal` redirect.
- 16.4 — Группа D: `UserResponse` referral leak fix.
- 16.5 — LOW cleanup batch.

**Acceptance criterion:** `mini_app` audit clean, no plaintext PII at rest in payouts/document tables, bot не accepts financial PII, admin endpoints pinned к web_portal.

---

# Phase 3 — Legal Compliance Gates (8-10ч, самая объёмная)

**Branch:** `feature/legal-compliance-gates`

**Prerequisites:** Phase 2 merged ✅. Серия 15.x желательно завершена. **ЯВНОЕ "ок" на правку `legal_profile.py`** (если research покажет что нужно добавить поля).

## 3.A Deep-dive research

Параллельно 3 агента:

### Agent A — legal_profile current structure
> Прочитать `src/db/models/legal_profile.py`, `src/api/routers/legal_profile.py`, `src/api/schemas/legal_profile.py`. Вернуть: (1) все текущие поля LegalProfile, (2) существующий enum legal_type и его значения (individual, self_employed, ie, llc?), (3) какие поля обязательны для каждого legal_type, (4) есть ли поля `fns_verification_status`, `egrul_snapshot_at`, `inn_validated_at`.

### Agent B — Existing gate-like checks scattered
> Найти точечные проверки legal-requirements в коде: `grep -rn "legal_profile\|framework_contract\|is_signed\|contract_signed" src/core/`. Вернуть: какие проверки уже есть (erid, framework contract signed и т.п.), где они вызываются, в какой момент flow.

### Agent C — Financial/payout existing infrastructure
> Прочитать `src/core/services/payout_service.py`, `billing_service.py`, `src/db/models/payout.py`. Вернуть: текущие payout methods (card, sbp, счёт), как связаны с legal_type owner, есть ли валидация реквизитов.

## 3.B Implementation

### 3.B.1 `PlacementGate` enum — 18 точек

`src/core/enums/placement_gate.py`:

**Pre-creation (перед созданием placement):**
- G01_ADVERTISER_LEGAL_PROFILE_COMPLETE
- G02_ADVERTISER_FRAMEWORK_CONTRACT_SIGNED
- G03_ADVERTISER_LEGAL_TYPE_COMPLIANT

**Owner-side (перед добавлением канала — DECLINE если fail):**
- G04_OWNER_LEGAL_PROFILE_COMPLETE
- G05_OWNER_FRAMEWORK_CONTRACT_SIGNED
- G06_OWNER_PAYOUT_METHOD_VALID

**Pre-escrow (перед оплатой, статус → pending_payment):**
- G07_SUPPLEMENTARY_AGREEMENT_SIGNED *(реализация ДС — Phase 4; здесь — заготовка gate'а с TODO и возвратом `fail + reason="phase4 pending"` пока. При Phase 4 gate заработает полностью.)*

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

**BL-037 sub-stage tracking applies:** каждый gate-check atomic, blocker chain explicit. Gate результат как explicit transition event в `placement_status_history.metadata_json`.

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
  - `individual` → валидный паспорт + checksum ИНН; налоговый агент удерживает НДФЛ в payout — flag для Phase 4 billing.
  - `self_employed` → статус НПД в ФНС активен (`fns_verification_status`); G16 обязателен при payout.
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
- Если `placement.is_test` и actor is admin: **не raise**, а сохранить blocker'ы в `placement.pending_gate_resolutions` (JSONB) и вернуть контролируемый результат — runtime pause (Phase 5 строит UI поверх).

### 3.B.5 API: эндпоинт статуса gate'ов
- `GET /api/placements/{id}/gates` → `list[GateResult]` (для UI фазы 5 и 7).

### 3.B.6 Owner channel-add hard precondition (DECLINE)

Hook в `POST /api/channels` (channel add endpoint):
```python
# G04 + G05 + G06 — hard preconditions
gates = await compliance.check_gates_for_user_role(session, user, role="owner")
blockers = [g for g in gates if g.gate in {G04, G05, G06} and not g.passed]
if blockers:
    raise ChannelAddDeclinedError(blockers)  # 403 + remediation URLs
```

UI — на attempt to add channel показывает блок "Чтобы добавить канал, заполните юр. профиль и подпишите договор владельца канала", не позволяет proceed.

### 3.B.7 legal_profile доп. поля (ТОЛЬКО если Agent A покажет отсутствие)
- `fns_verification_status: Enum["unchecked", "active", "inactive"]`
- `fns_verified_at: datetime | None`
- `egrul_snapshot_at: datetime | None`
- `inn_checksum_valid: bool`
- Миграция в `0001_initial_schema.py`.

## 3.C Acceptance

- [ ] Все 18 gate-checkers имеют unit-тесты.
- [ ] Integration: попытка перехода без заполненного legal_profile — `TransitionBlockedError` с G01.
- [ ] Integration: попытка add channel без G04+G05+G06 — `ChannelAddDeclinedError` с remediation URLs.
- [ ] Integration: test-placement (admin) проходит с blocker'ами в `pending_gate_resolutions` (без exception).
- [ ] legal_type-matrix тесты: individual / self_employed / ie / llc — каждый с соответствующими required gates.
- [ ] `GET /api/placements/{id}/gates` отдаёт все applicable gates.
- [ ] Snapshot для `GateResult` schema зафиксирован.
- [ ] **BL-037 acceptance:** каждый gate-check логирует sub-stage event с `placement_id`, `gate_code`, `passed/blocked`, `error_class`.
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
- [ ] **Sub-stage tracking (BL-037):** каждый gate event в `placement_status_history.metadata_json`. Recovery path: admin override (Phase 5) или user remediation.

**STOP → ждать "ок" перед Phase 4.**

---

# Phase 4 — Supplementary Agreements / ДС (4-5ч)

**Branch:** `feature/supplementary-agreements`

**Prerequisites:** Phase 3 merged. **ЯВНОЕ "ок" на правку `contract.py`.**

## 4.A Deep-dive research

Параллельно 2 агента:

### Agent A — Current contract model + service
> Прочитать `src/db/models/contract.py`, `src/core/services/contract_service.py`, `src/api/routers/contracts.py`. Вернуть: (1) все enum-values ContractType, (2) как генерируются рамочные (endpoints, вызовы), (3) поле `parent_contract_id` уже есть?, (4) методы подписи (click, КЭП, sms).

### Agent B — Act generation parallel
> Прочитать `src/db/models/act.py`, `src/core/services/` для act-generation. Вернуть: как генерируется закрывающий акт при завершении placement (template engine, PDF generation). Это модель для ДС генерации.

## 4.B Implementation

### 4.B.1 Расширение `Contract` модели
- В `ContractType` enum добавить `supplementary_agreement`.
- Добавить колонку `parent_contract_id: int | None` FK → contracts.id (самоссылка): `SELF-FK`.
- Добавить `placement_id: int | None` FK → placement_requests.id (только для ДС, для рамочных NULL).
- Миграция в `0001_initial_schema.py`.

### 4.B.2 `SupplementaryAgreementService`
`src/core/services/supplementary_agreement_service.py`:
- `async def generate_for_placement(session, placement) -> Contract`:
  - Создаёт Contract с `contract_type=supplementary_agreement`, `parent_contract_id=<advertiser's framework>`, `placement_id=<id>`, `user_id=<advertiser.id>`, `status=draft`.
  - Template: инкорпорирует условия placement (канал, цена, время, текст, erid, период) + ссылку на рамочный.
  - Аналогично для owner — вторая сущность Contract с тем же `placement_id`, но `parent_contract_id=<owner's framework>`, `user_id=<owner.id>`.
- Двух-стороннее подписание: placement считается "ДС подписано" когда оба Contract получили `status=signed`.

**BL-037 sub-stage tracking:** ДС flow sub-stages: gen advertiser ДС → gen owner ДС → notify both → sign advertiser → sign owner → mark active. Atomic, fail-fast STOP.

### 4.B.3 Hook в placement flow
- При переходе placement в `pending_payment` (после одобрения owner'ом условий) — `PlacementTransitionService` вызывает `supplementary_agreement_service.generate_for_placement()`.
- Gate `G07_SUPPLEMENTARY_AGREEMENT_SIGNED` проверяет существование двух Contract'ов с `placement_id=X, contract_type=supplementary_agreement, status=signed`.

### 4.B.4 API endpoints
- `GET /api/placements/{id}/supplementary-agreements` → оба ДС (advertiser + owner).
- `POST /api/contracts/{id}/sign` — уже есть, работает для ДС тоже (метод `click_accept` для ФЛ/самозанятых, `sms_code` fallback для остальных если КриптоПро не готов — НЕ откладываем, делаем fallback).
- Уведомления: при создании ДС — notification владельцу/рекламодателю.

### 4.B.5 UI (web_portal only per ФЗ-152)
- В `CampaignWaiting.tsx` (статус `pending_payment`): секция "Доп. соглашение — подпишите" с кнопкой перехода на ContractDetail.
- `OwnRequestDetail.tsx`: аналогично.
- Mini_app: НЕ показывает (ДС содержит реквизиты = ПД).

**Templates:** ДС templates пишутся с `_build_fee_context()` Jinja injection (наследует из 15.8 серии — fee model уже централизован).

## 4.C Acceptance

- [ ] Переход placement в `pending_payment` → созданы 2 Contract'а с `contract_type=supplementary_agreement`.
- [ ] G07 gate: оба не подписаны → fail; оба подписаны → pass.
- [ ] Integration: не подписав ДС нельзя перейти в escrow.
- [ ] UI: advertiser видит кнопку "Подписать ДС" на CampaignWaiting.
- [ ] PDF generation работает (можно скачать ДС).
- [ ] **BL-037:** ДС flow sub-stages logged.
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
- [ ] **Sub-stage tracking (BL-037):** каждый sub-stage event logged в `contract.metadata_json`.

**STOP → ждать "ок" перед Phase 5.**

---

# Phase 5 — Test-mode runtime + admin UI (5-7ч)

**Branch:** `feature/test-mode-runtime`

**Prerequisites:** Phase 4 merged.

## 5.A Deep-dive research

Параллельно 3 агента:

### Agent A — Channel repository + current is_test usage
> Прочитать `src/db/repositories/channel_repo.py`, все места где используется `channel.is_test`, `User.is_test`. Вернуть: (1) как сейчас фильтруются каналы для advertiser'а, (2) где `is_test` меняет логику (что конкретно bypass'ится), (3) структура admin-role check.

### Agent B — Existing tests fixtures + factories
> Прочитать `tests/conftest.py`, найти `tests/factories/`, `tests/fixtures/`, `tests/unit/**/conftest.py`. Вернуть: (1) есть ли factory_boy / pytest fixtures для PlacementRequest, Channel, User, (2) есть ли готовые сценарии для mock external services (ORD response, YooKassa webhook), (3) как организован единый источник истины для mock-данных.

### Agent C — External service providers
> Прочитать `src/core/services/ord_provider.py`, `stub_ord_provider.py`, `src/utils/telegram/sender.py`, `src/core/services/yookassa_service.py` (если есть). Вернуть: (1) есть ли уже provider pattern у каждого, (2) как выбирается реализация (env var? factory?), (3) список внешних сервисов требующих mock: ORD, Telegram Bot API (публикация), YooKassa, КриптоПро, ФНС ("Мой налог"), ЕГРЮЛ/ЕГРИП.

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
- Frontend: channel-selector эндпоинт автоматически возвращает отфильтрованный список. Для admin — в UI добавлен toggle "Показать только тестовые".

### 5.B.3 Admin-only `is_test` галочка
- `PlacementCreateRequest` — добавить `is_test_run: bool = False`.
- Backend: если `is_test_run and not user.is_admin` → 403.
- Backend: если `is_test_run=True` → channel-selector фильтр `Channel.is_test == True only`.
- Frontend (web_portal, NOT mini_app): в campaign-creation wizard добавить `<IsTestRunToggle />` — виден только если `user.is_admin`. При включении — channel dropdown rerender'ится с test-only.

### 5.B.4 Provider pattern + admin override API
Каждый внешний провайдер получает единый интерфейс:
```python
class ExternalProvider(Protocol):
    async def call(self, request: ProviderRequest, placement_id: int) -> ProviderResult: ...
```
Провайдеры:
- `OrdProvider` (`RealYandexOrdProvider` | `StubOrdProvider`)
- `TelegramPublisher` (`RealTelegramPublisher` | `SandboxTelegramPublisher` — отправка в `settings.sandbox_telegram_channel_id`)
- `PaymentProvider` (`RealYookassaProvider` | `MockPaymentProvider`)
- `ContractSigner` (`RealKepSigner` | `ClickSimulationSigner` | `SmsCodeSigner` — fallback для pre-КриптоПро эры)
- `FnsProvider` (`RealFnsProvider` | `MockFnsProvider`)
- `EgrulProvider` (`RealEgrulProvider` | `MockEgrulProvider`)

**BL-037:** каждый provider call atomic, retry/mock fallback explicit.

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
- В `placement.pending_gate_resolutions` (JSONB): `[{"gate": "G08_ERID_REGISTERED", "reason": "ord_unreachable", ...}]`.
- Новый endpoint:
  ```
  POST /api/admin/placements/{id}/gates/{gate_code}/resolve
  body: {
    action: "retry" | "mock",
    mock_fixture_id?: string   // id fixture из tests/factories/
  }
  ```
- `retry`: повторный вызов real provider (с соответствующим provider-switch).
- `mock`: загружает fixture из `tests/factories/*` через helper. Применяет результат, перезапускает gate-check, если pass → продолжает flow.

### 5.B.6 Mock fixtures через test infrastructure
- НЕ создаём отдельный каталог `src/mocks/`.
- Создаём модуль `src/core/testing/fixture_loader.py` (имя намеренно содержит "testing" — это scope):
  ```python
  def list_fixtures_for_gate(gate: PlacementGate) -> list[FixtureMetadata]: ...
  def load_fixture(fixture_id: str) -> dict: ...
  ```
- Эти функции читают из `tests/factories/` / `tests/fixtures/` (путь относительно project root).
- Важное: `tests/` остаётся test directory; модуль `fixture_loader` импортирует оттуда только при runtime admin override (не для prod flow).
- CI: для prod build убираем `tests/` из docker image — значит runtime override доступен **только в dev/test docker сборке**. В prod admin UI показывает только кнопку "retry", mock кнопка недоступна.

### 5.B.7 Admin UI для gate resolution
- `web_portal/src/screens/admin/PlacementGatesPanel.tsx`:
  - Список placement'ов с `pending_gate_resolutions`.
  - Для каждого gate: описание проблемы + remediation_url + 2 кнопки:
    - **"Выполнить реально"** — `POST ... /resolve body={action:retry}`.
    - **"Подтянуть mock"** — выпадашка fixture'ов (из `GET /api/admin/fixtures?gate={code}`) + кнопка apply.
- Встроить в CampaignWaiting/OwnRequestDetail для admin-просмотра: badge "N gates pending" + ссылка на панель.

## 5.C Acceptance

- [ ] Advertiser не видит test-каналы; admin видит всё.
- [ ] Non-admin не может создать placement с `is_test_run=True`.
- [ ] Closed-loop mismatch → 422.
- [ ] Integration: test-placement → провайдеры все stub/mock; real-placement → провайдеры все real.
- [ ] Gate failure в test-mode → placement в `pending_gate_resolutions`; admin через API resolve(mock) → placement продвигается.
- [ ] Fixture loader: та же factory что и в pytest.
- [ ] В production docker image `tests/` отсутствует → admin UI не показывает mock кнопку.
- [ ] Playwright: admin gate-resolution flow desktop + mobile.
- [ ] **BL-037:** каждый provider call event logged. Sub-stage status enum granularity.
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
> Прочитать `mini_app/src/App.tsx`, `screens/advertiser/AdvMenu.tsx`, `screens/owner/OwnMenu.tsx`, `screens/common/Cabinet.tsx`. Вернуть: все пункты меню, их иконки, порядок. Определить оптимальное место для "Документы" с badge'ем.

### Agent B — Current ERID rendering + prod-block logic
> Прочитать `src/core/services/publication_service.py`, `_build_marked_text`, `web_portal/src/screens/advertiser/campaign/CampaignWaiting.tsx`, `CampaignPublished.tsx`. Вернуть: (1) текущая логика ERID-проверки, (2) где ERID визуализируется, (3) как `settings.ord_provider` будет влиять на реальный блок.

## 6.B Implementation

### 6.B.1 mini_app документы как badge + deep-link
- `mini_app/src/api/client.ts` (или где ax/ky инстанс) — оставляем, но без contracts/acts endpoints (уже удалены в Phase 1).
- Backend: новые lightweight endpoints:
  - `GET /api/contracts/unread-count` → `{count: N}`
  - `GET /api/acts/unread-count` → `{count: N}`
  - (оба без ПД в response)
- Компонент `mini_app/src/components/DocumentsBadge.tsx`:
  - Показывает сумму unread contracts + acts.
  - onClick → `OpenInWebPortal` (`target=/documents` — новый "landing" экран в web_portal со списками contracts+acts).
- В `AdvMenu.tsx` и `OwnMenu.tsx` добавить пункт "Документы" с `<DocumentsBadge />`. `Cabinet.tsx` аналогично.

### 6.B.2 Web_portal `/documents` landing
- `web_portal/src/screens/common/DocumentsHub.tsx`:
  - Две вкладки: "Договоры" / "Акты".
  - Переиспользует существующие `ContractList`, `MyActsScreen` (уже есть в web_portal).

### 6.B.3 ORD production hardening
- `src/config/settings.py`:
  - `ord_provider: Literal["stub", "yandex", "vk", "ozon"] = "stub"`.
  - **Удалить** `ord_block_publication_without_erid` (замена — детерминированная логика).
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
- UI: в `CampaignWaiting.tsx` секция "ОРД" — убираем вручную; всё видно через Timeline (Phase 7) как event.

### 6.B.4 КЭП fallback (чтобы не blocker для pre-launch)
- `ContractSigner` провайдер (из Phase 5) имеет три реализации:
  - `ClickSimulationSigner` — для `individual`/`self_employed` (click accept юридически достаточно).
  - `SmsCodeSigner` — для `ie`/`llc` (enhanced, SMS code на зарегистрированный номер) — **временный fallback** до интеграции КриптоПро.
  - `RealKepSigner` — когда подключен реальный КриптоПро (отдельный тикет вне плана, но интерфейс готов).
- Сервис `ContractService.sign` выбирает метод по `legal_type` пользователя + `signature_method` в запросе + флага `settings.kep_available`.

## 6.C Acceptance

- [ ] mini_app: в AdvMenu и OwnMenu виден пункт "Документы" с badge.
- [ ] Клик на "Документы" → web_portal `/documents` с залогиненным пользователем.
- [ ] `settings.ord_provider=yandex` + placement.erid=None → `PublicationBlockedError`.
- [ ] `settings.ord_provider=stub` + is_test=True + erid=None → публикация с "[ТЕСТОВАЯ ПУБЛИКАЦИЯ]".
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

# Phase 7 — UI Timeline + sub-stage events + educational overlay (3-4ч)

**Branch:** `feature/placement-timeline-ui`

**Prerequisites:** Phase 6 merged.

**BL-037 implementation:** это фаза где sub-stage tracking visualization landed. Timeline displays not only 8 main stages but all sub-stages including failure events.

## 7.A Deep-dive research

Параллельно 2 агента:

### Agent A — Existing timeline-like components
> Найти в `web_portal/src/` и `mini_app/src/` компоненты с ключами `Timeline`, `Stepper`, `History`, `Status`. Вернуть: что есть, какой уровень переиспользуемости, tailwind/CSS conventions в проекте.

### Agent B — Schedule field rendering audit
> В `web_portal/src/screens/advertiser/campaign/CampaignWaiting.tsx`, `CampaignPublished.tsx`, `_shell.tsx`, `screens/owner/OwnRequestDetail.tsx` найти все рендеры `final_schedule`, `proposed_schedule`, `published_at`, `scheduled_delete_at`, `expires_at`. Таблица: компонент × поле × статус (в каком статусе рендерится).

## 7.B Implementation

### 7.B.1 Backend: единый timeline endpoint
`GET /api/placements/{id}/timeline` (уже есть skeleton из Phase 2) — вернуть агрегированный поток событий:
- Status transitions (из `placement_status_history`, Phase 2).
- **Sub-stage events** (BL-037 — из metadata_json).
- Scheduled events (из timestamp-полей): `final_schedule`, `scheduled_delete_at`, `expires_at`.
- Gate events (из Phase 3): "G08 ERID registered at T", fail/pass/resolved by admin.
- Контракты: создан / подписан (advertiser → owner).
- ДС events (Phase 4).

Response: `list[TimelineEvent]` с полями `timestamp`, `event_type`, `actor`, `description`, `status_meta`.

### 7.B.2 Frontend компонент `<PlacementTimeline />`
- `web_portal/src/components/placement/PlacementTimeline.tsx`:
  - Vertical stepper.
  - Event types: `status_transition`, `sub_stage_passed`, `sub_stage_failed`, `gate_passed`, `gate_failed`, `gate_resolved_admin_mock`, `scheduled_publication`, `scheduled_deletion`, `contract_signed`, `act_signed`, `supplementary_signed`, `erid_received`, `erid_failed`, ...
  - Цветовое кодирование: completed / current / scheduled / blocked (gate failure or sub-stage failure).
  - Responsive: на mobile horizontal scroll или compact vertical.

### 7.B.3 Educational overlay для admin
- Если `placement.is_test and user.is_admin` — каждому событию timeline добавляется info-callout:
  - "В production на этом шаге вызывается YooKassa webhook → freeze_escrow Celery task → ..."
  - Тексты в `src/core/constants.py::TIMELINE_EDUCATIONAL_NOTES` (enum-key → текст).
- Non-admin или non-test placement: overlay не рендерится.

### 7.B.4 Интеграция в экраны + schedule gap fixes
- `CampaignWaiting.tsx` — добавить `<PlacementTimeline />` ниже основной информации. Убедиться что `scheduled_delete_at` рендерится в статусе `escrow` (через Timeline, не inline) — gap из findings закрыт.
- `CampaignPublished.tsx` — inline-таймлайн (если был) заменить на компонент.
- `OwnRequestDetail.tsx` — добавить Timeline.
- Все inline-ERID-блоки удалить: ERID только как event в Timeline.

### 7.B.5 Mini_app compact timeline
- `mini_app/src/components/PlacementTimelineCompact.tsx` — read-only компактный компонент:
  - Только status transitions + schedule events.
  - Sub-stage events — да, но только их `event_type` без financial/legal_type details.
  - Без gates content (admin-only).
  - Без financial details.

### 7.B.6 Playwright tests
- `placement-timeline.spec.ts` — на iPhone SE, Pixel 5, Desktop Chrome.
- Проверка sub-stage events рендерятся.
- Проверка educational overlay для admin (role switch).
- Проверка всех schedule-полей рендерятся как events.

## 7.C Acceptance

- [ ] Timeline виден на CampaignWaiting, CampaignPublished, OwnRequestDetail.
- [ ] **Sub-stage events рендерятся** — не только 8 главных этапов (BL-037 visualization done).
- [ ] `scheduled_delete_at` рендерится в статусе `escrow` (как event).
- [ ] Admin в test-placement видит educational overlay, обычный user — нет.
- [ ] Gate failure/resolution — отдельный event type в timeline.
- [ ] Mini_app: compact timeline без legal/financial.
- [ ] Playwright: mobile + desktop — green.
- [ ] `make lint`, `make test`, `make typecheck` — pass.
- [ ] `CHANGES_<date>_phase7-timeline-ui.md` + `CHANGELOG.md`.
- [ ] `docker compose up -d --build nginx api`.

### 7.D Cross-cutting checklist
- [ ] **Repo:** aggregator-endpoint переиспользует existing repos:
  - `PlacementStatusHistoryRepo.list_by_placement` (P2)
  - `ContractRepository.list_supplementary_for_placement` (P4)
  - `ActRepository.list_by_placement` — новый метод.
  - Новый **сервис-агрегатор** `PlacementTimelineService.build_timeline(placement_id) -> list[TimelineEvent]` собирает все источники и сортирует по времени. Включая sub-stage events из metadata_json.
- [ ] **Hooks:**
  - web_portal: `usePlacementTimelineEvents(placementId)` — заменяет/обёртка `usePlacementTimeline` из P2.
  - mini_app: `usePlacementTimelineCompact(placementId)` — упрощённая версия.
- [ ] **API modules:**
  - web_portal: `api/placements.ts::getTimelineEvents(id)`.
  - mini_app: `api/placements.ts::getTimelineCompact(id)` — отдельный эндпоинт `GET /api/placements/{id}/timeline/compact` возвращает subset без legal_type/financial данных.
- [ ] **Types (Python):** `TimelineEvent`, `TimelineEventType` enum (включая sub-stage event types), `TimelineCompactResponse` (для mini_app) + snapshots.
- [ ] **Types (TS):** те же в обоих `types.ts`; mini_app получает narrow subset.
- [ ] **Indices:** N/A (переиспользуем созданные в P2, P3, P4).
- [ ] **Frontend tests:**
  - Playwright `web_portal/tests/specs/placement-timeline.spec.ts` — desktop + mobile, все event types рендерятся.
  - Playwright `placement-timeline-admin-overlay.spec.ts` — admin видит educational callouts, non-admin нет.
  - Playwright `placement-timeline-compact-miniapp.spec.ts` — compact timeline без legal/financial.
  - Playwright `placement-timeline-sub-stages.spec.ts` — **sub-stage events рендерятся** (BL-037 acceptance).
- [ ] **Mini_app audit:** `PlacementTimelineCompact.tsx` — новый компонент, показывает только status transitions + schedule events + sub-stage event types (без content). Gates и financial details отсутствуют. ПД-утечка исключена.

**STOP → итоговый merge.**

---

## 8. Финальный merge и удаление плана

После всех 8 фаз + серий 15.x + 16.x:

1. Все feature-ветки смержены в `develop` через `--no-ff`.
2. `git checkout develop && git pull`.
3. Убедиться: `make lint && make test && make typecheck` — pass.
4. Прогнать Playwright полностью: `cd web_portal && npx playwright test`.
5. `git checkout main && git pull`.
6. `git merge develop --no-ff -m "chore(main): merge develop — legal gates + transition service + test-mode runtime + fee model + PII hardening (v4.4.0)"`.
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

---

## 9. Что НЕ делаем (и почему)

- **Отдельный `src/mocks/`** — моки и так в `tests/`, переиспользуем.
- **SQLAlchemy event-hook на status** — магия, ломается на Celery/bulk. Используем explicit transition function (Phase 2 done).
- **`run_mode` enum** — лишняя сущность; `is_test` достаточно.
- **Runtime правка `audit_middleware.py`** — снято с NEVER TOUCH в Phase 1 PF.4 (refactor in place done).
- **`sandbox_step` отдельный режим** — runtime pause происходит естественно на gate-failure; явный step-mode не нужен.
- **Миграция legacy placement в `placement_status_history`** — pre-prod, БД пересоздаётся; history начнёт заполняться с момента listener'а (Phase 2 done).
- **Реальные интеграции (ОРД/КриптоПро/Мой налог)** — отдельные тикеты; план готовит архитектуру под них (provider pattern), но фактические контракты с провайдерами вне scope.
- **`test.fixme(true, ...)` Playwright BL-001/002/003** — остаются как есть, deferred per BACKLOG.
- **GitHub CI / Actions** — billing permanently inactive (BL-017 ACCEPTED). Real CI = `make ci-local`.
- **Staging environment** — нет staging.
- **Force-push, rebase, squash на feature branches** — preserve history.
- **Best-effort partial flows** — BL-037 запрещает; sub-stage failures должны STOP, не continue.

---

## 10. Quick navigation

- Текущее состояние: см. **Status overlay** в начале.
- Что делать дальше: серия 15.x → 15.8 (legal templates Jinja injection).
- Что после серии 15.x: серия 16.x (PII hardening) или Phase 3 — Marina decision.
- BL inventory: `reports/docs-architect/BACKLOG.md` (36 entries).
- Recent changes: `CHANGELOG.md [Unreleased]` + `reports/docs-architect/discovery/CHANGES_*.md`.
- PII findings (open): `reports/docs-architect/discovery/PII_AUDIT_2026-04-28.md`.
- Серия 15.x план: `PLAN_centralized_fee_model_consistency.md`.
