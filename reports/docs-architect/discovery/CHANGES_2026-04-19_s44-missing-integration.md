# Changes: S-44 Missing frontend↔backend integration — Stage 3 of 6-stage fix plan
**Date:** 2026-04-19T00:00:00Z
**Author:** Claude Code
**Sprint/Task:** S-44 (fix plan Stage 3 — Missing integration, P1)
**Branch:** `feat/s-44-missing-integration`

## Scope
Подключены реализованные, но неиспользуемые бэкенд-эндпоинты к UI web_portal,
согласно `reports/20260419_diagnostics/FIX_PLAN_03_missing_integration.md`
(§§ 3.1, 3.2, 3.4, 3.7, 3.8a, 3.8b). Плюс два Stage 2 follow-up'а, всплывшие
при `npx tsc --noEmit` (phantom re-exports + ContractData status).

Пункты 3.3 (CampaignVideo uploads), 3.5 (PRO-аналитика), 3.6 (channel preview)
**отложены** — требуется продуктовое согласование, см. _Known follow-ups_.

## Affected Files

### Frontend (web_portal) — API clients
- `web_portal/src/api/billing.ts` — +`TopupStatus`, `getTopupStatus(paymentId)`.
- `web_portal/src/api/users.ts` — +`checkNeedsAcceptRules()`.
- `web_portal/src/api/disputes.ts` — +`PublicationEvidenceEvent`,
  `DisputeEvidenceSummary`, `DisputeEvidenceResponse`, `getDisputeEvidence(placementId)`.
- `web_portal/src/api/admin.ts` — +`PlatformCreditResponse`,
  `GamificationBonusResponse`, `createPlatformCredit()`, `createGamificationBonus()`.

### Frontend (web_portal) — hooks
- `web_portal/src/hooks/useBillingQueries.ts` — +`useTopupStatus()` (polling 3s,
  максимум 120s, инвалидация `billing.balance`/`billing.history`/`user.me` при
  `succeeded`, локальный `timedOut` через setTimeout).
- `web_portal/src/hooks/useUserQueries.ts` — +`useNeedsAcceptRules()` (staleTime 5мин).
- `web_portal/src/hooks/useDisputeQueries.ts` — +`useDisputeEvidence(placementId)`.
- `web_portal/src/hooks/useAdminQueries.ts` — +`useCreatePlatformCredit()`,
  `useCreateGamificationBonus()` (invalidate `admin.user.{id}`, `admin.platform-stats`).

### Frontend (web_portal) — screens / layout
- `web_portal/src/screens/shared/TopUp.tsx` — пробрасывает `paymentId`
  в `location.state` для следующего шага.
- `web_portal/src/screens/shared/TopUpConfirm.tsx` — реальное отслеживание статуса
  через `useTopupStatus`: Notification + набор кнопок под `succeeded`/`canceled`/
  `timedOut`/`pending`; StepIndicator теперь показывает текущий шаг 2.
- `web_portal/src/components/layout/PortalShell.tsx` — «Выплаты» в admin sidebar
  (иконка `Banknote`), breadcrumb для `/admin/payouts`; warning-плашка
  «Примите правила платформы» с кнопкой на `/accept-rules`, скрытая на самой
  странице accept-rules.
- `web_portal/src/screens/shared/OpenDispute.tsx` — карточка «Что мы знаем о
  публикации»: published_at, deleted_at + тип удаления, total_duration_minutes,
  erid_present, раскрывающийся лог событий с ссылками на пост.
- `web_portal/src/screens/admin/AdminUserDetail.tsx` — две новые карточки:
  «Зачислить из доходов платформы» (POST `/admin/credits/platform-credit`) и
  «Геймификационный бонус» (POST `/admin/credits/gamification-bonus`).
  Feedback-сообщения показывают `new_user_balance`/`new_user_xp`.
- `web_portal/src/screens/admin/AdminAccounting.tsx` — `downloadMode` переключён
  с `simple` (через `window.open` → 401, т.к. Bearer-токен не прикладывается)
  на `auth`.
