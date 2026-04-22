# CHANGES 2026-04-21 — FIX_PLAN_06 §§6.1–6.7 finish (tests + guards + CI + docs)

## Scope

Closes the remaining sub-sections of
`reports/20260419_diagnostics/FIX_PLAN_06_tests_and_guards.md` that were not
shipped by the S-47 contract-guards or S-48 grep-guards sprints:

- §6.1 — (done earlier as Variant B); **added CI integration** via
  `.github/workflows/contract-check.yml`.
- §6.2 — Playwright E2E deep-flow pack.
- §6.3 — frontend `tsc --noEmit` in CI.
- §6.4 — (done earlier); wired into `contract-check.yml`.
- §6.5 — unit & integration tests for AdminPayouts.
- §6.6 — regression tests for unified placement PATCH.
- §6.7 — docs: CLAUDE.md «API Conventions» + `web_portal/README.md`.

No changes to `src/`, `mini_app/src/`, `web_portal/src/`, `landing/src/`.
All work lives under `tests/`, `.github/workflows/`, `CLAUDE.md`,
`web_portal/README.md`, `CHANGELOG.md`, and this discovery report.

## Affected files

### New — tests

| File | Tests | Purpose |
|---|---:|---|
| `tests/unit/api/__init__.py` | — | package marker |
| `tests/unit/api/test_admin_payouts.py` | 9 | router contract for admin payouts (§6.5 unit) |
| `tests/unit/api/test_placements_patch.py` | 11 | unified PATCH action dispatch (§6.6) |
| `tests/integration/test_payout_lifecycle.py` | 4 | approve/reject lifecycle on real Postgres (§6.5 integration) |
| `web_portal/tests/specs/deep-flows.spec.ts` | 7 + 3 fixme | Playwright deep-flow pack (§6.2) |

Total new pytest coverage: **24 tests** (9 + 11 + 4). All green.

### New — CI

| File | Purpose |
|---|---|
| `.github/workflows/contract-check.yml` | grep-guards + contract-drift snapshots + API unit tests |
| `.github/workflows/frontend.yml` | `tsc --noEmit` matrix — web_portal / mini_app / landing |

### New — docs

| File | Purpose |
|---|---|
| `web_portal/README.md` | API conventions + development commands + CI map |

### Modified

| File | Change |
|---|---|
| `CLAUDE.md` | +2 sections («API Conventions», «Contract drift guard») inserted before «Component Inventory» |
| `CHANGELOG.md` | `[Unreleased]` → new «FIX_PLAN_06 §§6.1–6.7 finish» block |

## §6.5 — AdminPayouts (unit + integration)

### Unit layer: `tests/unit/api/test_admin_payouts.py` (9 tests)

Isolates the router from the service by `unittest.mock.patch` on
`src.core.services.payout_service.payout_service.approve_request /
reject_request`. `get_current_admin_user` и `get_current_user` подменяются
через `app.dependency_overrides`; `get_db_session` возвращает
`MagicMock` со `session.get = AsyncMock(return_value=None)` (в роутере
`session.get(User, payout.owner_id)` используется для enrich'а
`owner_username`, None допустим).

Scenarios:

| # | Test | Expected |
|---|---|---|
| 1 | `test_advertiser_gets_403` | non-admin GET /api/admin/payouts → 403 |
| 2 | `test_anonymous_gets_401` | unauthenticated → 401 (или 403) |
| 3 | `test_approve_returns_paid_response` | 200 + `AdminPayoutResponse` сериализован, `admin_id=9001`, `status=paid` |
| 4 | `test_approve_already_finalized_returns_400` | `ValueError('... already finalized ...')` → 400 |
| 5 | `test_approve_missing_returns_404` | `ValueError('... not found')` → 404 |
| 6 | `test_reject_without_body_returns_422` | POST без тела → 422 |
| 7 | `test_reject_with_empty_reason_returns_422` | POST `reason=""` → 422 |
| 8 | `test_reject_happy_path` | 200 + `status=rejected`, `rejection_reason` прокинут в сервис |
| 9 | `test_reject_already_finalized_returns_400` | повторный reject → 400 |

### Integration layer: `tests/integration/test_payout_lifecycle.py` (4 tests)

