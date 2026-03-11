# Этап 7: Завершение — Celery SLA таймеры для PlacementRequest флоу

**Дата:** 2026-03-10
**Тип задачи:** NEW_FEATURE
**Принцип:** CLEAN_RESULT — идемпотентные задачи, без дублей, правильный asyncio паттерн
**Статус:** ✅ ЗАВЕРШЁНО
**Файлы создано:** 1
**Файлы изменено:** 3

---

## 📋 Выполненные задачи

### Задача 1 — Создан `src/tasks/placement_tasks.py`

**Файл:** `src/tasks/placement_tasks.py` (~650 строк)

**Задачи (6):**

| ID | Название | Очередь | Описание |
|----|----------|---------|----------|
| T1 | `check_owner_response_sla` | worker_critical | Проверка SLA ответа владельца (24ч) |
| T2 | `check_payment_sla` | worker_critical | Проверка SLA оплаты (24ч) |
| T3 | `check_counter_offer_sla` | worker_critical | Проверка SLA контр-предложения (24ч) |
| T4 | `publish_placement` | worker_critical | Публикация поста в запланированное время |
| T5 | `retry_failed_publication` | worker_background | Повторная попытка через 1ч |
| T6 | `schedule_placement_publication` | worker_critical | Хелпер для планирования |

---

## 🔨 Детали задач

### T1: check_owner_response_sla

**Триггер:** Beat каждые 5 минут

**Логика:**
1. `repo.get_expired_pending_owner()` — все pending_owner с expires_at < now
2. Для каждого placement:
   - `status → 'failed'`
   - Возврат advertiser 100% (ещё не в эскроу)
   - ReputationService: owner не получает штраф
   - `notify_advertiser('⏱ Владелец не ответил. Средства возвращены')`
   - `notify_owner('⚠️ Заявка #{id} просрочена')`

**Дедупликация:** `task_key = placement_task:check_owner_response_sla:{placement_id}`, TTL=3600s

---

### T2: check_payment_sla

**Триггер:** Beat каждые 5 минут

**Логика:**
1. `repo.get_expired_pending_payment()` — все pending_payment с expires_at < now
2. Для каждого placement:
   - `status → 'cancelled'`
   - `ReputationService.on_cancel_after_confirmation() → -20` к репутации
   - `notify_advertiser('⏱ Время оплаты истекло. Заявка отменена. Репутация -20')`
   - `notify_owner('ℹ️ Рекламодатель не оплатил заявку #{id} вовремя')`

**Дедупликация:** `task_key = placement_task:check_payment_sla:{placement_id}`, TTL=3600s

---

### T3: check_counter_offer_sla

**Триггер:** Beat каждые 5 минут

**Логика:**
1. `repo.get_expired_counter_offer()` — все counter_offer с expires_at < now
2. Для каждого placement:
   - `status → 'failed'`
   - Возврат advertiser 100% (не в эскроу)
   - Репутация не меняется
   - `notify_advertiser('⏱ Переговоры истекли. Заявка отменена')`
   - `notify_owner('⏱ Контр-предложение по заявке #{id} не было принято вовремя')`

**Дедупликация:** `task_key = placement_task:check_counter_offer_sla:{placement_id}`, TTL=3600s

---

### T4: publish_placement

**Триггер:** `apply_async(eta=scheduled_at)` — планируется при переходе в escrow

**Логика:**
1. Проверить `status == 'escrow'` — иначе skip
2. Отправить пост через `bot.send_message` / `bot.send_photo`
3. Если успех:
   - `status → 'published'`
   - `ReputationService.on_publication()` (+1 advertiser, +1 owner)
   - `BillingService.release_escrow_for_placement()` → owner 80%, платформа 20%
   - `notify_advertiser('✅ Пост опубликован в @channel!')`
   - `notify_owner('✅ Пост опубликован. Начислено {owner_payout} кр')`
4. Если ошибка Telegram:
   - `status → 'failed'`
   - `refund 50%`
   - `notify_advertiser('❌ Ошибка публикации. Возврат 50%')`
   - `notify_owner('❌ Не удалось опубликовать пост #{id}')`

**Дедупликация:** `task_key = placement_task:publish_placement:{placement_id}`, TTL=300s

---

### T5: retry_failed_publication

**Триггер:** T4 при ошибке Telegram → `apply_async(countdown=3600)`

**Логика:**
1. Проверить `status == 'failed'` и `retry_count < 1`
2. Повторить логику T4
3. Если снова неудача → финальный 'failed', refund 50%

**Дедупликация:** `task_key = placement_task:retry_failed_publication:{placement_id}`, TTL=600s

---

### T6: schedule_placement_publication

**Триггер:** Вызывается из PlacementRequestService при переходе в escrow

**Логика:**
```python
publish_placement.apply_async(
    args=[placement_id],
    eta=scheduled_at,
    task_id=f'publish:{placement_id}'
)
```

