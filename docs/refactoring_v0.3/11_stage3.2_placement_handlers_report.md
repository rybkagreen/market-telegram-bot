# Этап 3.2: Завершение — Handlers размещения (сторона рекламодателя)

**Дата:** 2026-03-10
**Спринт:** 6 (Channel Owner & Advertiser v2.0)
**Статус:** ✅ ЗАВЕРШЁНО
**Файлы создано:** 1
**Файлы изменено:** 0
**Строк кода:** ~720

---

## 📋 Выполненные задачи

### Задача 1 — Реализован `placement.py` (handlers рекламодателя)

**Файл:** `src/bot/handlers/placement/placement.py` (720 строк)

**Callback prefix:** `placement:*`

---

## 🔨 Реализованные handlers (11 штук)

### H1 — Список заявок

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_placement_list()` | `placement:list` | Показать список заявок рекламодателя |

**Логика:**
- Получить user по telegram_id
- `repo.get_by_advertiser(user_id, limit=10)` — все заявки
- Если пусто — сообщение "Нет активных заявок"
- Показать список через `get_placement_list_kb(placements)`

---

### H2 — Выбор канала

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_select_channel()` | `placement:select_channel` | Инструкция по выбору канала |

**Логика:**
- Показать инструкцию: "Перейдите в каталог каналов"
- Кнопка "📺 Открыть каталог" → `ChannelsCB(action='categories')`
- Кнопка "◀️ Назад" → `placement:list`

---

### H3 — Начало создания заявки

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_create_placement()` | `placement:create:{channel_id}` | Карточка канала + старт FSM |

**Логика:**
- Проверить что advertiser не заблокирован (`ReputationRepo.is_advertiser_blocked`)
- Получить channel + ChannelSettings
- FSM: `state.update_data(channel_id, proposed_price)`
- Перейти в `waiting_post_text`

---

### H3a — Ввод текста поста

| Метод | State | Описание |
|-------|-------|----------|
| `process_post_text()` | `PlacementStates.waiting_post_text` | Обработка текста поста |

**Валидация:**
- `len(text) >= 10` — иначе ошибка
- `len(text) <= 4096` — иначе ошибка
- `state.update_data(post_text=text)`
- Перейти в `waiting_post_media`

---

### H3b — Ввод медиа

| Метод | State | Описание |
|-------|-------|----------|
| `process_post_media()` | `PlacementStates.waiting_post_media` | Обработка медиа или /skip |

**Логика:**
- Если `/skip` → `media_file_id = None`
- Если photo → `photo[-1].file_id`
- Если document → `document.file_id`
- Показать inline-кнопки выбора даты

---

### H3c — Выбор даты

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_schedule_select()` | `placement:schedule:{days_offset}` | Выбор даты публикации |

**Логика:**
- `scheduled_at = now + timedelta(days=days_offset)`
- Показать превью заявки
- Кнопки: "✅ Отправить заявку" → `placement:confirm_create`

---

### H3d — Подтверждение создания

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_confirm_create()` | `placement:confirm_create` | Создать PlacementRequest |

**Логика:**
- Собрать все данные из state
- Создать кампанию-заглушку
- Вызвать `PlacementRequestService.create_request()`
- `state.clear()`
- Показать: "✅ Заявка отправлена!"

---

### H4 — Карточка заявки

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_view_placement()` | `placement:view:{placement_id}` | Показать карточку заявки |

**Логика:**
- Проверить `placement.advertiser_id == user.id`
- Сформировать текст карточки с emoji статуса
- Передать status в `get_placement_card_kb()`

**Текст карточки:**
```
📋 Заявка #{id} — {status_emoji} {status_ru}

📺 Канал: @{channel_username}
💰 Предложенная цена: {proposed_price} кр
💰 Финальная цена: {final_price} кр (если есть)
📅 Дата публикации: {scheduled_at}
⏱ Истекает: {expires_at} (если pending_owner)
💱 Контр-предложений: {counter_offer_count}/{MAX_COUNTER_OFFER_ROUNDS}
```

---

