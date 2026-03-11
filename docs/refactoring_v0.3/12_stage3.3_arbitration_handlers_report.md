# Этап 3.3: Завершение — Handlers арбитража (сторона владельца)

**Дата:** 2026-03-10
**Спринт:** 6 (Channel Owner & Advertiser v2.0)
**Статус:** ✅ ЗАВЕРШЁНО
**Файлы создано:** 1
**Файлы изменено:** 0
**Строк кода:** ~680

---

## 📋 Выполненные задачи

### Задача 1 — Реализован `arbitration.py` (handlers владельца)

**Файл:** `src/bot/handlers/placement/arbitration.py` (680 строк)

**Callback prefix:** `arbitration:*`

---

## 🔨 Реализованные handlers (10 штук)

### H1 — Список входящих заявок

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_arbitration_list()` | `arbitration:list` | Список pending_owner заявок владельца |

**Логика:**
- Получить user по telegram_id
- `repo.get_pending_for_owner(user_id)` — все pending_owner заявки
- Если пусто — "Нет входящих заявок"
- Показать список через `get_arbitration_list_kb(requests)`

---

### H2 — Карточка заявки

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_view_request()` | `arbitration:view:{placement_id}` | Детали заявки |

**Текст карточки:**
```
📋 Заявка #{id} от рекламодателя

📺 Канал: @{channel_username}
💰 Предложенная цена: {proposed_price} кр → вы получите: {owner_payout} кр
📅 Желаемая дата: {scheduled_at}
⏱ Истекает через: {time_left}
💱 Раунд переговоров: {counter_offer_count}/{MAX_COUNTER_OFFER_ROUNDS}

━━━━━━━━━━━━━━━━━━━━
📝 ТЕКСТ ПОСТА:
{post_text[:800]}
```

**Кнопки:**
- ✅ Принять → `arbitration:accept:{id}`
- ❌ Отклонить → `arbitration:reject:{id}`
- 💱 Контр-предложение → `arbitration:counter:{id}`
- ◀️ Назад → `arbitration:list`

---

### H3 — Принять заявку

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_accept()` | `arbitration:accept:{placement_id}` | Владелец принимает заявку |

**Логика:**
- Проверить `channel.owner_user_id == user.id`
- Проверить `status in (pending_owner, counter_offer)`
- Вызвать `service.owner_accept(placement_id, owner_id)`
- Показать: "✅ Заявка принята! Ожидайте оплаты (до 24 ч)"

---

### H4 — Меню отклонения

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_reject_menu()` | `arbitration:reject:{placement_id}` | Выбор причины отказа |

**Причины (inline кнопки):**
- 🚫 Не моя тематика → `topic_mismatch`
- 📝 Низкое качество текста → `low_quality`
- 📅 Неудобное время → `bad_timing`
- 💰 Цена слишком низкая → `low_price`
- 🔒 Временно не принимаю → `paused`
- ✍️ Другая причина → `other`

---

### H4a — Выбор причины

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_reject_reason_select()` | `arbitration:reject_reason:{id}:{code}` | Обработка выбора |

**Логика:**
- Если `code == 'other'` → FSM `waiting_rejection_reason`
- Иначе → вызвать `handle_reject_execute()` с предустановленной причиной

---

### H4b — Ввод текстовой причины

| Метод | State | Описание |
|-------|-------|----------|
| `process_rejection_reason_text()` | `ArbitrationStates.waiting_rejection_reason` | Валидация текста |

**Валидация:**
- `len(text) >= 10` — иначе ошибка
- `re.search(r'[а-яёa-z]', text)` — должна содержать буквы
- Нет 5+ одинаковых символов подряд
- Нет в чёрном списке (asdf, 1234, qwerty, нет, no)

---

### H4c — Выполнение отклонения

| Метод | Тип | Описание |
|-------|-----|----------|
| `handle_reject_execute()` | internal function | Применить отклонение |

**Логика:**
- Вызвать `service.owner_reject(placement_id, owner_id, reason)`
- Если невалидный отказ → `ReputationService.on_invalid_rejection()`
- Показать результат + текущий score репутации
- `state.clear()`

**Штрафы за невалидный отказ:**
- 1й: `-10` к репутации
- 2й: `-15`
- 3й+: `-20` + бан 7 дней

---

### H5 — Контр-предложение

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_counter_offer_init()` | `arbitration:counter:{placement_id}` | Начало флоу |

**Логика:**
- Проверить `counter_offer_count < MAX_COUNTER_OFFER_ROUNDS (3)`
- Проверить `status == pending_owner`
- FSM: `state.update_data(placement_id)`
- Перейти в `waiting_counter_price`

