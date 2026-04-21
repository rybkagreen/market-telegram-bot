# Admin dispute filter fix + campaigns filter unification

**Branch:** `feat/s-47-ui-redesign-ds-v2`
**Date:** 2026-04-21
**Scope:** UI-only; без изменений API / БД.

## Context

1. Открытый спор со статусом `owner_explained` («ожидает ответа
   администратора») не попадал в `AdminDisputesList`: дефолтный фильтр
   был `open`, а пункт «Ответ владельца» отправлял на бэк
   `status=owner_reply`, что бэк отвергал с 400 (валидные значения —
   `open|owner_explained|resolved|all`). В результате такой дисп
   пропадал из любого среза.
2. Пользователь заметил расхождение фильтров кампаний:
   `status=published` на экране рекламодателя (`MyCampaigns`) был в
   «Завершена», а у владельца (`OwnRequests`) — в «Активные». Одна и
   та же кампания одновременно показывалась в противоположных
   категориях.

## Affected files

- `web_portal/src/screens/admin/AdminDisputesList.tsx`
- `web_portal/src/screens/owner/OwnRequests.tsx`

## Changes

### 1. AdminDisputesList

- Тип `StatusFilter`: `owner_reply` → `owner_explained`.
- `FILTERS`: соответственно обновлён ключ и порядок; добавлена «Все»
  первой.
- Значение по умолчанию: `useState<StatusFilter>('all')` (было
  `'open'`) — админ сразу видит и открытые, и ожидающие решения
  споры.
- Контракт с бэком (`GET /disputes/admin/disputes?status=…`) теперь
  совпадает: значения `open | owner_explained | resolved` передаются
  как есть; `all` → параметр не передаётся.

### 2. OwnRequests — добавлен фильтр «Завершённые»

- `Filter` теперь `'new' | 'active' | 'completed' | 'cancelled'`.
- `ACTIVE_STATUSES` = `['escrow']` (ранее включал `'published'`).
- Добавлен `COMPLETED_STATUSES = ['published']`.
- Новая кнопка «Завершённые» в фильтрах и подсчёт `completedCount`.
- SummaryTile «Активных» заменён на «Завершено» (тональность success,
  delta «Опубликованные размещения»).
- `getFilter()` теперь различает 4 бакета.

После изменения обе стороны трактуют `published` как **Завершено** —
расхождения больше нет.

## Verification

1. `npx tsc --noEmit` в `web_portal/` — exit 0.
2. MCP-диагностики `AdminDisputesList.tsx` и `OwnRequests.tsx` —
   пустой список.
3. `docker compose up -d --build nginx` — контейнер стартовал.
4. Ручная проверка:
   - Админ открывает `/admin/disputes` — по умолчанию фильтр «Все»,
     виден дисп со статусом `owner_explained`; клик по фильтру
     «Ответ владельца» отправляет `status=owner_explained` и не
     падает.
   - Владелец открывает `/own/requests` — размещение `published`
     отображается в фильтре «Завершённые», как и у рекламодателя.

🔍 Verified against: `45bdb04` | 📅 Updated: 2026-04-21T00:00:00Z
