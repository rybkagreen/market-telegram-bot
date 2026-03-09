# RACE CONDITIONS & FSM LEAKS AUDIT REPORT

**Проект:** Market Telegram Bot (RekHarborBot)  
**Дата аудита:** 2026-03-10  
**Аудитор:** Qwen Code  
**Статус:** ✅ ЗАВЕРШЕНО

---

## 📊 ОБЗОР НАЙДЕННЫХ ПРОБЛЕМ

| Категория | Критические | Высокие | Средние | Низкие | Всего |
|-----------|-------------|---------|---------|--------|-------|
| Race Conditions (БД) | 0 | 2 | 3 | - | 5 |
| FSM утечки | 0 | 1 | 2 | - | 3 |
| Celery задачи | 0 | 1 | 2 | 1 | 4 |
| Redis кэш | 0 | 0 | 1 | 1 | 2 |
| Callback Query | 0 | 0 | 1 | - | 1 |
| Транзакции | 0 | 0 | 1 | - | 1 |
| **ИТОГО** | **0** | **4** | **10** | **2** | **16** |

---

## 1. RACE CONDITIONS В БД

### RC1 — Прямое изменение `user.credits` без блокировки (HIGH)

**Файлы:**
- `src/core/services/xp_service.py:546`
- `src/core/services/badge_service.py:206`

**Проблема:**
```python
# xp_service.py:546
user.credits += earned_bonus["credits"]  # ❌ Нет блокировки

# badge_service.py:206
user.credits += badge.credits_reward  # ❌ Нет блокировки
```

**Риск:** При одновременном начислении кредитов (например, несколько достижений одновременно) возможны потери обновлений.

**Сценарий гонки:**
```
Time  | Поток A                  | Поток B
------|--------------------------|--------------------------
T1    | read user.credits = 100  |
T2    |                          | read user.credits = 100
T3    | credits += 50 → 150      |
T4    |                          | credits += 30 → 130
T5    | write 150                |
T6    |                          | write 130 (потеряно 50!)
```

**Решение:**
```python
# Вариант 1: with_for_update()
stmt = select(User).where(User.id == user_id).with_for_update()
result = await session.execute(stmt)
user = result.scalar_one_or_none()
user.credits += earned_bonus["credits"]

# Вариант 2: атомарное UPDATE (как в user_repo.py:361)
await session.execute(
    update(User)
    .where(User.id == user_id)
    .values(credits=User.credits + delta)
)
```

**Приоритет:** 🟠 HIGH

---

### RC2 — Обновление баланса в billing_service.py (MEDIUM)

**Файл:** `src/core/services/billing_service.py:325, 557, 664, 777`

**Проблема:**
```python
# billing_service.py:325
user.credits -= plan_price  # ❌ Прямое изменение

# billing_service.py:557
user.credits -= int(campaign.cost)  # ❌ Прямое изменение
```

**Хорошая новость:** В billing_service.py используется `session.begin()` с `with_for_update()` (строка 300), что обеспечивает блокировку.

**Риск:** Низкий — транзакция защищает от гонок, но прямое изменение атрибутов менее явно, чем атомарный UPDATE.

**Рекомендация:** Использовать явный `update()` для консистентности кода.

**Приоритет:** 🟡 MEDIUM

---

### RC3 — Campaign status update без проверки (MEDIUM)

**Файл:** `src/db/repositories/campaign_repo.py:146`

**Проблема:**
```python
# campaign_repo.py:146
query = select(Campaign).where(Campaign.status == CampaignStatus.RUNNING)
# Нет проверки на одновременное изменение статуса
```

**Риск:** Два воркера могут одновременно начать обработку одной кампании.

**Текущая защита:** Campaign meta хранит `celery_task_id`, что позволяет отследить дублирование.

**Рекомендация:** Добавить `with_for_update()` при изменении статуса кампании.

**Приоритет:** 🟡 MEDIUM

---

### RC4 — MailingLog status update (LOW)

