# Промт 15.7 — синхронизация документации и UI с фактическими ставками

🔍 Verified against: HEAD on `main` (after centralized fee config commit 72c7099)
📅 Updated: 2026-04-28T00:00:00Z

## Что и зачем

Код (`src/constants/fees.py`) с момента коммита 72c7099 уже соответствует
**Промту 15.7**:

- Topup: 3,5% YooKassa pass-through (`YOOKASSA_FEE_RATE = 0.035`),
  платформа зарабатывает 0.
- Placement release: 20% валовая комиссия + 1,5% сервисный сбор из доли
  владельца (`PLATFORM_COMMISSION_RATE = 0.20`,
  `OWNER_SHARE_RATE = 0.80`, `SERVICE_FEE_RATE = 0.015`) → эффективно
  21,2% / 78,8%.
- Cancel `after_confirmation` (post-escrow, pre-publish): 50 / 40 / 10
  (`CANCEL_REFUND_*_RATE`).

Однако документация, агентские промпты, frontend-экраны и часть
docstring'ов всё ещё использовали v4.2-модель (15% / 85%). Этот PR
устраняет рассинхрон.

## Принцип формул вместо хардкода

В местах применения никаких `0.788` / `0.212` / "78,8%" не оставлено.
Везде вычисляется из gross-констант через хелперы:

- Python: `format_rate_pct()` + `OWNER_NET_RATE` / `PLATFORM_TOTAL_RATE`
  добавлены в `src/constants/fees.py`.
- TypeScript: `computePlacementSplit()` + `formatRatePct()` добавлены в
  `mini_app/src/lib/constants.ts`, `web_portal/src/lib/constants.ts`,
  `landing/src/lib/constants.ts` — каждый фронт держит собственный
  набор, синхронизированный с Python.

Это единственное место, где задаются числа — и единственное место,
где их предстоит менять при будущем тарифном пересмотре.

## Затронутые файлы

### Active docs (project memory / agent instructions)

- `CLAUDE.md` — раздел Payments полностью перезаписан под Промт 15.7,
  с явной отсылкой к `src/constants/fees.py` как источнику правды.
- `QWEN.md` — секция «Financial Constants v4.2» переименована в
  «Financial Constants (Промт 15.7, 28.04.2026)»; таблица v4.2 помечена
  как историческая; `release_escrow` в Service Contracts заменён на
  формульный псевдокод; `profit_accumulated` в PlatformAccount теперь
  показывает 21,2%.
- `README.md` — Financial Model переписана под Промт 15.7; таблица
  ставок расширена до 6 строк (gross commission / service fee /
  platform total / owner net / topup / cancel / payout).
- `.qwen/agents/backend-core.md` — описание агента и правило по
  комиссиям обновлены (старое «15/85» удалено).
- `.qwen/agents/docs-architect-aaa.md` — правило финансов
  переформулировано через Промт 15.7.

### docs/AAA reference set

- `docs/AAA-01_ARCHITECTURE.md` — «Financial Model» разворачивается на
  10 000 ₽: видна gross-комиссия 2 000 ₽, service_fee 120 ₽, итого
  платформа 2 120 ₽ / владелец 7 880 ₽; ASCII-диаграмма escrow-флоу
  обновлена (78,8% / 21,2%).
- `docs/AAA-03_DATABASE_REFERENCE.md` — инвариант `profit_accumulated`
  указывает 21,2%.
- `docs/AAA-04_SERVICE_REFERENCE.md` — `release_escrow` показывает
  формулу (gross_owner − service_fee = 78,8%); добавлен раздел про
  cancel split 50/40/10; `calculate_payout` отражает новую модель.
- `docs/AAA-08_ONBOARDING.md` — глоссарий и Financial Pitfalls
  обновлены.
- `docs/AAA-02_API_REFERENCE.md` — в Breaking Change History добавлена
  строка для Промт 15.7 (28.04.2026).

### Backend Python

- `src/constants/fees.py` — добавлены derived `OWNER_NET_RATE`,
  `PLATFORM_TOTAL_RATE` и хелпер `format_rate_pct()`.
- `src/bot/handlers/placement/placement.py` — split на экране оплаты
  считает service_fee; UI-строки используют `format_rate_pct(...)`
  вместо хардкода (78,8% / 21,2% / 50% / 40% / 10% теперь выводятся
  из констант).
