# QWEN CODE — СПРИНТ 2: ВЫСОКИЙ ПРИОРИТЕТ (P1)

## ⚠️ ПРАВИЛА ВЫПОЛНЕНИЯ — ЧИТАЙ ПЕРЕД СТАРТОМ

1. **Спринт 1 должен быть завершён** перед началом этого спринта
2. **Выполняй задачи строго по порядку** — некоторые зависят друг от друга
3. **После каждой задачи** — пиши `✅ ЗАДАЧА N ВЫПОЛНЕНА` и показывай изменённые файлы
4. **При рефакторинге** (задача 5, 6) — не меняй бизнес-логику, только структуру
5. **Не добавляй новые зависимости** в `requirements.txt` без явного указания

---

## ЗАДАЧА 1 — Уведомление пользователя о продлении тарифа

### Файл: `src/tasks/billing_tasks.py`

### Контекст
После успешного или неуспешного продления тарифа (`check_plan_renewals`) пользователь не получает никакого уведомления. Это нарушает UX и вызывает вопросы в поддержку.

### Что читать перед правкой
```
1. src/tasks/billing_tasks.py — найти check_plan_renewals (строка ~90)
2. src/core/services/notification_service.py — методы отправки уведомлений
3. src/db/models/notification.py — NotificationType enum, доступные типы
4. src/db/models/user.py — поля plan, plan_expires_at, telegram_id
```

### Что реализовать

После блока продления тарифа добавить вызов уведомлений:

```python
# Сценарий А — успешное продление:
await notification_service.send_notification(
    user_id=user.id,
    notification_type=NotificationType.PLAN_RENEWED,  # или ближайший аналог
    message=f"✅ Ваш тариф {plan_name} продлён до {new_expires_at.strftime('%d.%m.%Y')}",
    extra_data={"plan": user.plan, "expires_at": str(new_expires_at)}
)

# Сценарий Б — недостаточно средств / ошибка продления:
await notification_service.send_notification(
    user_id=user.id,
    notification_type=NotificationType.PLAN_EXPIRED,  # или ближайший аналог
    message=f"⚠️ Не удалось продлить тариф {plan_name}. Пополните баланс.",
    extra_data={"plan": user.plan, "balance": str(user.balance)}
)
```

**Важно:**
- Если `NotificationType` не имеет нужных значений — добавить их в enum модели и создать миграцию
- Уведомление отправляется только если `user.notifications_enabled = True`
- Ошибка при отправке уведомления не должна прерывать задачу продления

### Критерии готовности
- [ ] Уведомление отправляется при успешном продлении
- [ ] Уведомление отправляется при неудачном продлении
- [ ] Нет отправки если `user.notifications_enabled = False`
- [ ] Ошибка уведомления логируется, но не прерывает billing_task
- [ ] TODO в строке ~90 удалён

---

## ЗАДАЧА 2 — Выбор аудитории в AI-визарде создания кампании

### Файл: `src/bot/handlers/campaign_create_ai.py`

### Что читать перед правкой
```
1. src/bot/handlers/campaign_create_ai.py — полностью, особенно строку ~419
2. src/bot/keyboards/campaign_ai.py — существующие клавиатуры AI-визарда
3. src/bot/states/campaign_create.py — FSM состояния визарда
4. src/utils/categories.py — доступные категории/подкатегории
5. src/db/models/campaign.py — поля filters_json или audience_filters
```

### Что реализовать

**Шаг 2.1** — Добавить состояние в `src/bot/states/campaign_create.py`:
```python
class CampaignCreateAI(StatesGroup):
    # ... существующие состояния ...
    select_audience = State()  # ← добавить
```

**Шаг 2.2** — Добавить клавиатуру в `src/bot/keyboards/campaign_ai.py`:
```python
def get_audience_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора аудитории.
    Показывает топ-8 тематик из categories.py.
    Кнопка "Все тематики" — без фильтра.
    Кнопка "Пропустить" — перейти дальше без фильтра.
    """
```

**Шаг 2.3** — В `campaign_create_ai.py` вместо TODO реализовать хендлер:
```python
@router.callback_query(CampaignCreateAI.select_audience)
async def handle_audience_select(callback: CallbackQuery, state: FSMContext):
    """
    Сохранить выбранную тематику в state.
    Перейти к следующему шагу визарда.
    """
```

**Структура выбора:**
```
Выберите целевую аудиторию:

[Бизнес и финансы]  [Технологии]
[Новости]           [Развлечения]
[Образование]       [Lifestyle]
[Криптовалюты]      [Другое]
[━━ Все тематики ━━]
[Пропустить →]
```