**Файл:** `src/db/repositories/log_repo.py:217, 275`

**Проблема:** Обновление статуса размещения без явной блокировки.

**Риск:** Низкий — каждое размещение обрабатывается один раз.

**Приоритет:** 🟢 LOW

---

### RC5 — User.ai_generations_used increment (MEDIUM)

**Файл:** `src/db/repositories/user_repo.py:371`

**Проблема:**
```python
# user_repo.py:371
await session.execute(
    update(User)
    .where(User.id == user_id)
    .values(ai_generations_used=User.ai_generations_used + 1)
)
```

**Хорошая новость:** Используется атомарный UPDATE — это правильно!

**Риск:** Отсутствует — реализовано корректно.

**Приоритет:** 🟢 LOW (информационный — проблем нет)

---

## 2. FSM STATE УТЕЧКИ

### FSM1 — Отсутствие timeout на состояния (HIGH)

**Файлы:** Все FSM handlers (`src/bot/handlers/campaigns.py`, `feedback.py`, `admin.py`, etc.)

**Проблема:**
- Нет middleware для автоматического сброса состояния после timeout
- Пользователь может начать создание кампании → уйти → состояние остаётся активным
- При возврате через N часов бот ожидает продолжения диалога

**Сценарий утечки:**
```
1. Пользователь: /campaign → state=waiting_topic
2. Пользователь уходит на 2 часа
3. Пользователь: /start → state НЕ сброшен (строка 207 проверяет has_channels/campaigns)
4. Пользователь в неопределённом состоянии
```

**Текущая защита:**
- `start.py:207, 228` — `state.clear()` при наличии каналов/кампаний
- `start.py:536` — `state.clear()` для новых пользователей
- 60 вызовов `state.clear()` в коде

**Риск:** Средний — большинство сценариев покрыты, но нет универсального timeout.

**Рекомендация:**
```python
# Добавить middleware для FSM timeout
class FSMTimeoutMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        state = data.get("state")
        if state:
            fsm_data = await state.get_data()
            if "expires_at" in fsm_data:
                if datetime.now() > fsm_data["expires_at"]:
                    await state.clear()
        return await handler(event, data)
```

**Приоритет:** 🟠 HIGH

---

### FSM2 — /start не всегда сбрасывает состояние (MEDIUM)

**Файл:** `src/bot/handlers/start.py:200-230`

**Проблема:**
```python
# start.py:207
if user_context.has_channels or user_context.has_campaigns:
    await state.clear()  # ✅ Сбрасывает
else:
    # ❌ Не сбрасывает — показывает меню без онбординга
    await send_banner_with_menu(...)
    return  # ← state остаётся!
```

**Сценарий:**
1. Пользователь в состоянии `waiting_topic`
2. Пользователь: `/start`
3. У пользователя нет каналов/кампаний → return без `state.clear()`
4. Состояние остаётся активным

**Решение:**
```python
# start.py:207-228
if user_context.has_channels or user_context.has_campaigns:
    await state.clear()
else:
    await state.clear()  # ← Добавить
    await send_banner_with_menu(...)
    return
```

**Приоритет:** 🟡 MEDIUM

---

### FSM3 — Отсутствие глобального /cancel handler (MEDIUM)

**Файл:** Не найден отдельный файл `/cancel` handler

**Проблема:**
- Нет универсальной команды `/cancel` для сброса состояния
- Каждая FSM должна иметь свою кнопку "Отмена"
- Если пользователь не находит кнопку — застревает в состоянии

**Текущая защита:**
- В каждом FSM диалоге есть кнопка "✖ Отмена"
- `campaign_create_ai.py:649` — `state.set_state(None)`

**Рекомендация:** Добавить глобальный `/cancel` handler:
```python
@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: StateProxy) -> None:
    await state.clear()
    await message.answer("Диалог отменён")
```

**Приоритет:** 🟡 MEDIUM

---

## 3. CELERY ЗАДАЧИ БЕЗ ИДЕМПОТЕНТНОСТИ