- `src/bot/handlers/admin/disputes.py` — `advertiser_fault` payout
  считает net вместо gross; UI-строка использует
  `format_rate_pct(OWNER_NET_RATE)`.
- `src/bot/handlers/shared/start.py` — `WELCOME_TEXT` показывает
  фактическую структуру комиссии через `format_rate_pct(...)`.
- `src/api/routers/disputes.py` — обновлены docstring и комментарий
  в `advertiser_fault` ветке.
- `src/core/services/tax_aggregation_service.py` — class docstring
  переписан под Промт 15.7 (старая фраза «15% от final_price» удалена).

### Frontend (TS)

- `mini_app/src/lib/constants.ts` — добавлены gross-константы,
  `OWNER_NET_RATE` / `PLATFORM_TOTAL_RATE` через формулу,
  `CANCEL_REFUND_*` для split, `formatRatePct()` и
  `computePlacementSplit()`.
- `mini_app/src/screens/advertiser/campaign/CampaignPublished.tsx` —
  локальные хардкоды убраны; split считается через
  `computePlacementSplit`.
- `mini_app/src/screens/owner/OwnRequestDetail.tsx` — owner net
  вычисляется через `OWNER_NET_RATE` (вместо `* 0.85`).
- `web_portal/src/lib/constants.ts` — добавлены те же константы и
  helper'ы.
- `web_portal/src/screens/owner/OwnRequests.tsx` — Потенциал считается
  через `OWNER_NET_RATE`; label через `formatRatePct(...)`.
- `web_portal/src/screens/owner/OwnRequestDetail.tsx` — split-блок
  Условий перешёл на `computePlacementSplit` + `formatRatePct`.
- `web_portal/src/screens/advertiser/CampaignPayment.tsx` — детали
  оплаты + warning-текст про cancel переписаны через формулы.
- `web_portal/src/screens/advertiser/AdvertiserFrameworkContract.tsx` —
  абзац рамочного договора (legal-tone) обновлён под Промт 15.7.
- `web_portal/src/screens/advertiser/campaign/CampaignPublished.tsx` —
  локальная константа `PLATFORM_COMMISSION = 0.15` удалена; split
  через `computePlacementSplit`.
- `landing/src/lib/constants.ts` — `PLATFORM_COMMISSION` устаревшее
  значение 0.15 убрано; effective rates вычисляются.
- `landing/src/components/HowItWorks.tsx` — текст шага «Получай
  выплаты» собирается из `formatRatePct(...)`.
- `landing/src/components/FAQ.tsx` — ответ про комиссию использует
  formula-derived строки (комиссия / сервисный сбор / payout / topup).

## Что НЕ менялось (намеренно)

- `tests/unit/test_no_hardcoded_fees.py`, `tests/unit/test_fee_constants.py`,
  `tests/test_constants.py`, `tests/test_billing_service.py`,
  `tests/integration/test_*` — тесты уже зафиксировали Промт 15.7;
  трогать не требуется.
- Исторические артефакты: `CHANGELOG.md`, `reports/docs-architect/BACKLOG.md`,
  все `reports/docs-architect/discovery/CHANGES_2026-04-*` файлы —
  append-only, фиксируют состояние на момент написания.
- `reports/docs-architect/discovery/02_dependency_graph.md`,
  `01_file_inventory.md`, `DISPUTES_PATHS_DUMP_2026-04-27.md`,
  `legal-templates-inventory.md` — historical research outputs.
- `mini_app/reports/phase_*_report.md` — sprint reports (frozen).
- УСН 15% / НДФЛ 15% / weights 0.15 / animation 0.15 / threshold 0.15
  и т.п. — это другие 15-процентные значения, не комиссия платформы;
  оставлены как есть.
- `tests/unit/test_escrow_payouts.py:486-487` — комментарий "15%
  platform fee" в моке транзакции; тест проверяет произвольную
  раскладку и не привязан к комиссии Промт 15.7.

## Verification

- `poetry run ruff check` на всех изменённых Python-файлах: 0 errors.
- `poetry run pytest tests/unit/test_no_hardcoded_fees.py
  tests/unit/test_fee_constants.py`: 10 passed.
- TypeScript-сторона построится при `docker compose build --no-cache nginx`
  (Vite собирает mini_app, web_portal, landing).
