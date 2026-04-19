# Changes: S-43 Contract drift alignment — Stage 2 of 6-stage fix plan
**Date:** 2026-04-19T00:00:00Z
**Author:** Claude Code
**Sprint/Task:** S-43 (fix plan Stage 2 — Contract drift, P0)
**Branch:** `fix/s-43-contract-alignment`

## Scope
Устранён контрактный дрейф между TypeScript-типами web_portal и Pydantic-схемами
бэкенда из `reports/20260419_diagnostics/FIX_PLAN_02_contract_drift.md` (§§ 2.1–2.8),
плюс три follow-up пункта из Stage 1 CHANGES файла. Источник правды — Pydantic-схемы
в `src/api/schemas/` и inline-классы в роутерах; фронт следует.

## Affected Files

### Infrastructure
- `.gitignore` — добавлено исключение `!web_portal/src/lib/` для Python-правила `lib/`,
  которое случайно скрывало 11 файлов типов/констант из VCS. Файлы работали только
  через Docker bind mount; теперь под контролем git.
- `web_portal/src/lib/constants.ts`, `web_portal/src/lib/timeline.ts`,
  `web_portal/src/lib/timeline.types.ts`, `web_portal/src/lib/types/*.ts` — добавлены
  в трекинг (as-is baseline, без изменений контента в отдельной chore-коммите).

### Frontend (web_portal) — types
- `web_portal/src/lib/types/payout.ts` — **новый канонический файл**:
  `PayoutStatus`, `PayoutResponse`, `AdminPayoutResponse`, `AdminPayoutListResponse`,
  `PayoutCreateRequest`. Поля точно соответствуют `src/api/schemas/payout.py`.
- `web_portal/src/lib/types/billing.ts` — `Payout/AdminPayout/PayoutListAdminResponse`
  больше не определяются здесь; re-export из `types/payout.ts`. `OrdStatus` сохранён.
- `web_portal/src/lib/types.ts` — удалено `PayoutStatus` (несовпадающий enum со значением
  `completed` вместо `paid`) и `status: ContractStatus` в `Contract`. Обновлён
  `DisputeReason` (добавлены `post_removed_early`, `bot_kicked`, `advertiser_complaint`).
- `web_portal/src/lib/types/user.ts` — `User.referral_code: string` → `string | null`.
- `web_portal/src/lib/types/placement.ts` — добавлены `advertiser_counter_price`,
  `advertiser_counter_schedule`, `advertiser_counter_comment`, `updated_at`;
  `proposed_schedule`, `expires_at` → nullable.
- `web_portal/src/lib/types/contracts.ts` — убран фейковый `status: ContractStatus`,
  `contract_status` стал required.
- `web_portal/src/lib/types/legal.ts` — удалены 4 паспортных поля (`passport_series`,
  `passport_number`, `passport_issued_by`, `passport_issued_at`) из response-типа
  `LegalProfile`; остался только флаг `has_passport_data`.
- `web_portal/src/lib/types/dispute.ts` — удалён legacy `interface Dispute`
  (placement_id/owner_comment/resolution_action).
- `web_portal/src/lib/types/index.ts` — убран `Dispute` из barrel export.
- `web_portal/src/lib/types/channel.ts` — `ChannelResponse` получил `last_er`,
  `avg_views`, `is_test`; `Channel.category` → nullable.
- `web_portal/src/lib/types/analytics.ts` — `ReputationHistoryItem`: добавлены
  `user_id`, `role`; `reason` → `comment` (как на бэке `ReputationHistoryEntry`).

### Frontend (web_portal) — consumers
- `web_portal/src/api/payouts.ts` — re-export `PayoutResponse/PayoutCreateRequest`,
  инлайновый `Payout` удалён.
- `web_portal/src/api/admin.ts` — импорты переключены на `AdminPayoutResponse` /
  `AdminPayoutListResponse`.
- `web_portal/src/api/campaigns.ts` — заменены возвращаемые типы:
  `startCampaign`/`cancelCampaign` → `CampaignActionResponse ({status, placement_request_id})`;
  `duplicateCampaign` → `CampaignDuplicateResponse ({id, ad_text})`.
- `web_portal/src/hooks/usePayoutQueries.ts` — `Payout[]` → `PayoutResponse[]`.
- `web_portal/src/screens/owner/OwnPayouts.tsx` — pill-map `completed` → `paid`,
  добавлен `cancelled`; `payout.amount` → `payout.gross_amount`.