- `web_portal/src/components/admin/TaxSummaryBase.tsx` — удалена мёртвая ветка
  `simple`-загрузки, тип `downloadMode` остался как `'auth'` для совместимости.

### Follow-ups из Stage 2 (вскрылись при tsc)
- `web_portal/src/lib/types/index.ts` — удалены несуществующие re-exports
  `Payout`/`AdminPayout`/`PayoutListAdminResponse` из `./billing`.
- `web_portal/src/screens/common/ContractDetail.tsx` — локальный интерфейс
  `ContractData.status` → `contract_status` (выровнен с `ContractResponse`
  бэкенда).

## Business Logic Impact
- **TopUp flow без перезагрузки.** После инициации платежа пользователь видит
  на `/topup/confirm` актуальный статус. На `succeeded` — моментальное
  обновление баланса и кнопка «История операций», `canceled` — красная
  плашка, `timeout 2мин` — hint «проверьте позже».
- **Admin payouts доступны из меню.** Раньше раздел был только по прямому URL.
- **Fallback на orphan accept-rules.** `RulesGuard` всё ещё перехватывает
  пользователей без таймстампов, но плашка поверх контента позволяет увидеть
  состояние и на exempt-маршрутах (/legal-profile), и пережить
  любое будущее ослабление RulesGuard.
- **Evidence-блок при открытии спора.** Советник не строит дело «на ощупь» —
  видит, когда пост действительно опубликован и сколько провисел.
- **Ручные зачисления в админке.** Операторам больше не надо лезть в psql/curl,
  чтобы перевести деньги из `profit_accumulated` или дать XP-бонус.
- **KUDiR-экспорт больше не 401.** `AdminAccounting` теперь корректно
  выкачивает PDF/CSV с Bearer-токеном.

## API / FSM / DB Contracts
- **Backend**: без изменений — все endpoint'ы уже существовали, меняется только
  потребление.
- **Frontend**: новые TS-интерфейсы для публикуемых ответов
  (`DisputeEvidenceResponse`, `PlatformCreditResponse`,
  `GamificationBonusResponse`, `TopupStatus`). Никаких breaking changes.

## Migration Notes
Не требуется. После мерджа в develop/main — `docker compose up -d --build nginx api`
(напоминание из memory), иначе новая UI не соберётся внутри образа nginx.

## Verification
- `cd web_portal && npx tsc --noEmit -p tsconfig.app.json` → exit 0 (после
  Stage 2 follow-up'ов — 0 ошибок; до коммита `cc75b83` было 10 карри-оверов).
- `docker compose exec api poetry run ruff check src/` → 3 pre-existing errors
  (document_validation, channel_owner) — не затронуты в S-44 (ни один `.py`
  не модифицирован).
- Ручной smoke не выполнен (требуется `docker compose up -d --build nginx api`).

## Known Follow-ups
- **§3.3 CampaignVideo uploads** — требует либо Redis-поллинг + deep-link в
  бота (нужен `src/bot/handlers/upload_video.py`), либо нового POST-endpoint
  `/api/uploads/video` с multipart/form-data. Поднять на ближайшем планировании.
- **§3.5 PRO/BUSINESS analytics blocks** — зависит от бизнес-решения,
  будет ли PRO-тариф продвигаться в ближайший квартал. Эндпоинты
  `/analytics/summary|activity|top-chats|topics|campaigns/{id}/ai-insights`
  остаются orphan до решения.
- **§3.6 Channel preview в wizard** — low business value, предложен к
  удалению в Stage 4 (orphan reject) если UX-команда не подтвердит.
- **§3.8 прочие admin-экраны** — LegalProfiles verify-UI, AuditLog screen,
  AdminContracts screen — заведены как отдельные эпики в бэклог.
- Backlog из Stage 1/2 — baseline ruff (3 errors) всё ещё ждёт владельца;
  трогать в рамках Stage 3 смысла нет, так как файлы вне P1-скоупа.

🔍 Verified against: `feat/s-44-missing-integration` HEAD (ed56d11) | 📅 Updated: 2026-04-19