### CR1 — Отсутствие проверки duplicate task_id (HIGH)

**Файл:** `src/tasks/mailing_tasks.py:30`

**Проблема:**
```python
@celery_app.task(bind=True, base=BaseTask, name="mailing:send_campaign")
def send_campaign(self, campaign_id: int) -> dict[str, Any]:
    # ❌ Нет проверки: уже обрабатывается ли эта кампания?
```

**Сценарий гонки:**
1. Пользователь запускает кампанию → `send_campaign.delay(campaign_id)`
2. Пользователь нажимает "Запустить" ещё раз (двойной клик)
3. Два воркера начинают одну кампанию
4. Дублирование отправок, двойное списание кредитов

**Текущая защита:**
- Campaign.meta хранит `celery_task_id` (строка 197)
- `cabinet.py:692, 780` — сохранение task_id
- `cabinet.py:727-736` — проверка task_id при отмене

**Недостаток:** Нет проверки в начале задачи `send_campaign`.

**Решение:**
```python
@celery_app.task(bind=True, base=BaseTask, name="mailing:send_campaign")
def send_campaign(self, campaign_id: int) -> dict[str, Any]:
    # Проверка на дубликат
    task_key = f"campaign_running:{campaign_id}"
    if redis_client.exists(task_key):
        return {"skipped": "Already running"}
    redis_client.setex(task_key, 3600, self.request.id)
    # ... остальная логика
```

**Приоритет:** 🟠 HIGH

---

### CR2 — notify_user без дедупликации (MEDIUM)

**Файл:** `src/tasks/notification_tasks.py:180`

**Проблема:**
```python
@celery_app.task(bind=True, base=BaseTask, name="mailing:notify_user")
def notify_user(self, user_id: int, message: str, ...) -> bool:
    # ❌ Нет проверки: не отправлено ли уже такое уведомление?
```

**Риск:** При повторном вызове — дублирование уведомлений.

**Текущая защита:** NotificationRepository создаёт запись в БД — можно проверить перед отправкой.

**Рекомендация:** Добавить проверку уникальности по `(user_id, message, notification_type)`.

**Приоритет:** 🟡 MEDIUM

---

### CR3 — Отсутствие unique=True для периодических задач (MEDIUM)

**Файл:** `src/tasks/celery_config.py` (Beat расписание)

**Проблема:**
```python
"check-low-balance": {
    "task": "src.tasks.notification_tasks.check_low_balance",
    "schedule": crontab(minute=0),
    # ❌ Нет "options": {"unique": True}
},
```

**Риск:** Если задача выполняется дольше 1 часа — следующий запуск создаст параллельное выполнение.

**Хорошая новость:** Celery Beat по умолчанию не запускает задачу, если предыдущая ещё выполняется (для одной очереди).

**Рекомендация:** Добавить `expires=60` для задач с `crontab(minute=0)`.

**Приоритет:** 🟡 MEDIUM

---

### CR4 — parser:refresh_chat_database без rate limit (LOW)

**Файл:** `src/tasks/parser_tasks.py:943`

**Проблема:**
```python
@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    # ✅ Есть retry логика
)
def refresh_chat_database(...)
```

**Хорошая новость:**
- `max_retries=3` ✅
- `autoretry_for=(Exception,)` ✅
- `with_for_update()` используется ✅

**Риск:** Отсутствует — задача реализована корректно.

**Приоритет:** 🟢 LOW (информационный — проблем нет)

---

## 4. REDIS RACE CONDITIONS

### RR1 — Отсутствие атомарных INCR/DECR (MEDIUM)

**Файлы:**
- `src/bot/middlewares/throttling.py:74`
- `src/utils/telegram/parser.py:373`
- `src/core/services/ai_service.py:345`

**Проблема:**
```bash
$ grep -rn "INCR\|DECR\|setnx\|SETNX" src/ --include="*.py"
# (пусто) — нет атомарных операций
```

