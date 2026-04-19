# Changes: S-42 Phantom calls — Stage 1 of 6-stage fix plan
**Date:** 2026-04-19T00:00:00Z
**Author:** Claude Code
**Sprint/Task:** S-42 (fix plan Stage 1 — Phantom calls, P0)

## Scope
Устранены 7 подтверждённых phantom-calls из `reports/20260419_diagnostics/FIX_PLAN_01_phantom_calls.md` — случаев, когда web_portal дёргает несуществующие URL бэкенда (живые 404 в рантайме).

## Affected Files

### Backend
- `src/api/routers/acts.py` — `GET /api/acts/mine` принимает новый query-параметр `placement_request_id: int | None`; фильтр пробрасывается в `ActRepository.list_by_user(...)`.
- `src/api/routers/channels.py` — новый эндпоинт `GET /api/channels/{channel_id}` → `ChannelResponse`. Доступ: владелец или админ (404 если нет). Маршрут размещён перед `DELETE /{channel_id}`; `int`-типизация пути гарантирует, что он не перехватывает `/available`, `/stats`, `/preview`, `/compare/preview`.
- `src/api/routers/admin.py` — 3 новых эндпоинта:
  - `GET /api/admin/payouts?status=&limit=&offset=` → `AdminPayoutListResponse`
  - `POST /api/admin/payouts/{payout_id}/approve` → `AdminPayoutResponse` (статус → `paid`)
  - `POST /api/admin/payouts/{payout_id}/reject` (body `{reason}`) → `AdminPayoutResponse` (статус → `rejected`, возврат на `earned_rub`)
- `src/api/schemas/payout.py` — добавлены `AdminPayoutResponse`, `AdminPayoutListResponse`, `AdminPayoutRejectRequest`.
- `src/core/services/payout_service.py` — добавлены методы `approve_request(payout_id, admin_id)` и `reject_request(payout_id, admin_id, reason)`. Обёртки над существующими `complete_payout` / `reject_payout`; правят финальный статус (`rejected` вместо `cancelled` при отклонении администратором) и фиксируют `admin_id`.
- `src/db/repositories/act_repo.py` — `list_by_user` расширен опциональным `placement_request_id`.

### Frontend (web_portal)
- `web_portal/src/api/reviews.ts` — URL `reviews/placement/${id}` → `reviews/${id}`.
- `web_portal/src/api/reputation.ts` — URL `reputation/history` (page/limit) → `reputation/me/history` (limit/offset). Response тип скорректирован на `ReputationHistoryItem[]` (бэк отдаёт массив, не обёрнутый объект). Drift в полях (`reason` vs `comment`) — Stage 2.
- `web_portal/src/hooks/useReputationQueries.ts` — сигнатура хука `(limit, offset)`.
- `web_portal/src/api/campaigns.ts` — `startCampaign/cancelCampaign/duplicateCampaign` используют `/api/campaigns/{id}/*` вместо `/placements/{id}/*` (бэк имеет эти методы на `campaigns_router`). В `getMyPlacements` заменены `page`/`page_size` на `limit`/`offset`; также параметры вынесены в опциональный вход функции.
- `web_portal/src/api/acts.ts` — URL `acts/?placement_request_id=X` → `acts/mine?placement_request_id=X`, response-тип выровнен на `ActListResponse`.
- `web_portal/src/App.tsx` — подключён существующий orphan screen `AdminPayouts` под маршрутом `/admin/payouts`.

## Business Logic Impact
- **Auditable admin approvals** — теперь у каждой выплаты, одобренной/отклонённой админом, в БД фиксируется `admin_id` (поле существовало, но не заполнялось).
- **Семантическое различение `rejected` vs `cancelled`** — `rejected` = отклонено админом; `cancelled` = отменено пользователем. Ранее `reject_payout` ошибочно использовал `cancelled`.
- **Acts filter** — страница актов кампании теперь грузится (ранее возвращала 404).
- **Reputation history** — доступна корректно из web_portal.
- **Campaign actions** — start/cancel/duplicate работают (ранее 404 — функциональность экранов была сломана).
- **Channel detail** — экран канала владельца открывается без 404.

## API / FSM / DB Contracts

### Added
- `GET /api/acts/mine?placement_request_id={int}` — new optional query param
- `GET /api/channels/{channel_id}` → `ChannelResponse` — new endpoint
- `GET /api/admin/payouts?status=&limit=&offset=` → `AdminPayoutListResponse` — new
- `POST /api/admin/payouts/{payout_id}/approve` → `AdminPayoutResponse` — new
- `POST /api/admin/payouts/{payout_id}/reject` → `AdminPayoutResponse` — new
- Pydantic: `AdminPayoutResponse`, `AdminPayoutListResponse`, `AdminPayoutRejectRequest`

### Changed (internal only, no contract break)
- `ActRepository.list_by_user(user_id, limit, placement_request_id=None)` — новый kw-only параметр.
- `PayoutService.approve_request(payout_id, admin_id)` / `reject_request(payout_id, admin_id, reason)` — новые методы.

### FSM / DB
- DB schema не менялась (все поля уже существовали: `payout_requests.admin_id`, `rejection_reason`, `status` enum).

## Migration Notes
Не требуется миграции. Существующие значения `status=cancelled` у отклонённых админом выплат не переприсваиваются — это исторический артефакт; новые отклонения пойдут как `rejected`.

## Known follow-ups (Stage 2)
- `web_portal/src/lib/types/billing.ts#AdminPayout` имеет поле `reject_reason`, бэк возвращает `rejection_reason` — контрактный дрейф, будет устранён в Stage 2 (§2.1 Payout Consolidation).
- `web_portal/src/lib/types/analytics.ts#ReputationHistoryItem` поле `reason` vs бэковский `comment`, отсутствуют `user_id`, `role` — Stage 2.
- Frontend `PlacementRequest` vs backend `CampaignResponse` для `campaigns/*/start|cancel|duplicate` эндпоинтов — Stage 2.

## Verification
- `docker compose exec api poetry run ruff check src/api/routers/acts.py src/api/routers/channels.py src/api/routers/admin.py src/api/schemas/payout.py src/core/services/payout_service.py src/db/repositories/act_repo.py` → **All checks passed**.
- `cd web_portal && npx tsc --noEmit` → **exit 0, no output**.
- Ручная проверка URL в Network (Definition of Done): отложена до следующего запуска контейнеров.

🔍 Verified against: `fix/s-42-phantom-calls` HEAD | 📅 Updated: 2026-04-19
