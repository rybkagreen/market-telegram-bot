# Changes: Campaign Timeline — Full Lifecycle Tracking

**Date:** 2026-04-11  
**Author:** Qwen Code  
**Commit:** pending  
**Sprint:** S-29 (Campaign Lifecycle Tracking)

---

## Summary

Added missing stages to the campaign placement timeline, enabling full lifecycle tracking from creation to completion. Previously, the timeline showed only: created → payment → escrow → publication. Now it shows all 8 stages including waiting for placement, deletion countdown, escrow release, and ERID status.

**Plus:** Fixed LegalProfileSetup "Кем выдан" field — replaced single-line input with 3-row textarea.

---

## затронутые файлы

### Backend (Python)

| Файл | Изменение | Влияние |
|------|-----------|---------|
| `src/db/models/placement_request.py` | Added `completed = "completed"` to `PlacementStatus` enum | New terminal state after deletion + escrow release |
| `src/core/services/publication_service.py` | `delete_published_post()` now sets `placement.status = PlacementStatus.completed` after `release_escrow()` | Fixes missing state transition — placement now properly marked as completed |
| `src/tasks/placement_tasks.py` | `check_published_posts_health` now monitors both `published` and `completed` statuses | Health check continues to audit completed placements |

### Frontend (TypeScript/React)

| Файл | Изменение | Влияние |
|------|-----------|---------|
| `mini_app/src/lib/types.ts` | Added `'completed'` to `PlacementStatus` type | Type safety for new status |
| `mini_app/src/lib/constants.ts` | Added `completed: 'Завершена'` to `CAMPAIGN_STATUS_LABELS` | UI label for new status |
| `mini_app/src/screens/advertiser/campaign/CampaignWaiting.tsx` | Rewrote `buildTimelineEvents()` — now shows 8-stage lifecycle | **Major change** — full lifecycle visualization |
| `mini_app/src/components/ui/RequestCard.tsx` | Added `'completed'` to `RequestStatus` type + STATUS_PILL mapping | RequestCard displays completed status correctly |
| `mini_app/src/screens/advertiser/MyCampaigns.tsx` | Added `'completed'` to `COMPLETED_STATUSES` array | Campaigns with completed status show in "Завершённые" tab |
| `web_portal/src/screens/common/LegalProfileSetup.tsx` | Replaced `<input>` with `<Textarea rows={3}>` for "Кем выдан" field | Long issuing authority names no longer truncated |

### Database

| Change | Method | Notes |
|--------|--------|-------|
| Added `completed` to `placementstatus` enum | `ALTER TYPE placementstatus ADD VALUE IF NOT EXISTS 'completed' AFTER 'published'` | PostgreSQL enum — irreversible (cannot remove enum values) |

---

## Новый Timeline — 8 этапов

```
1. ✅ Заявка создана           — created_at timestamp
2. ⏳ Ожидает ответа владельца  — expires_at (24h SLA)
3. 💳 Оплата                  — pending_payment → escrow
4. 🔒 Эскроу                  — средства заблокированы
5. ⏳ Ожидает размещения       — escrow → published (owner publishes)
6. 📢 Опубликовано            — published_at + ERID статус
7. ⏳ Удаление через X ч       — countdown to scheduled_delete_at
8. ✅ Завершена               — post deleted + escrow released
```

**ERID статус** отображается как отдельный элемент timeline (присвоен/ожидается).

---

## Влияние на бизнес-логику

### Положительное
- ✅ Рекламодатели видят полный жизненный цикл кампании
- ✅ Можно точно определить на каком этапе произошёл сбой
- ✅ Статус `completed` — явное indication что escrow освобождён
- ✅ ERID статус виден без перехода на отдельный экран
- ✅ Countdown удаления — прозрачность для рекламодателей

### Риски
- ⚠️ Существующие `published` размещения без `deleted_at` останутся в статусе `published` (не `completed`)
- ⚠️ Для старых размещений timeline покажет "published" без countdown (нет scheduled_delete_at)

---

## API Контракты — изменения

### PlacementResponse (без изменений)
Новый статус `completed` передаётся в поле `status: string`. Никаких новых полей не добавлено — timeline вычисляется на клиенте из существующих полей:
- `scheduled_delete_at` — для countdown
- `published_at` — для timestamp публикации
- `erid` — для статуса маркировки
- `deleted_at` — для подтверждения завершения

---

## Migration Notes

**DB Migration:** `ALTER TYPE placementstatus ADD VALUE IF NOT EXISTS 'completed' AFTER 'published'`

**Rollback:** PostgreSQL enum values cannot be removed. To revert, would need to:
1. Create new enum type without `completed`
2. Update all rows with `status='completed'` to `published`
3. Drop old enum type, rename new to old
**Not recommended** — this is a forward-only change.

**Backend:** No env var changes. Just code deployment.

**Frontend:** Rebuild nginx with `--no-cache` required (Vite build caching).

---

## Testing Checklist

- [ ] Создать новую кампанию → проверить что timeline показывает все 8 этапов
- [ ] Дождаться публикации → проверить что появляется этап "Опубликовано" + ERID
- [ ] Дождаться удаления (или вручную вызвать `delete_published_post`) → проверить статус `completed`
- [ ] Проверить что MyCampaigns показывает completed кампании в правильной вкладке
- [ ] Проверить что RequestCard отображает "Завершено" для completed статуса
- [ ] Проверить что terminal states (cancelled/failed) показывают корректный timeline

---

🔍 Verified against: working tree | 📅 Updated: 2026-04-11T13:00:00Z