**Текущее использование Redis:**
- `throttling.py:74` — `setex(key, 1, "1")` ✅ (TTL есть)
- `parser.py:360, 373` — `get/setex` ✅ (TTL есть)
- `ai_service.py:335, 345` — `get/setex` ✅ (TTL есть)

**Риск:** Низкий — все операции используют `setex` с TTL.

**Рекомендация:** Для счётчиков (rate limiting) использовать `INCR` вместо `get` + `set`.

**Приоритет:** 🟡 MEDIUM

---

### RR2 — Кэш без инвалидации при обновлении данных (LOW)

**Файл:** `src/core/services/analytics_service.py:96-150`

**Проблема:**
```python
# analytics_service.py:163-167
cache_key = self._get_cache_key(f"campaign:{campaign_id}")
cached = await self._check_cache(cache_key)
if cached:
    return CampaignStats(**cached)  # ❌ Не проверяет актуальность
```

**Риск:** Устаревшие данные кэша после обновления кампании.

**Хорошая новость:** TTL кэша ограничивает время жизни устаревших данных.

**Приоритет:** 🟢 LOW

---

## 5. CALLBACK QUERY ПРОБЛЕМЫ

### CB1 — Потенциальный double-click на кнопках (MEDIUM)

**Файлы:** Все callback handlers (`src/bot/handlers/*.py`)

**Проблема:**
- Нет защиты от двойного нажатия на кнопку
- Telegram позволяет отправить 2 callback_query за 1 секунду

**Сценарий:**
1. Пользователь: "Запустить кампанию" (двойной клик)
2. Два callback_query → два `send_campaign.delay()`
3. Две параллельные рассылки

**Текущая защита:**
- ThrottlingMiddleware (`throttling.py:60-74`) — 0.5 секунды между запросами
- 252 вызова `callback.answer()` на 251 handler — все обработчики отвечают ✅

**Недостаток:** 0.5 секунды может быть недостаточно для финансовых операций.

**Рекомендация:**
```python
# Для критических кнопок (оплата, запуск кампании)
# Добавить проверку в handler:
async def launch_campaign_callback(callback: CallbackQuery, ...):
    # Проверка: не запущена ли уже кампания
    if campaign.status == "running":
        await callback.answer("Кампания уже запущена", show_alert=True)
        return
    # ... запуск
```

**Приоритет:** 🟡 MEDIUM

---

## 6. ТРАНЗАКЦИИ И БЛОКИРОВКИ

### TX1 — Непоследовательное использование with_for_update() (MEDIUM)

**Файлы:**
- ✅ `src/core/services/billing_service.py:300, 533, 541, 618, 635, 642, 741, 760, 767`
- ❌ `src/core/services/xp_service.py:546`
- ❌ `src/core/services/badge_service.py:206`

**Проблема:**
- billing_service.py использует `with_for_update()` ✅
- xp_service.py и badge_service.py — нет ❌

**Хорошая новость:**
```bash
$ grep -rn "with_for_update" src/ --include="*.py"
# 11 находок — блокировки используются
```

**Рекомендация:** Унифицировать использование `with_for_update()` во всех сервисах.

**Приоритет:** 🟡 MEDIUM

---

## 7. ПОЛОЖИТЕЛЬНЫЕ НАХОДКИ ✅

### Что реализовано правильно:

1. **Транзакции в billing_service.py:**
   ```python
   async with async_session_factory() as session, session.begin():
       stmt = select(User).where(User.id == user_id).with_for_update()
       # ✅ Правильный паттерн
   ```

2. **Атомарный UPDATE в user_repo.py:**
   ```python
   await session.execute(
       update(User)
       .where(User.id == user_id, User.credits + delta >= 0)
       .values(credits=User.credits + delta)
   )
   # ✅ Атомарная операция с проверкой
   ```

3. **Task ID tracking:**
   - Campaign.meta хранит `celery_task_id`
   - Отмена кампании проверяет task_id

