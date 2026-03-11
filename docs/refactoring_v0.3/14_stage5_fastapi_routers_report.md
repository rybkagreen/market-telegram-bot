# Этап 5: Завершение — FastAPI routers (placements, channel_settings, reputation)

**Дата:** 2026-03-10
**Тип задачи:** NEW_FEATURE
**Принцип:** CLEAN_RESULT — RESTful, типизировано, без бизнес-логики в роутерах
**Статус:** ✅ ЗАВЕРШЁНО
**Файлы создано:** 3
**Файлы изменено:** 2
**Строк кода:** ~750

---

## 📋 Выполненные задачи

### Задача 1 — Создан `placements.py` router

**Файл:** `src/api/routers/placements.py` (~400 строк)

**Prefix:** `/api/v1/placements`

**Tags:** `["placements"]`

---

## 🔨 Endpoints (9 штук)

### GET `/` — Список заявок

**Query params:**
- `role` (str): "advertiser" или "owner" (default: "advertiser")
- `status` (str|None): фильтр по статусу
- `limit` (int): 1-100 (default: 20)
- `offset` (int): >= 0 (default: 0)

**Returns:** `list[PlacementResponse]`

**Errors:** 400 (Invalid role)

---

### POST `/` — Создать заявку

**Body:** `PlacementCreateRequest`
```python
{
    "channel_id": int,
    "proposed_price": int,  # >= 100
    "post_text": str,       # 10-4096 символов
    "media_file_id": str|None,
    "scheduled_at": datetime
}
```

**Returns:** `PlacementResponse` (201)

**Errors:**
- 403: Advertiser is blocked
- 404: Channel not found
- 409: Channel not accepting ads
- 422: Validation error

---

### GET `/{placement_id}` — Получить заявку

**Returns:** `PlacementResponse`

**Errors:**
- 403: Access denied — not your placement
- 404: Placement not found

---

### POST `/{placement_id}/accept` — Принять заявку

**Описание:** Владелец принимает заявку

**Returns:** `PlacementResponse`

**Errors:**
- 403: Not channel owner
- 409: Invalid status transition

---

### POST `/{placement_id}/reject` — Отклонить заявку

**Body:** `RejectRequest`
```python
{
    "reason_code": str,
    "reason_text": str|None  # обязательно для code='other'
}
```

**Returns:** `PlacementResponse`

**Errors:**
- 403: Not channel owner
- 409: Invalid status transition
- 422: reason_text required for 'other'

---

### POST `/{placement_id}/counter` — Контр-предложение

**Body:** `CounterOfferRequest`
```python
{
    "counter_price": int,    # >= 100
    "counter_comment": str|None  # <= 500 символов
}
```

**Returns:** `PlacementResponse`

**Errors:**
- 403: Not channel owner
- 409: Max counter offer rounds reached

---

### POST `/{placement_id}/accept-counter` — Принять контр-предложение

**Returns:** `PlacementResponse`

**Errors:**
- 403: Not placement advertiser
- 409: Placement not in counter_offer status

---

### POST `/{placement_id}/pay` — Оплатить → эскроу

**Returns:** `PlacementResponse`

**Errors:**
- 400: Insufficient credits
- 403: Not placement advertiser
- 409: Placement not in pending_payment status

---

### DELETE `/{placement_id}` — Отменить заявку

**Returns:** `PlacementResponse` (200)

**Errors:**
- 403: Not placement advertiser
- 409: Cannot cancel in current status

---

## 📁 Созданные файлы

### `src/api/routers/placements.py` (~400 строк)

**Pydantic схемы:**
- `PlacementCreateRequest` — создание заявки
- `PlacementResponse` — ответ с данными заявки
- `CounterOfferRequest` — контр-предложение
- `RejectRequest` — отклонение с причиной

---

### `src/api/routers/channel_settings.py` (~250 строк)

**Prefix:** `/api/v1/channels/{channel_id}/settings`

**Tags:** `["channel-settings"]`

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Получить настройки канала |
| PATCH | `/` | Частичное обновление настроек |

**Pydantic схемы:**
- `ChannelSettingsResponse` — ответ с настройками
- `ChannelSettingsUpdateRequest` — partial update (все поля Optional)