---

### H5a — Ввод цены

| Метод | State | Описание |
|-------|-------|----------|
| `process_counter_price()` | `ArbitrationStates.waiting_counter_price` | Ввод новой цены |

**Валидация:**
- `text.isdigit()` — иначе ошибка
- `int(text) >= 100` — иначе ошибка
- Перейти в `waiting_counter_comment`

---

### H5b — Ввод комментария

| Метод | State | Описание |
|-------|-------|----------|
| `process_counter_comment()` | `ArbitrationStates.waiting_counter_comment` | Комментарий или /skip |

**Логика:**
- Если `/skip` → `counter_comment = None`
- Иначе → `text[:500]`
- Вызвать `service.owner_counter_offer()`
- `state.clear()`
- Показать: "💱 Контр-предложение отправлено!"

---

### H6 — Точка входа из меню

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_my_requests()` | `main:my_requests` | Алиас на `arbitration:list` |

**Логика:**
- Вызвать `handle_arbitration_list(callback)` напрямую

---

## 📊 Бизнес-константы

```python
REJECT_INVALID_DELTA_1: float = -10.0
REJECT_INVALID_DELTA_2: float = -15.0
REJECT_INVALID_DELTA_3: float = -20.0
REJECT_FREQUENT_DELTA: float = -5.0
BAN_DURATION_DAYS: int = 7
PERMANENT_BAN_VIOLATIONS: int = 5
MAX_COUNTER_OFFER_ROUNDS: int = 3
SLA_OWNER_RESPONSE_HOURS: int = 24
OWNER_PAYOUT_PCT: int = 80
PLATFORM_FEE_PCT: int = 20
REJECTION_REASON_MIN_LEN: int = 10
```

---

## 🔄 FSM States (3 состояния)

```python
class ArbitrationStates(StatesGroup):
    waiting_rejection_reason = State()  # ввод комментария к отклонению
    waiting_counter_price = State()     # ввод новой цены
    waiting_counter_comment = State()   # комментарий к контр-предложению
```

---

## 🛠️ Вспомогательные функции

### `get_time_left(expires_at: datetime) -> str`

Получить оставшееся время до истечения:
- Если истекло → "ИСТЕКЛО"
- Иначе → "Xч Yмин"

### `validate_rejection_reason(text: str) -> tuple[bool, str]`

Валидировать причину отклонения:
- Минимум 10 символов
- Должна содержать буквы
- Нет 5+ одинаковых символов
- Нет в чёрном списке

Returns: `(is_valid, error_message)`

### `check_channel_owner(callback, channel) -> bool`

Проверить что пользователь — владелец канала.

### `handle_reject_execute_internal()`

Внутренняя функция выполнения отклонения (вызывается из H4a и H4b).

---

## ✅ Чеклист завершения

```
[✅] Прочитаны все 11 файлов из step_0
[✅] Все callbacks начинаются с arbitration:
[✅] main:my_requests обрабатывается как алиас arbitration:list
[✅] Нет пересечений с placement:*, ch_cfg:*, channel_add:*
[✅] Константы объявлены в начале файла
[✅] ArbitrationStates объявлены в файле (3 состояния)
[✅] Guard InaccessibleMessage в каждом callback handler
[✅] Проверка channel.owner_user_id в H2, H3, H4, H5
[✅] await callback.answer() везде
[✅] state.clear() после H4b, H5b
[✅] ReputationService вызывается при невалидном отказе
[✅] streak читается через repo.count_invalid_rejections_streak()
[✅] handle_reject_execute — внутренняя функция
[✅] Нет дублирования логики из placement.py
[✅] Нет голых except: без logger.error()
[✅] placement/__init__.py уже обновлён
```

---

## 🔍 Статический анализ

| Инструмент | Статус | Ошибок |
|------------|--------|--------|
| **Ruff** | ✅ PASS | 0 |
| **Импорты** | ✅ PASS | `from src.bot.handlers.placement import router` → OK |
| **Бот** | ✅ Running | Polling active |

---

## 📊 Итоговая статистика

| Категория | Количество |
|-----------|------------|
| **Handlers реализовано** | 10 |
| **FSM состояний** | 3 |
| **Вспомогательных функций** | 5 |
| **Констант** | 11 |
| **Строк кода** | ~680 |

---

## 🎯 Следующие шаги

**Готово к Этапу 4:** FSM States (вынос в отдельный файл `src/bot/states/placement.py`)

---

**Версия:** 1.0
**Дата:** 2026-03-10
**Статус:** ✅ ЗАВЕРШЕНО