4. **FSM cleanup:**
   - 60 вызовов `state.clear()` в коде
   - Кнопка "Отмена" в каждом FSM диалоге

5. **Redis TTL:**
   - Все `setex` операции имеют TTL
   - Throttling: 1 секунда
   - Parser cache: 3600 секунд
   - AI cache: 3600 секунд

6. **Callback answer:**
   - 252 вызова `callback.answer()` на 251 handler
   - Все обработчики отвечают на callback

---

## 8. РЕКОМЕНДАЦИИ

### Критические (P0) — Исправить немедленно:

- [ ] **RC1:** Добавить `with_for_update()` в `xp_service.py:546` и `badge_service.py:206`
- [ ] **FSM1:** Добавить FSM timeout middleware
- [ ] **CR1:** Добавить проверку duplicate task_id в `send_campaign()`

### Важные (P1) — Исправить в течение спринта:

- [ ] **FSM2:** Добавить `state.clear()` в `start.py:220` (else ветка)
- [ ] **FSM3:** Добавить глобальный `/cancel` handler
- [ ] **CR2:** Добавить дедупликацию в `notify_user()`
- [ ] **CB1:** Добавить защиту от double-click для критических кнопок

### Средние (P2) — Исправить в следующем спринте:

- [ ] **RC2:** Использовать явный `update()` вместо прямого изменения атрибутов
- [ ] **RC3:** Добавить `with_for_update()` при изменении статуса кампании
- [ ] **CR3:** Добавить `expires=60` для периодических задач Beat
- [ ] **RR1:** Использовать `INCR` для счётчиков rate limiting
- [ ] **TX1:** Унифицировать использование `with_for_update()`

### Низкие (P3) — Улучшения:

- [ ] **RR2:** Добавить инвалидацию кэша при обновлении данных
- [ ] **RC4:** Документировать mailing_log status update логику

---

## 9. ИТОГОВАЯ ОЦЕНКА РИСКОВ

| Категория | Текущий риск | После исправления P0 | После исправления P1 |
|-----------|--------------|---------------------|---------------------|
| Race Conditions (БД) | 🟠 Средний | 🟢 Низкий | 🟢 Низкий |
| FSM утечки | 🟠 Средний | 🟢 Низкий | 🟢 Низкий |
| Celery задачи | 🟠 Средний | 🟢 Низкий | 🟢 Низкий |
| Redis кэш | 🟢 Низкий | 🟢 Низкий | 🟢 Низкий |
| Callback Query | 🟡 Низкий | 🟡 Низкий | 🟢 Низкий |
| Транзакции | 🟡 Низкий | 🟢 Низкий | 🟢 Низкий |

**Общий риск:** 🟠 **СРЕДНИЙ** → После исправлений P0+P1: 🟢 **НИЗКИЙ**

---

## 10. ПЛАН ДЕЙСТВИЙ

### Неделя 1 (P0):
1. Исправить RC1 — `with_for_update()` в xp_service.py и badge_service.py
2. Исправить FSM1 — добавить timeout middleware
3. Исправить CR1 — проверка duplicate task_id в send_campaign()

### Неделя 2 (P1):
1. Исправить FSM2 — `state.clear()` в start.py
2. Добавить /cancel handler (FSM3)
3. Добавить дедупликацию в notify_user() (CR2)
4. Добавить защиту от double-click (CB1)

### Неделя 3-4 (P2):
1. Рефакторинг RC2, RC3
2. Добавить expires для Beat задач (CR3)
3. Использовать INCR для rate limiting (RR1)
4. Унифицировать with_for_update() (TX1)

---

**АУДИТ ЗАВЕРШЁН:** 2026-03-10  
**СЛЕДУЮЩИЙ АУДИТ:** Рекомендуется через 3 месяца или после крупных изменений

---

**ИСПОЛНИТЕЛЬ:** Qwen Code  
**ФАЙЛ ОТЧЁТА:** `docs/audit/reports/RACE_CONDITIONS_AUDIT.md`