### H5 — Принять контр-предложение

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_accept_counter()` | `placement:accept_counter:{placement_id}` | Принять контр-предложение |

**Логика:**
- Проверить `status == counter_offer`
- Вызвать `service.advertiser_accept_counter()`
- Обновить карточку

---

### H6 — Отмена заявки

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_cancel_init()` | `placement:cancel:{placement_id}` | Инициация отмены |
| `handle_cancel_confirm()` | `placement:cancel_confirm:{placement_id}` | Подтверждение отмены |

**Штрафы:**
- `pending_owner/pending_payment` → `CANCEL_BEFORE_DELTA (-5)`, возврат 100%
- `escrow` → `CANCEL_AFTER_DELTA (-20)`, возврат 50%

---

### H7 — Оплата

| Метод | Callback | Описание |
|-------|----------|----------|
| `handle_pay_placement()` | `placement:pay:{placement_id}` | Оплата заявки → эскроу |

**Логика:**
- Проверить `status == pending_payment`
- Проверить баланс `user.credits >= final_price`
- Если недостаточно → предложить пополнить
- Вызвать `service.process_payment()`
- Показать: "🔒 Средства заморожены"

---

## 📊 Бизнес-константы

```python
CANCEL_BEFORE_DELTA: float = -5.0
CANCEL_AFTER_DELTA: float = -20.0
CANCEL_SYSTEMATIC_DELTA: float = -20.0
CANCEL_SYSTEMATIC_THRESHOLD: int = 3
REFUND_BEFORE_ESCROW_PCT: int = 100
REFUND_AFTER_ESCROW_PCT: int = 50
OWNER_PAYOUT_PCT: int = 80
PLATFORM_FEE_PCT: int = 20
SLA_OWNER_RESPONSE_HOURS: int = 24
SLA_PAYMENT_HOURS: int = 24
MAX_COUNTER_OFFER_ROUNDS: int = 3
```

---

## 🔄 FSM States (4 состояния)

```python
class PlacementStates(StatesGroup):
    waiting_post_text = State()     # ввод текста рекламного поста
    waiting_post_media = State()    # ожидание медиа (опционально)
    waiting_schedule_date = State() # выбор даты публикации
    waiting_cancel_confirm = State() # подтверждение отмены
```

---

## 🛠️ Вспомогательные функции

### `get_status_emoji(status: PlacementStatus) -> str`

Получить emoji для статуса:
- `pending_owner` → "⏳"
- `counter_offer` → "💱"
- `pending_payment` → "💳"
- `escrow` → "🔒"
- `published` → "✅"
- `failed` → "❌"
- `refunded` → "↩️"
- `cancelled` → "🚫"

### `get_status_ru(status: PlacementStatus) -> str`

Получить русское описание статуса.

### `check_placement_owner(callback, placement) -> bool`

Проверить что пользователь — владелец заявки (advertiser_id).

---

## ✅ Чеклист завершения

```
[✅] Прочитаны все 8 файлов из step_0
[✅] Все callbacks начинаются с placement:
[✅] Нет пересечений с arbitration:*, ch_cfg:*, channel_add:*
[✅] Константы объявлены в начале файла
[✅] PlacementStates объявлены в файле
[✅] Guard InaccessibleMessage в каждом callback handler
[✅] Проверка advertiser_id в H4, H5, H6, H6a, H7
[✅] await callback.answer() везде
[✅] state.clear() после H3d и H6a
[✅] Сервис создаётся внутри async with session
[✅] Нет голых except: без logger.error()
[✅] placement/__init__.py уже обновлён
```

---

## 🔍 Статический анализ

| Инструмент | Статус | Ошибок |
|------------|--------|--------|
| **Ruff** | ✅ PASS | 5 (автоисправлено) |
| **Импорты** | ✅ PASS | `from src.bot.handlers.placement import router` → OK |
| **Бот** | ✅ Running | Polling active |

---

## 📊 Итоговая статистика

| Категория | Количество |
|-----------|------------|
| **Handlers реализовано** | 11 |
| **FSM состояний** | 4 |
| **Вспомогательных функций** | 3 |
| **Констант** | 11 |
| **Строк кода** | ~720 |

---

## 🎯 Следующие шаги

**Готово к Этапу 3.3:** arbitration.py handlers (сторона владельца)

---

**Версия:** 1.0
**Дата:** 2026-03-10
**Статус:** ✅ ЗАВЕРШЕНО