- `web_portal/src/screens/common/ContractList.tsx`,
  `web_portal/src/screens/common/ContractDetail.tsx`,
  `web_portal/src/lib/timeline.ts` — все обращения `contract.status` переведены
  на `contract.contract_status`.
- `web_portal/src/screens/common/LegalProfileSetup.tsx` — удалены pre-fill чтения
  4 паспортных полей из ответа (они всегда были `undefined`); submit-поле
  `passport_issued_at` переименовано в `passport_issue_date` под backend schema.
- `web_portal/src/shared/ui/StatusBadge.tsx` — `PayoutStatus`/`OrdStatus` теперь
  импортируются из `types/billing.ts`.

## Business Logic Impact
- **Корректное отображение сумм выплат** (OwnPayouts): ранее UI обращался к
  `payout.amount`, поле которого нет в API (возвращается `gross_amount`), что
  приводило к отображению `undefined ₽`.
- **Admin payouts — статус `paid`**: пилот показывал "completed" в маппинге,
  бэк возвращает `paid` — кнопки-фильтры и бейджи теперь работают.
- **Контракты**: `contract.status` читался как `undefined` во всех местах
  (`ContractList`, `ContractDetail`, timeline); теперь статусы отображаются
  корректно через `contract_status`.
- **LegalProfile**: форма «вид паспорта» больше не пытается показать PII из
  response (всё равно её там не было) и сохраняет дату в поле `passport_issue_date`,
  ожидаемом бэкендом.
- **Кампании (start/cancel/duplicate)**: тип возвращаемого значения теперь
  соответствует реальному ответу; потребители могут полагаться на
  `placement_request_id` у ответа start/cancel и `id` у duplicate.
- **Репутация (ReputationHistoryItem)**: поля `user_id`, `role`, `comment` теперь
  доступны для будущих UI-улучшений истории репутации.

## API / FSM / DB Contracts

### Changed (TS-only — frontend types aligned with backend)
- `PayoutResponse/AdminPayoutResponse` — новый источник `lib/types/payout.ts`;
  старые `Payout/AdminPayout` остаются как type alias? **Нет — удалены**.
- `User.referral_code: string | null`.
- `PlacementRequest` — добавлены 4 поля, 2 поля → nullable.
- `Contract` — удалено `status`, `contract_status` обязательно.
- `LegalProfile` (response) — удалены 4 паспортных поля.
- `Dispute` (legacy) — тип удалён; потребители переходят на `DisputeDetailResponse`.
- `ChannelResponse` — добавлены `last_er/avg_views/is_test`.
- `Channel.category` → nullable.
- `DisputeReason` (root types.ts) — добавлены 3 bot-legacy значения.
- `ReputationHistoryItem` — `user_id`, `role`, `comment` (вместо `reason`).
- `startCampaign/cancelCampaign/duplicateCampaign` — корректные response-типы.

### Backend
- Без изменений.

### DB
- Без изменений.

## Migration Notes
Не требуется миграции БД. Тип-правки на фронте — чисто compile-time, без
изменений wire-format'а. Пользователям не нужно перезагружать данные.

## Verification
- `cd web_portal && npx tsc --noEmit` → exit 0, no output (all 10 commits).
- DoD grep checks:
  - `grep -rn "reject_reason\|contract\.status" web_portal/src/` → 0 matches.
  - `grep -rn "payment_details" web_portal/src/` → только в `PayoutCreateRequest`
    (это wire-field для POST /payouts, корректно).
  - `grep -rn "fee: string" web_portal/src/` → 2 matches, оба в `TopupInitiateResponse`
    (billing top-up fee, не payout fee) — валидны.
- Контейнерная проверка и ручной smoke (OwnPayouts, ContractList, LegalProfileSetup)
  отложены — запустить после `docker compose up -d --build nginx api`.

## Known follow-ups
- Отделить `/reputation/me/history` response-тип (list directly) от `ReputationHistory`
  (который сейчас выглядит как paginated — но такого эндпоинта у /me нет).
  Сейчас `api/reputation.ts` уже возвращает `ReputationHistoryItem[]` — потребители
  знают.
- mini_app не затронут — если там есть аналогичные типы, их сверка — отдельный скоуп.
- OpenAPI-spec генерация фронтовых типов (см. Этап 6) — предотвратит будущий дрейф.

🔍 Verified against: `fix/s-43-contract-alignment` HEAD (48944e7) | 📅 Updated: 2026-04-19
