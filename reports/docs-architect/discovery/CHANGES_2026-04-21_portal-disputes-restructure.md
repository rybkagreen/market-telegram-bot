# Portal Disputes UX — restructure to per-campaign access + admin-only sidebar

**Branch:** `feat/s-47-ui-redesign-ds-v2`
**Date:** 2026-04-21
**Scope:** UI-only; никаких изменений API-контрактов или БД.

## Context

Пользователь нашёл две взаимосвязанные проблемы:

1. Админ-список «Споры» (`/admin/disputes`) переходил на общий
   read/write-экран `/disputes/:id` (shared `DisputeDetail`), где есть
   textarea «Ваш ответ». В результате админ видел форму владельца и мог
   отправить ответ от его имени — бэкенд подтверждал такие вызовы как
   `PATCH /disputes/:id` от админа, получая `owner_explanation`.
2. Структура диспутов неверна концептуально: споры привязаны к
   конкретной кампании, но отдельные пункты «Мои споры» в сайдбаре
   вынуждают пользователя искать кампанию отдельно. Для админа же,
   наоборот, не было быстрого перехода к спорной кампании.

## Goals

- Диспуты рекламодателя/владельца открываются и читаются **из деталей
  кампании**, не из сайдбара.
- В сайдбаре раздел «Споры» остаётся **только для админа**.
- Админ из спора может перейти к кампании.
- Все маршруты `/admin/**` гардятся `AdminGuard`-ом.

## Affected files

- `web_portal/src/App.tsx` — вся группа `admin/*` под единым `AdminGuard`.
- `web_portal/src/components/layout/Sidebar.tsx` — удалён пункт
  `adv-disputes` из группы «Реклама».
- `web_portal/src/screens/admin/AdminDisputesList.tsx` — navigate →
  `/admin/disputes/:id` вместо `/disputes/:id`.
- `web_portal/src/screens/admin/AdminDisputeDetail.tsx` — в header-action
  добавлена кнопка «Перейти к кампании #{placement_request_id}».
- `web_portal/src/screens/owner/OwnRequestDetail.tsx` — новая карточка
  «Спор по этой заявке» при `request.has_dispute`, ведёт на
  `/own/disputes/:disputeId` (ответ владельца).
- `web_portal/src/screens/advertiser/campaign/CampaignPublished.tsx` —
  при `placement.has_dispute` показывается статус спора и кнопка
  «Открыть детали спора» → `/disputes/:disputeId` (read-only view).
- `web_portal/src/hooks/useDisputeQueries.ts` — добавлен хук
  `useMyDisputeByPlacement(placementId)`: получает все споры пользователя
  (`GET /disputes?limit=100`) и возвращает запись, где
  `placement_request_id === placementId`. Кэширование — через
  react-query (`staleTime 30s`).

## Behavioral changes

### Admin
- `AdminDisputesList` → `AdminDisputeDetail` (вместо shared
  `DisputeDetail`). Админ видит resolve-UI с четырьмя пресетами и
  ползунком доли возврата, **без** блока «Ваш ответ».
- В header — кнопка «Перейти к кампании #N» → `/own/requests/:id`
  (OwnRequestDetail как наиболее полный read-only-экран кампании).

### Owner
- В сайдбаре пункта «Мои споры» нет (и ранее не было).
- В `/own/requests/:id` при `has_dispute=true` отображается карточка
  спора с комментарием рекламодателя и кнопкой «Ответить на спор»
  (при `status=open`) / «Открыть детали спора».

### Advertiser
- Из сайдбара убран пункт «Мои споры». Маршрут `/adv/disputes` остаётся
  доступным как глубокая ссылка (на случай уведомлений/истории), но не
  виден в сайдбаре.
- В `CampaignPublished` кнопка «Открыть спор» сохранена; когда спор уже
  открыт, рядом показывается карточка статуса и ответа владельца.

### Routing/guards
- Все `admin/**` маршруты теперь под `AdminGuard` (ранее только
  `accounting`, `tax-summary`, `settings` были под гардой; остальные
  защищались лишь условным показом в сайдбаре).

## Contract impact

- **API:** без изменений. Новых эндпойнтов/полей не заведено.
- **DB/FSM:** без изменений.
- **Типы TS:** без изменений; используется существующий
  `DisputeDetailResponse`.

## Verification

1. `npx tsc --noEmit` в `web_portal/` — без ошибок.
2. MCP-диагностики для всех шести изменённых файлов — пустые.
3. `docker compose up -d --build nginx` — контейнер стартовал.
4. Ручная проверка:
   - Админ: `/admin/disputes` → клик по записи → `/admin/disputes/:id`
     (resolve-UI, без textarea владельца); кнопка «Перейти к кампании»
     открывает `/own/requests/:id`.
   - Владелец: `/own/requests/:id` с открытым спором — видит карточку
     спора, жмёт «Ответить на спор» → `/own/disputes/:disputeId`.
   - Рекламодатель: `/adv/campaigns/:id/published` — «Открыть спор» для
     новой претензии, карточка статуса при существующем споре.
   - Не-админ, попытавшийся открыть `/admin/disputes` напрямую,
     редиректится на `/` через `AdminGuard`.

🔍 Verified against: `45bdb04` | 📅 Updated: 2026-04-21T00:00:00Z