Проблема: `PayoutService.approve_request / reject_request` открывают
собственные сессии через `async_session_factory` и не принимают
session на вход. Чтобы протестировать финансовые инварианты на реальной
Postgres-схеме, фикстура `bound_factory` создаёт sessionmaker,
привязанный к `test_engine` (testcontainers), и патчит
`async_session_factory` в обоих модулях-пользователях:

```python
patch.object(session_module, "async_session_factory", factory),
patch.object(payout_service_module, "async_session_factory", factory),
```

Транзакции сервиса настоящие (commit в базу), поэтому autouse fixture
`_cleanup_after_test` выполняет
`TRUNCATE TABLE transactions, payout_requests, platform_account, users
RESTART IDENTITY CASCADE` после каждого теста. Schema живёт до конца
testcontainers-сессии.

Инварианты:

| Test | Assertions |
|---|---|
| `test_approve_moves_pending_to_paid` | `status=paid`, `admin_id=admin_id`, `processed_at is not None`, `platform_account.payout_reserved == 0` |
| `test_approve_on_paid_raises` | повторный approve → `ValueError('already finalized')` |
| `test_reject_moves_pending_to_rejected_and_refunds` | `status=rejected`, `rejection_reason` сохранён, `user.earned_rub == gross` |
| `test_reject_requires_unfinalized` | reject уже paid → `ValueError('already finalized')` |

**Deviation от плана:** план упоминал `total_payouts` в `PlatformAccount` —
фактически `platform_account_repo.complete_payout` (S-42) обновляет
только `payout_reserved`. Тест закрепляет текущее поведение и
содержит комментарий с ссылкой на спринт.

## §6.6 — Unified placement PATCH regression (`tests/unit/api/test_placements_patch.py`)

Полная регрессия на `PATCH /api/placements/{id}`, заменивший legacy
`POST /accept|/reject|/counter|/pay|/cancel` в S-44. 11 тестов:

| Action | Тесты |
|---|---|
| `accept` | owner accepts → 200 + `pending_payment`; advertiser accepts → 403 |
| `reject` | owner + reason_text → 200 с передачей reason; owner без reason → literal `"rejected"` |
| `counter` | owner + price → `owner_counter_offer(..., Decimal('2000'))`; без price → 400 |
| `pay` | advertiser на `pending_payment` → 200 + `escrow`; advertiser на `pending_owner` → 409 |
| `cancel` | advertiser → 200 + `cancelled`; owner → 403 |
| — | неизвестный placement_id → 404 |

Моки на трёх уровнях (`PlacementRequestRepository`, `TelegramChatRepository`,
`PlacementRequestService`) через `patch("src.api.routers.placements.*")`.
`_make_placement` и `_make_channel` строят `SimpleNamespace`, совместимые с
`PlacementResponse.model_validate(p)` (from_attributes=True).

## §6.2 — Playwright deep-flow pack (`web_portal/tests/specs/deep-flows.spec.ts`)

7 активных сценариев + 3 скаффолда `test.fixme` (недостижимы без реального
Telegram/ЦС). Стратегия: предпочитать `request.{get,post,patch}` (API-level)
вместо DOM-селекторов, чтобы тесты не ломались при UI-перекрасках.

Активные:
1. Accept rules — POST /api/legal-profile/rules.
2. Campaign wizard navigation — category → channels → format → text → terms.
3. Channel settings PATCH — owner изменяет price, GET возвращает новое.
4. Placement lifecycle — advertiser получает pending, owner accepts,
   advertiser платит (через unified PATCH).
5. Payouts list — owner + admin + 403 для advertiser.
6. Top-up intent — POST /api/billing/topup (confirmation_url есть).
7. Review on published — POST /api/reviews на published-placement из seed.

Скаффолды:
- Dispute round-trip — требует escrow + disputable window ≤48h в seed.
- Channel add via bot — требует реального Telegram Bot API
  (`get_chat_administrators`).
- KEP подпись — требует удостоверяющий центр.

## §6.3 — Frontend typecheck in CI (`frontend.yml`)

Матрица из трёх фронтов. `web_portal` и `mini_app` используют
`tsc -b` внутри `npm run build`; в CI выделили отдельный шаг
`npx tsc --noEmit -p tsconfig.json` для быстрой обратной связи (без
`vite build`). `landing` экспортирует `npm run typecheck` → `tsc
--noEmit` — используется как есть.