### Критерии готовности
- [ ] Клавиатура отображается в нужный момент визарда
- [ ] Выбор сохраняется в FSM state
- [ ] Кнопка "Пропустить" работает, не ломает флоу
- [ ] После выбора — переход к следующему шагу визарда
- [ ] TODO в строке ~419 удалён

---

## ЗАДАЧА 3 — Планирование кампании (выбор даты/времени)

### Файл: `src/bot/handlers/campaign_create_ai.py`

### Что читать перед правкой
```
1. src/bot/handlers/campaign_create_ai.py — строка ~529
2. src/bot/states/campaign_create.py — состояния визарда
3. src/db/models/campaign.py — поля scheduled_at, status
4. src/tasks/mailing_tasks.py — check_scheduled_campaigns
```

### Что реализовать

**Шаг 3.1** — Добавить состояние:
```python
class CampaignCreateAI(StatesGroup):
    # ...
    select_schedule = State()  # ← добавить
```

**Шаг 3.2** — Клавиатура планирования:
```python
def get_schedule_keyboard() -> InlineKeyboardMarkup:
    """
    Опции планирования:
    - "Запустить сейчас" → scheduled_at = None
    - "Через 1 час"     → scheduled_at = now + 1h
    - "Сегодня вечером" → scheduled_at = сегодня 20:00 МСК
    - "Завтра утром"    → scheduled_at = завтра 09:00 МСК
    - "Выбрать дату"    → запросить ввод текстом
    """
```

**Шаг 3.3** — Хендлер ввода даты текстом:
```python
@router.message(CampaignCreateAI.select_schedule)
async def handle_schedule_input(message: Message, state: FSMContext):
    """
    Парсить дату из текста.
    Форматы: "25.03", "25.03.2026", "25.03 14:00"
    При ошибке парсинга — попросить повторить.
    Timezone: UTC+3 (МСК).
    """
```

**Шаг 3.4** — Сохранение в БД:
```python
# При создании кампании из state:
campaign.scheduled_at = state_data.get("scheduled_at")  # None = немедленно
campaign.status = CampaignStatus.SCHEDULED if campaign.scheduled_at else CampaignStatus.PENDING
```

### Критерии готовности
- [ ] Кнопки "быстрого" планирования работают
- [ ] Ввод даты вручную работает (с валидацией)
- [ ] Дата сохраняется в `campaign.scheduled_at`
- [ ] Статус кампании выставляется корректно
- [ ] `check_scheduled_campaigns` подхватывает новые кампании
- [ ] TODO в строке ~529 удалён

---

## ЗАДАЧА 4 — Полная статистика в еженедельном дайджесте

### Файл: `src/tasks/notification_tasks.py`

### Что читать перед правкой
```
1. src/tasks/notification_tasks.py — строки ~985, ~1021, ~1036
2. src/core/services/analytics_service.py — get_user_summary()
3. src/db/repositories/transaction_repo.py — методы суммирования
4. src/db/repositories/payout_repo.py — get_available_amount() (из Спринта 1)
5. src/db/models/user.py — поля plan, owner_xp, advertiser_xp
```

### Что реализовать

Заменить 3 TODO реальными данными:

**TODO #1 — строка ~985 (`total_views`, `total_spent`):**
```python
# БЫЛО: # TODO: получить total_views и total_spent
# ДОЛЖНО СТАТЬ:
summary = await analytics_service.get_user_summary(user_id=user.id, days=7)
total_views = summary.total_views
total_spent = summary.total_spent
campaigns_count = summary.campaigns_count
```

**TODO #2 — строка ~1021 (данные плана):**
```python
# БЫЛО: # TODO: получить данные из БД
# ДОЛЖНО СТАТЬ:
plan_display = {
    "FREE": "Бесплатный",
    "PRO": "PRO",
    "BUSINESS": "Business"
}.get(user.plan, user.plan)

plan_expires_str = (
    user.plan_expires_at.strftime("%d.%m.%Y")
    if user.plan_expires_at else "Бессрочно"
)
```

**TODO #3 — строка ~1036 (`available_payout`):**
```python
# БЫЛО: # TODO: получить available_payout
# ДОЛЖНО СТАТЬ:
available_payout = await payout_repo.get_available_amount(user.id)
```

### Критерии готовности
- [ ] Дайджест содержит `total_views` из реальных данных
- [ ] Дайджест содержит `total_spent` из реальных данных
- [ ] Отображается актуальный тариф и дата его окончания
- [ ] Доступная сумма к выводу реальная
- [ ] Все три TODO удалены
- [ ] При отсутствии данных — fallback на 0, не исключение