---

## 📊 SLA константы

```python
SLA_OWNER_RESPONSE_HOURS: int = 24
SLA_PAYMENT_HOURS: int = 24
SLA_COUNTER_OFFER_HOURS: int = 24
SLA_PUBLISH_RETRY_HOURS: int = 1
SCORE_AFTER_BAN: float = 2.0
REFUND_AFTER_ESCROW_PCT: int = 50
BEAT_CHECK_INTERVAL_MINUTES: int = 5
```

---

## 🔄 asyncio паттерн

**Обязательный паттерн для всех async вызовов в Celery:**
```python
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    result = loop.run_until_complete(_async_logic())
finally:
    loop.close()
return result
```

---

## 🛡️ Дедупликация (CR1 из RACE_CONDITIONS_AUDIT)

**Обязателен для КАЖДОЙ задачи:**
```python
task_key = f'placement_task:{task_name}:{placement_id}'
if redis_client.exists(task_key):
    return {'skipped': 'Already running'}
redis_client.setex(task_key, TTL_SECONDS, self.request.id)
```

**TTL по задачам:**
| Задача | TTL (сек) |
|--------|-----------|
| check_owner_response_sla | 3600 |
| check_payment_sla | 3600 |
| check_counter_offer_sla | 3600 |
| publish_placement | 300 |
| retry_failed_publication | 600 |

---

## 📁 Изменённые файлы

### `src/db/repositories/placement_request_repo.py`

**Добавлено 3 метода:**
- `get_expired_pending_owner()` — pending_owner с expires_at < now
- `get_expired_pending_payment()` — pending_payment с expires_at < now
- `get_expired_counter_offer()` — counter_offer с expires_at < now

---

### `src/tasks/celery_app.py`

**Добавлено в include:**
```python
"src.tasks.placement_tasks",
```

---

### `src/tasks/celery_config.py`

**Добавлено в BEAT_SCHEDULE:**
```python
"placement-check-owner-sla": {
    "task": "placement:check_owner_response_sla",
    "schedule": crontab(minute="*/5"),
    "options": {"queue": "worker_critical", "expires": 60},
},
"placement-check-payment-sla": {
    "task": "placement:check_payment_sla",
    "schedule": crontab(minute="*/5"),
    "options": {"queue": "worker_critical", "expires": 60},
},
"placement-check-counter-sla": {
    "task": "placement:check_counter_offer_sla",
    "schedule": crontab(minute="*/5"),
    "options": {"queue": "worker_critical", "expires": 60},
},
```

**Добавлено в TASK_ROUTES:**
```python
"placement.*": {"queue": "worker_critical"},
"src.tasks.placement_tasks.*": {"queue": "worker_critical"},
```

---

## ✅ Чеклист завершения

```
[✅] Все 10 файлов из step_0 прочитаны до начала
[✅] asyncio паттерн взят из billing_tasks.py — new_event_loop()
[✅] CR1 дедупликация реализована для КАЖДОЙ задачи
[✅] 3 новых метода в PlacementRequestRepo добавлены
[✅] 3 записи в beat_schedule добавлены
[✅] placement_tasks добавлен в celery_app include
[✅] TASK_ROUTES обновлён
[✅] expires=60 добавлен для всех SLA checks
[✅] Ruff check → 0 ошибок
[✅] Все импорты работают
```

---

## 🔍 Статический анализ

| Команда | Результат |
|---------|-----------|
| `python -c "from src.tasks.placement_tasks import ...; print('OK')"` | ✅ All tasks imported OK |
| `ruff check src/tasks/placement_tasks.py --fix` | ✅ 6 errors fixed |
| **Файлов создано** | 1 |
| **Файлов изменено** | 3 |
| **Строк кода** | ~650 |

---

## 📊 Итоговая статистика

| Категория | Количество |
|-----------|------------|
| **Celery задач** | 6 |
| **Repo методов** | 3 |
| **Beat записей** | 3 |
| **Строк кода** | ~650 |

---

## 🏗️ Celery очереди (актуально)

```
Очереди:
├── worker_critical    # ✅ placement tasks, billing
├── mailing            # рассылки, уведомления
├── parser             # парсинг каналов
├── cleanup            # очистка старых данных
├── rating             # пересчёт рейтингов
└── gamification       # XP, бейджи
```

---

## 🎯 Следующие шаги

**Готово к запуску:**
```bash
# Запустить worker для critical очереди
celery -A src.tasks.celery_app worker -Q worker_critical -l info -c 4

# Запустить Beat
celery -A src.tasks.celery_app beat -l info
```

**Мониторинг:**
- Flower: http://localhost:5555
- Задачи: `placement:*`

---

**Версия:** 1.0
**Дата:** 2026-03-10
**Статус:** ✅ ЗАВЕРШЕНО