**Валидация:**
- `start_time < end_time`
- `break_end_time > break_start_time`
- `sub_max_days > sub_min_days`
- Формат времени: HH:MM

---

### `src/api/routers/reputation.py` (~200 строк)

**Prefix:** `/api/v1/reputation`

**Tags:** `["reputation"]`

**Endpoints:**

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| GET | `/me` | any | Репутация текущего пользователя |
| GET | `/me/history` | any | История репутации пользователя |
| GET | `/{user_id}` | any | Публичная репутация (без ban-деталей) |
| GET | `/{user_id}/history` | admin | История репутации (только admin) |

**Pydantic схемы:**
- `ReputationResponse` — полная репутация (с ban-деталями)
- `PublicReputationResponse` — публичная (без ban)
- `ReputationHistoryEntry` — запись истории

---

## 🔄 Изменённые файлы

### `src/api/routers/__init__.py`

**Добавлено:**
```python
from src.api.routers.channel_settings import router as channel_settings
from src.api.routers.placements import router as placements
from src.api.routers.reputation import router as reputation

__all__ = [
    "auth",
    "campaigns",
    "analytics",
    "billing",
    "placements",
    "channel_settings",
    "reputation",
]
```

---

### `src/api/main.py`

**Добавлено:**
```python
from src.api.routers.channel_settings import router as channel_settings_router
from src.api.routers.placements import router as placements_router
from src.api.routers.reputation import router as reputation_router

# Регистрация роутеров
app.include_router(placements_router, tags=["Placements"])
app.include_router(channel_settings_router, tags=["Channel Settings"])
app.include_router(reputation_router, tags=["Reputation"])
```

---

## ✅ Чеклист завершения

```
[✅] Все 11 файлов из step_0 прочитаны до начала
[✅] Каждый роутер: никакой бизнес-логики, только вызовы сервиса
[✅] Pydantic-схемы объявлены в том же файле что и роутер
[✅] Все endpoints возвращают типизированные Pydantic-схемы
[✅] HTTPException с корректными status_code везде
[✅] Зависимости (сессия, current_user) через FastAPI Depends
[✅] PATCH /channel_settings — partial update (только переданные поля)
[✅] GET /reputation/{user_id} — публичные поля без ban-деталей
[✅] GET /reputation/{user_id}/history — только admin
[✅] src/api/routers/__init__.py сохранил все старые роутеры
```

---

## 🔍 Статический анализ

| Команда | Результат |
|---------|-----------|
| `python -c "from src.api.routers.placements import router; print('Placements OK')"` | ✅ Placements OK |
| `python -c "from src.api.routers.channel_settings import router; print('ChannelSettings OK')"` | ✅ ChannelSettings OK |
| `python -c "from src.api.routers.reputation import router; print('Reputation OK')"` | ✅ Reputation OK |
| `python -c "from src.api.main import app; print('API OK')"` | ✅ API OK |
| `ruff check src/api/routers/ --fix` | ✅ All checks passed! |
| **Бот запущен** | ✅ Polling active |

---

## 📊 Итоговая статистика

| Категория | Количество |
|-----------|------------|
| **Роутеров создано** | 3 |
| **Endpoints всего** | 15 (9 + 2 + 4) |
| **Pydantic схем** | 9 |
| **Файлов изменено** | 2 |
| **Строк кода** | ~750 |

---

## 🏗️ API структура (актуальная)

```
/api
├── /auth/*              # Auth (JWT via Telegram)
├── /campaigns/*         # Campaigns CRUD
├── /analytics/*         # Analytics
├── /billing/*           # Billing operations
├── /*                   # Channels catalog
├── /v1/placements/*     # ✅ PlacementRequest CRUD (Этап 5)
├── /v1/channels/{id}/settings  # ✅ ChannelSettings CRUD (Этап 5)
└── /v1/reputation/*     # ✅ Reputation (Этап 5)
```

---

## 🎯 Следующие шаги

**Готово к использованию:**
- Mini App может использовать новые endpoints
- Тестирование интеграции с bot handlers
- Документация API (OpenAPI/Swagger)

---

**Версия:** 1.0
**Дата:** 2026-03-10
**Статус:** ✅ ЗАВЕРШЕНО