---

## ЗАДАЧА 5 — Разделить `admin.py` на подмодули

### Файлы:
- `src/bot/handlers/admin.py` → разбить на:
  - `src/bot/handlers/admin/campaigns.py`
  - `src/bot/handlers/admin/users.py`
  - `src/bot/handlers/admin/analytics.py`
  - `src/bot/handlers/admin/ai.py`
  - `src/bot/handlers/admin/__init__.py`

### Контекст
`admin.py` содержит 1421 строку и 30+ хендлеров. Это делает невозможным нормальную поддержку. Нужно **только переместить код** — не менять логику.

### Как разбивать

**Читай `admin.py` полностью, затем:**

1. **`admin/users.py`** — всё что связано с управлением пользователями:
   - просмотр пользователей, бан/разбан, изменение баланса, изменение плана

2. **`admin/campaigns.py`** — всё что связано с кампаниями:
   - просмотр кампаний, принудительная остановка, модерация

3. **`admin/analytics.py`** — статистика платформы:
   - общая статистика, топы, графики активности

4. **`admin/ai.py`** — AI-настройки:
   - переключение моделей, просмотр использования токенов, тест промптов

5. **`admin/__init__.py`** — экспортировать все роутеры:
   ```python
   from .users import router as users_router
   from .campaigns import router as campaigns_router
   from .analytics import router as analytics_router
   from .ai import router as ai_router
   
   __all__ = ["users_router", "campaigns_router", "analytics_router", "ai_router"]
   ```

### Что обновить после разбивки
```
src/bot/main.py — обновить импорты роутеров
```

### Критерии готовности
- [ ] Все хендлеры из `admin.py` перенесены в подмодули
- [ ] Старый `admin.py` удалён или заменён на `__init__.py`
- [ ] Бот запускается без ошибок (`python -m src.bot.main` или аналог)
- [ ] Ни одна бизнес-логика не изменена — только перемещение
- [ ] Импорты в `main.py` обновлены

---

## ЗАДАЧА 6 — Удалить legacy слой `src/services/`

### Файлы для удаления:
```
src/services/billing_service.py
src/services/campaign_service.py
src/services/user_service.py
src/services/__init__.py
```

### Контекст
Слой `src/services/` является обёрткой над `src/core/services/` и дублирует функциональность. Все handlers должны использовать `core/services` напрямую.

### Алгоритм выполнения

**Шаг 6.1 — Найти все импорты legacy слоя:**
```bash
grep -rn "from src.services" src/
grep -rn "from services" src/
grep -rn "import services" src/
```

**Шаг 6.2 — Для каждого найденного импорта:**
- Понять какой метод используется из legacy сервиса
- Найти аналог в `src/core/services/` или `src/db/repositories/`
- Заменить импорт и вызов на прямой

**Шаг 6.3 — Особые случаи:**
```python
# src/services/user_service.py: get_or_create()
# Аналог: src/db/repositories/user_repo.py: create_or_update()

# src/services/billing_service.py: create_payment()
# Аналог: src/core/services/billing_service.py: create_payment()

# src/services/campaign_service.py: get_user_campaigns()
# Аналог: src/db/repositories/campaign_repo.py: get_by_user_id()
```

**Шаг 6.4 — После замены всех импортов:**
```bash
# Убедиться что нет оставшихся импортов
grep -rn "from src.services" src/
# Если пусто — удалить директорию
rm -rf src/services/
```

### Критерии готовности
- [ ] `grep -rn "from src.services" src/` возвращает пусто
- [ ] Директория `src/services/` удалена
- [ ] Бот и API запускаются без `ImportError`
- [ ] Ни одна функциональность не нарушена

---

## ФИНАЛЬНАЯ ПРОВЕРКА СПРИНТА 2

```bash
# 1. Проверить запуск бота
python -c "from src.bot.main import main; print('Bot: OK')"

# 2. Проверить запуск API
python -c "from src.api.main import app; print('API: OK')"

# 3. Проверить отсутствие legacy
grep -rn "from src.services" src/ && echo "ОШИБКА: legacy импорты остались" || echo "OK: legacy удалён"

# 4. Проверить отсутствие TODO в изменённых файлах
grep -rn "TODO\|FIXME" \
  src/tasks/billing_tasks.py \
  src/tasks/notification_tasks.py \
  src/bot/handlers/campaign_create_ai.py

# 5. Линтер
ruff check src/bot/handlers/admin/
ruff check src/tasks/notification_tasks.py
```

**Спринт считается завершённым** когда все 6 задач выполнены, бот и API стартуют без ошибок, legacy директория удалена.
