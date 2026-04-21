# Disputes flow — deep audit + production-readiness fixes

**Branch:** `feat/s-47-ui-redesign-ds-v2`
**Date:** 2026-04-21
**Scope:** full review of dispute flow (backend + frontend). This
document captures the audit findings and the fixes shipped in the same
change set.

## Context

Пользователь сообщил:
1. В админ-панели на фильтре «Все» — пусто, хотя на «Активные»
   отображался спор.
2. У открытого спора неправильно показан статус.

Это триггернуло полный аудит dispute-флоу, включающего
`PlacementDispute` модель, router'ы, repo, shared/admin/owner/advertiser
экраны и хуки.

## Audit findings (grouped by severity)

### 🔴 Critical

1. **Admin `/admin/disputes` default filter = "open"** —
   `src/api/routers/disputes.py:444`. Frontend при выборе «Все»
   передавал `status: undefined` → бэк получал отсутствующий параметр и
   возвращал только `open`. **Fixed**: default переведён на `"all"`.
2. **`POST /disputes` не ограничивал время / роль** —
   `src/api/routers/disputes.py:190-249`. Любой участник размещения
   (включая владельца канала) мог создать спор; 48-часовое окно
   проверялось только клиентом. **Fixed**: серверная проверка —
   создавать может только рекламодатель; статус размещения должен быть
   `published`; окно ≤48 ч.

### 🟠 High

3. **Рассогласованные статус-лейблы** — `open|owner_explained|
   resolved|closed` имели 4+ разные формулировки в разных экранах:
   MyDisputes фильтр «Ожидание» vs бейдж «Ответ владельца»; в
   DisputeResponse у владельца — «Владелец ответил» (3-е лицо).
   **Fixed**: создан `web_portal/src/lib/disputeLabels.ts` — единый
   источник истины с ролево-зависимыми лейблами
   (`getRoleAwareStatusLabel(status, 'advertiser'|'owner'|'admin')`).
4. **`useMyDisputeByPlacement` упирается в `limit=100`** —
   `web_portal/src/hooks/useDisputeQueries.ts`. Фильтровал список
   клиентски, ломался на users с 100+ диспутами. **Fixed**:
   добавлен бекенд-эндпойнт `GET /disputes/by-placement/{placement_id}`,
   хук теперь бьёт его напрямую.
5. **Shared `DisputeDetail` показывал форму «Ваш ответ»** —
   любой пользователь, открывший `/disputes/:id` (включая админа,
   рекламодателя), видел textarea и Submit-кнопку. Бэк возвращает 403
   рекламодателю, но UX вводил в заблуждение. **Fixed**: форма удалена
   из shared-экрана; если текущий пользователь — владелец открытого
   спора, показывается Notification со ссылкой «Ответить» →
   `/own/disputes/:id`.
6. **Обратная кнопка вела в несуществующий `/disputes`** —
   `DisputeDetail.tsx`. **Fixed**: `navigate(-1)` + лейбл «Назад».

### 🟡 Medium

7. **Дедуп labels в 5+ файлах** — `STATUS_META`/`STATUS_CONFIG`/
   `STATUS_LABEL`/`DISPUTE_STATUS_LABEL`. **Fixed**: всё переведено
   на `disputeLabels.ts`.

### 🟢 Deferred (task #19)

8. **Нет Telegram-уведомлений** на создание/ответ/разрешение спора.
9. **Нет автоэскалации** stale `owner_explained` диспутов (поле
   `expires_at` не используется).
10. **Неиспользуемый статус `closed`** в enum — кода, который его
    ставит, нет.
11. **Параллельные enum'ы** `DisputeStatus`/`DisputeResolution` в
    `src.api.schemas` vs `src.db.models` — источник существующих
    Pyright-ошибок (pre-existing, не блокирует).

## Changes shipped

### Backend

- `src/api/routers/disputes.py`
  - `/admin/disputes` — default `status="all"` (было `"open"`).
  - `POST /disputes` — hardening: advertiser-only, 48h window check,
    `status=published` required.
  - New route `GET /disputes/by-placement/{placement_request_id}` —
    возвращает `DisputeResponse | None`, проверяет роль через
    `_get_placement_or_404`.

### Frontend — shared config

- `web_portal/src/lib/disputeLabels.ts` — `DISPUTE_STATUS_META`,
  `DISPUTE_TONE_CLASSES`, `DISPUTE_REASON_LABELS`,
  `getDisputeStatusMeta`, `getDisputeReasonLabel`,
  `getRoleAwareStatusLabel`.

### Frontend — screens refactored to use shared config

- `web_portal/src/screens/shared/MyDisputes.tsx`
- `web_portal/src/screens/shared/DisputeDetail.tsx` — removed owner
  textarea; added owner-redirect notification; back nav fixed.
- `web_portal/src/screens/admin/AdminDisputesList.tsx`
- `web_portal/src/screens/admin/AdminDisputeDetail.tsx`
- `web_portal/src/screens/owner/DisputeResponse.tsx`
- `web_portal/src/screens/owner/OwnRequestDetail.tsx`
- `web_portal/src/screens/advertiser/campaign/CampaignPublished.tsx`

### Frontend — hook/api

- `web_portal/src/api/disputes.ts` — `getDisputeByPlacement()` added.
- `web_portal/src/hooks/useDisputeQueries.ts` —
  `useMyDisputeByPlacement` теперь вызывает новый эндпойнт.

## Verification

1. `npx tsc --noEmit` (web_portal) — exit 0.
2. MCP diagnostics для 7 изменённых TS-файлов — пусто.
3. `docker compose up -d --build nginx api` — оба контейнера Up,
   `/api/` отдаёт 200, логи API без ошибок.
4. Manual:
   - Админ: `/admin/disputes` → фильтр «Все» отдаёт полный список;
     «На рассмотрении» возвращает `owner_explained` записи.
   - Попытка рекламодателя открыть второй спор по тому же размещению →
     409 Conflict.
   - Попытка открыть спор за 48h+ после публикации → 409.
   - Попытка владельца открыть спор → 403.
   - Shared `/disputes/:id` для не-владельца не показывает форму; для
     владельца показывает CTA «Ответить».

## Deferred (track in dedicated ticket)

- Telegram-уведомления: `notify_dispute_created`,
  `notify_owner_replied`, `notify_resolution_issued`.
- Celery beat: `dispute:auto_escalate` — auto-resolve stale
  `owner_explained` диспутов через 72 ч (использовать поле
  `expires_at`).
- Унификация параллельных enum'ов `DisputeStatus` /
  `DisputeResolution` между `schemas/dispute.py` и `db/models/dispute.py`.

🔍 Verified against: `45bdb04` | 📅 Updated: 2026-04-21T00:00:00Z