Кэширование: `actions/setup-node@v4` с `cache: npm` и
`cache-dependency-path: ${{ matrix.dir }}/package-lock.json`.

## §6.1 + §6.4 — CI integration (`contract-check.yml`)

Один job запускает три независимых гарда:

1. `bash scripts/check_forbidden_patterns.sh` — §6.4 grep-guards (7
   паттернов).
2. `poetry run pytest tests/unit/test_contract_schemas.py --no-cov` —
   §6.1 Variant B snapshot-тесты для 8 Pydantic-схем.
3. `poetry run pytest tests/unit/api/ --no-cov` — §6.5 + §6.6 unit.

Триггеры: `pull_request` + `push` на `develop` и `main`. `ci.yml.disabled`
специально не включался — решение по его судьбе остаётся за
оператором, но contract-check и frontend workflow теперь работают
независимо.

## §6.7 — документация

### CLAUDE.md — два новых раздела перед «Component Inventory»

- **«API Conventions (FIX_PLAN_06 §6.7)»** — формализованное правило
  `screen → hook → api-module`, трёхслойная защита:
  - ESLint `no-restricted-imports` (S-46)
  - `scripts/check_forbidden_patterns.sh` (S-48)
  - `.github/workflows/contract-check.yml` (§6.1 + §6.5 + §6.6)
  - процедура добавления endpoint'а (4 шага).
- **«Contract drift guard (FIX_PLAN_06 §6.1 Variant B)»** — описание
  snapshot-инструмента, команда регенерации
  `UPDATE_SNAPSHOTS=1 poetry run pytest tests/unit/test_contract_schemas.py`.

### web_portal/README.md (новый)

Структура директории, правила API conventions с примерами кода (api-модуль
→ hook → screen), команды разработки (`npm run dev`, `npm run build`,
`npm run lint`, tsc, `make -C .. test-e2e`), карта CI workflow'ов.

## Validation (run on this commit)

```bash
$ bash scripts/check_forbidden_patterns.sh
… 7 checks … OK: 7 check(s) passed — no forbidden patterns detected.

$ poetry run pytest tests/unit/api/ tests/unit/test_contract_schemas.py \
    tests/integration/test_payout_lifecycle.py --no-cov -q
tests/unit/api/test_admin_payouts.py .........        [ 27%]
tests/unit/api/test_placements_patch.py ...........   [ 60%]
tests/unit/test_contract_schemas.py .........         [ 87%]
tests/integration/test_payout_lifecycle.py ....       [100%]
============================== 33 passed in 8.80s ==============================

$ poetry run ruff check tests/unit/api/ tests/integration/test_payout_lifecycle.py
All checks passed!

$ cd web_portal && npx tsc --noEmit -p tests/tsconfig.json
(exit 0, no output)
```

Ruff / mypy / contract-snapshot baselines для `src/` не тронуты — только
добавлены новые тесты.

## Known deviations from the original plan

- **§6.1 Variant A не выполнен.** План предлагал две альтернативы
  (A — openapi-typescript codegen в `web_portal/src/lib/types/api-generated.ts`;
  B — pytest snapshot по `.model_json_schema()`). Реализован Variant B
  (закрыт в S-47 contract-guards); Variant A требует рефакторинга
  импортов ручных TS-типов в двух фронтендах и откладывается.
- **§6.5 expected 409 для already-finalized → фактически 400.** Роутер
  `src/api/routers/admin.py:1146-1149` мэппит `ValueError('...
  already finalized ...')` на 400 (не 409). Тесты закрепляют текущий
  контракт; смена на 409 — отдельная задача с breaking-change для
  frontend'ов.
- **§6.2 deep flows частично.** Пункты, требующие реального Telegram или
  ЦС, скаффолдены как `test.fixme` — закрыть их можно только в
  отдельном спринте с mock'ами нужных внешних систем.

## Next steps (deferred)

- Variant A codegen для api-generated.ts (1–2 дня рефакторинга TS-типов).
- Dispute-round-trip E2E — нужен fixture в `scripts/e2e/seed_e2e.py`.
- Channel-add Telegram flow — нужна mock-ообёртка
  `get_chat_administrators`.

🔍 Verified against: 803aec0 (main @ start of sprint) | 📅 Updated: 2026-04-21
