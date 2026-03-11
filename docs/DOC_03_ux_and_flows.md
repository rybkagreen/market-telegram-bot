# DOC-03: UX, Меню, Клавиатуры и FSM

**RekHarborBot — Техническая документация v3.0**  
**Дата:** 2026-03-10 | Навигация, callback_data, состояния, пользовательские флоу

---

## 1. Архитектура меню v3.0

### 1.1 Принцип двухуровневой иерархии

```
/start
  └── Главное меню (4 кнопки, shared для всех ролей)
          │
          └── main:change_role
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
   Advertiser Menu        Owner Menu
   (5 кнопок)            (5 кнопок)
```

**Главное меню** — общее для всех ролей, отображается всегда при `/start`.  
**Меню роли** — появляется после `main:change_role`, зависит от текущей роли.

### 1.2 Диспетчер ролей в `get_role_menu_kb()`

```python
def get_role_menu_kb(role: str, **kwargs) -> InlineKeyboardMarkup:
    if role == "new":     return get_main_menu_kb()
    if role == "advertiser": return get_advertiser_menu_kb(**kwargs)
    if role == "owner":   return get_owner_menu_kb(**kwargs)
    if role == "both":    return get_combined_menu_kb(**kwargs)
    if role == "admin":   return get_advertiser_menu_kb(**kwargs)  # admin видит advertiser меню
```

---

## 2. Главное меню (`get_main_menu_kb()`)

**Файл:** `src/bot/keyboards/main_menu.py`  
**Триггеры:** `/start`, `main:main_menu` callback

```
┌─────────────────────────────────────┐
│  👤 Кабинет                         │  callback: main:cabinet
│  🔄 Выбрать роль                    │  callback: main:change_role
│  💬 Помощь                          │  callback: main:help
│  ✉️ Обратная связь                  │  callback: main:feedback
└─────────────────────────────────────┘
```

| Кнопка | callback_data | Handler | Файл |
|--------|---------------|---------|------|
| 👤 Кабинет | `main:cabinet` | `show_cabinet` | `cabinet.py` |
| 🔄 Выбрать роль | `main:change_role` | `show_role_selection` | `start.py` |
| 💬 Помощь | `main:help` | `show_help` | `help.py` |
| ✉️ Обратная связь | `main:feedback` | `start_feedback` | `feedback.py` |

---

## 3. Меню рекламодателя (`get_advertiser_menu_kb()`)

**Параметры:** `active_campaigns: int = 0, user_id: int`

```
┌─────────────────────────────────────┐
│  📊 Статистика и аналитика          │  callback: main:analytics
│  📣 Создать кампанию                │  callback: main:create_campaign
│  📋 Мои кампании  [N активных]      │  callback: main:my_campaigns
│  💼 B2B-пакеты                      │  callback: main:b2b
│  🔙 В главное меню                  │  callback: main:main_menu
└─────────────────────────────────────┘
```

| Кнопка | callback_data | Handler | Файл |
|--------|---------------|---------|------|
| 📊 Статистика | `main:analytics` | `show_advertiser_analytics` | `analytics.py` |
| 📣 Создать кампанию | `main:create_campaign` | `start_placement_creation` | `placement.py` (новый) |
| 📋 Мои кампании | `main:my_campaigns` | `show_my_campaigns` | `campaigns.py` |
| 💼 B2B-пакеты | `main:b2b` | `show_b2b_packages` | `b2b.py` |
| 🔙 В главное меню | `main:main_menu` | `go_to_main_menu` | `start.py` |

---

## 4. Меню владельца канала (`get_owner_menu_kb()`)

**Параметры:** `pending_requests: int = 0, available_payout: Decimal = 0, user_id: int`

```
┌─────────────────────────────────────┐
│  📊 Статистика                      │  callback: main:owner_analytics
│  📺 Мои каналы                      │  callback: main:my_channels
│  📋 Заявки  [N новых]               │  callback: main:my_requests
│  💸 Выплаты  [NNN кр доступно]      │  callback: main:payouts
│  🔙 В главное меню                  │  callback: main:main_menu
└─────────────────────────────────────┘
```

| Кнопка | callback_data | Handler | Файл |
|--------|---------------|---------|------|
| 📊 Статистика | `main:owner_analytics` | `show_owner_analytics` | `analytics.py` |
| 📺 Мои каналы | `main:my_channels` | `show_my_channels` | `channel_owner.py` |
| 📋 Заявки | `main:my_requests` | `show_placement_requests` | `arbitration.py` (новый) |
| 💸 Выплаты | `main:payouts` | `show_payouts` | `channel_owner.py` |
| 🔙 В главное меню | `main:main_menu` | `go_to_main_menu` | `start.py` |

**⚠️ КРИТИЧНО:** `main:analytics` ≠ `main:owner_analytics`. Это два физически разных callback_data с разными handlers, разными данными и разными источниками статистики. Баг RT-001 исправлен в Этапе 0.

---

## 5. Комбинированное меню (`get_combined_menu_kb()`)

Для пользователей с ролью `both`. Показывает кнопки обеих ролей с визуальным разделителем.

```
┌─────────────────────────────────────┐
│  ── РЕКЛАМОДАТЕЛЬ ──                │
│  📊 Статистика рекламодателя        │  callback: main:analytics
│  📣 Создать кампанию                │  callback: main:create_campaign
│  📋 Мои кампании                    │  callback: main:my_campaigns
│  💼 B2B-пакеты                      │  callback: main:b2b
│  ── ВЛАДЕЛЕЦ КАНАЛА ──              │
│  📊 Статистика канала               │  callback: main:owner_analytics
│  📺 Мои каналы                      │  callback: main:my_channels
│  📋 Заявки                          │  callback: main:my_requests
│  💸 Выплаты                         │  callback: main:payouts
│  🔙 В главное меню                  │  callback: main:main_menu
└─────────────────────────────────────┘
```

---

## 6. Полный реестр callback_data (навигация)

| callback_data | Тип | Handler | Доступен ролям |
|---------------|-----|---------|----------------|
| `main:cabinet` | Главное меню | `show_cabinet` | all |
| `main:change_role` | Главное меню | `show_role_selection` | all |
| `main:help` | Главное меню | `show_help` | all |
| `main:feedback` | Главное меню | `start_feedback` | all |
| `main:main_menu` | Навигация | `go_to_main_menu` | all |
| `main:analytics` | Advertiser | `show_advertiser_analytics` | advertiser, both |
| `main:create_campaign` | Advertiser | `start_placement_creation` | advertiser, both |
| `main:my_campaigns` | Advertiser | `show_my_campaigns` | advertiser, both |
| `main:b2b` | Advertiser | `show_b2b_packages` | advertiser, both |
| `main:owner_analytics` | Owner | `show_owner_analytics` | owner, both |
| `main:my_channels` | Owner | `show_my_channels` | owner, both |
| `main:my_requests` | Owner | `show_placement_requests` | owner, both |
| `main:payouts` | Owner | `show_payouts` | owner, both |

---

## 7. Схема CallbackData

**Файл:** `src/bot/handlers/callback_schemas.py`

```python
from aiogram.filters.callback_data import CallbackData

class MainMenuCB(CallbackData, prefix="main"):
    action: str

# Использование:
# MainMenuCB(action="analytics").pack()  →  "main:analytics"
# F.data == "main:analytics"  →  MainMenuCB.filter(F.action == "analytics")
```

---

## 8. FSM States — существующие

### 8.1 CampaignStates (`src/bot/states/campaign.py`) — 9 состояний

```python
class CampaignStates(StatesGroup):
    waiting_name        = State()  # Ввод названия
    waiting_text        = State()  # Ввод текста объявления
    waiting_budget      = State()  # Ввод бюджета
    waiting_category    = State()  # Выбор категории
    waiting_channels    = State()  # Выбор каналов
    waiting_schedule    = State()  # Выбор времени
    waiting_confirm     = State()  # Подтверждение
    waiting_payment     = State()  # Ожидание оплаты
    campaign_active     = State()  # Кампания активна
```

### 8.2 CampaignCreateState (`src/bot/states/campaign_create.py`) — 13 состояний

**⚠️ НЕ ТРОГАТЬ — AI wizard.**

```python
class CampaignCreateState(StatesGroup):
    choosing_ai_or_manual  = State()
    entering_topic         = State()
    choosing_tone          = State()
    choosing_variant       = State()
    editing_text           = State()
    choosing_category      = State()
    choosing_subcategory   = State()
    choosing_channels      = State()
    setting_budget         = State()
    setting_schedule       = State()
    setting_frequency      = State()
    confirming             = State()
    waiting_payment        = State()
```

### 8.3 AddChannelStates (`src/bot/states/channel_owner.py`) — 6 состояний

```python
class AddChannelStates(StatesGroup):
    waiting_username    = State()  # Ввод @username канала
    checking_channel    = State()  # Проверка существования
    waiting_bot_added   = State()  # Ожидание добавления бота
    verifying_admin     = State()  # Верификация прав бота
    waiting_price       = State()  # Ввод цены за пост
    confirming          = State()  # Подтверждение регистрации
```

### 8.4 OnboardingStates (`src/bot/states/onboarding.py`)

```python
class OnboardingStates(StatesGroup):
    choosing_role    = State()
    confirming_role  = State()
```

### 8.5 FeedbackStates (`src/bot/states/feedback.py`)

```python
class FeedbackStates(StatesGroup):
    waiting_message  = State()
    waiting_contact  = State()
```

---

## 9. FSM States — новые (создать в Этапе 4)

### 9.1 PlacementStates (`src/bot/states/placement.py`) — 9 состояний

```python
class PlacementStates(StatesGroup):
    selecting_category    = State()  # Шаг 1: категория
    selecting_subcategory = State()  # Шаг 2: подкатегория (skip если нет)
    selecting_channels    = State()  # Шаг 3: выбор каналов из каталога
    entering_text         = State()  # Шаг 4: текст (AI/Manual)
    arbitrating           = State()  # Шаг 5: ввод условий (цена, время)
    confirming            = State()  # Шаг 6: подтверждение перед отправкой
    waiting_payment       = State()  # Шаг 7: ожидание оплаты
    escrow                = State()  # Шаг 8: средства заблокированы
    publishing            = State()  # Шаг 9: идёт публикация
```

### 9.2 ArbitrationStates (`src/bot/states/arbitration.py`) — 5 состояний

```python
class ArbitrationStates(StatesGroup):
    viewing_request    = State()  # Просмотр заявки
    accepting          = State()  # Подтверждение принятия
    rejecting          = State()  # Ввод причины отклонения (мин 10 символов)
    counter_offering   = State()  # Ввод контр-предложения (цена/время)
    waiting_response   = State()  # Ожидание ответа advertiser
```

### 9.3 ChannelSettingsStates (`src/bot/states/channel_settings.py`) — 6 состояний

```python
class ChannelSettingsStates(StatesGroup):
    editing_price          = State()  # Редактирование цены за пост
    editing_daily_package  = State()  # Настройка дневного пакета
    editing_weekly_package = State()  # Настройка недельного пакета
    editing_subscription   = State()  # Настройка подписки
    editing_schedule       = State()  # Настройка расписания публикаций
    confirming             = State()  # Подтверждение изменений
```

---

## 10. Пользовательские флоу

### 10.1 Онбординг (новый пользователь)

```
/start
  └── Нет в БД → create User(role="new")
        └── Показать баннер + описание платформы
              └── Кнопка "Начать" → OnboardingStates.choosing_role
                    ├── [Я рекламодатель] → role="advertiser" → Advertiser Menu
                    ├── [У меня есть канал] → role="owner" → Owner Menu
                    └── [Обе роли] → role="both" → Combined Menu
```

### 10.2 Флоу рекламодателя: создание кампании (9 шагов)

```
main:create_campaign
  │
  ▼ Шаг 1: Выбор категории
  InlineKeyboard: 11 категорий (Бизнес, IT, Lifestyle, Финансы, ...)
  │
  ▼ Шаг 2: Выбор подкатегории (если есть)
  InlineKeyboard: список подкатегорий | [Пропустить]
  │
  ▼ Шаг 3: Выбор каналов
  InlineKeyboard: список каналов с фильтрами
  Показывать: @username, подписчики, ER%, avg_views, цена/пост, рейтинг
  [Выбрать] [Медиакит] | пагинация | [Далее →] (мин 1 канал)
  │
  ▼ Шаг 4: Текст рекламы
  [✨ Создать с AI] → 3 варианта → выбрать/редактировать
  [✏️ Написать вручную] → TextInput (макс 1000 символов)
  │
  ▼ Шаг 5: Условия арбитража
  Показать: предложенная цена (= price_per_post канала), желаемое время
  [Изменить цену] [Изменить время] [Добавить частоту]
  [Отправить заявку →]
  │
  ▼ Шаг 6: Подтверждение
  Итог: каналы, текст (превью), условия, итоговая сумма
  [✅ Подтвердить и отправить] [← Назад]
  │
  ▼ → PlacementRequest создан (status=pending_owner)
      Уведомление → владельцу канала
  │
  ▼ Шаг 7: Ожидание ответа владельца (24ч таймер)
  Статус: "⏳ Ожидаем ответа владельца"
  При принятии → статус pending_payment
  При отклонении → уведомление с причиной, refund 100%
  При контр-предложении → показать новые условия, принять/отклонить (макс 3 раунда)
  │
  ▼ Шаг 7 (продолжение): Оплата (24ч таймер)
  [💳 Оплатить картой] [⭐ Telegram Stars] [₿ CryptoBot] [СБП]
  Сумма = final_price
  │
  ▼ Шаг 8: Эскроу
  Средства заблокированы: "🔒 N кр заморожены"
  Статус → ESCROW
  │
  ▼ Шаг 9: Публикация
  В назначенное final_schedule время → sender.py публикует в канал
  При успехе: MailingLog(status=SENT), статус → PUBLISHED
              Выплата 80% владельцу, 20% комиссия
              ReputationService.on_publication(advertiser_id, owner_id)
  При ошибке: retry через 1ч, затем status=FAILED → refund 100%
```

### 10.3 Флоу владельца канала: обработка заявки

```
Уведомление о новой заявке
  └── [Посмотреть заявку] → ArbitrationStates.viewing_request
        │
        Показать: @advertiser_username, текст рекламы, предложенная цена,
                  желаемое время, репутация рекламодателя
        │
        ├── [✅ Принять] → ArbitrationStates.accepting
        │      └── Подтвердить → status=PENDING_PAYMENT
        │                        Уведомление рекламодателю
        │
        ├── [❌ Отклонить] → ArbitrationStates.rejecting
        │      └── TextInput: причина отклонения (мин 10 символов, должна содержать буквы)
        │           Валидация: len≥10, re.search(r'[а-яёa-z]', reason, re.I)
        │           Невалидная причина → штраф репутации + повтор ввода
        │           Валидная → status=CANCELLED, refund 100% advertiser
        │
        └── [🔄 Контр-предложение] → ArbitrationStates.counter_offering
               └── Ввод новой цены и/или нового времени
                    counter_offer_count += 1
                    Если counter_offer_count >= 3 → блокировать кнопку контр-предложения
                    status=COUNTER_OFFER, уведомление advertiser
                    expires_at = now() + 24h
```

### 10.4 Флоу владельца: добавление канала

```
main:my_channels → [Добавить канал]
  │
  ▼ AddChannelStates.waiting_username
  TextInput: "Введите @username канала"
  │
  ▼ AddChannelStates.checking_channel
  Автоматическая проверка: канал существует, публичный
  Если не найден → ошибка, повторить
  │
  ▼ AddChannelStates.waiting_bot_added
  Инструкция: "Добавьте @RekHarborBot как администратора"
  [Я добавил бота] → проверка
  │
  ▼ AddChannelStates.verifying_admin
  channel_rules_checker.py: проверить bot_is_admin
  Если нет прав → ошибка, повторить
  │
  ▼ AddChannelStates.waiting_price
  TextInput: "Укажите цену за пост (мин 100 кр)"
  Валидация: ≥ ChannelSettings.MIN_PRICE_PER_POST
  │
  ▼ AddChannelStates.confirming
  Итог: название, подписчики, цена
  [✅ Зарегистрировать] → TelegramChat создан + ChannelSettings создан (defaults)
                          owner_id = user.id, is_opt_in = True
```

### 10.5 Флоу настройки канала

```
main:my_channels → [⚙️ Настройки] → ChannelSettingsStates.editing_price
  │
  Меню настроек:
  ├── [💰 Цена за пост: 500 кр]      → editing_price
  ├── [📦 Дневной пакет: 20% скидка] → editing_daily_package
  ├── [📦 Недельный пакет: 30%]       → editing_weekly_package
  ├── [📅 Подписка: 7-365 дней]       → editing_subscription
  ├── [🕐 Расписание: 09:00-21:00]    → editing_schedule
  └── [🤖 Авто-принятие: выкл]        → toggle_auto_accept
```

---

## 11. Клавиатуры — существующие файлы

| Файл | Основные функции |
|------|-----------------|
| `main_menu.py` | `get_main_menu_kb()`, `get_advertiser_menu_kb()`, `get_owner_menu_kb()`, `get_combined_menu_kb()`, `get_role_menu_kb()` |
| `cabinet.py` | `get_cabinet_kb()`, `get_xp_details_kb()`, `get_reputation_kb()` |
| `campaign.py` | `get_campaigns_list_kb()`, `get_campaign_detail_kb()`, `get_campaign_actions_kb()` |
| `campaign_ai.py` | AI wizard клавиатуры — **НЕ ТРОГАТЬ** |
| `channels.py` | `get_channels_catalog_kb()`, `get_channel_detail_kb()`, `get_channel_filter_kb()` |
| `billing.py` | `get_payment_methods_kb()`, `get_tariffs_kb()`, `get_topup_kb()` |
| `comparison.py` | `get_comparison_kb()`, `get_comparison_result_kb()` |
| `feedback.py` | `get_feedback_kb()` |
| `mediakit.py` | `get_mediakit_kb()` |
| `admin.py` | Панель администратора |
| `pagination.py` | `get_pagination_kb(page, total_pages, prefix)` — универсальная пагинация |

### 11.1 Клавиатуры для создания (Этап 5)

| Файл | Функции |
|------|---------|
| `placement.py` | `get_category_kb()`, `get_subcategory_kb()`, `get_channel_selection_kb()`, `get_text_mode_kb()`, `get_placement_confirm_kb()`, `get_payment_kb()` |
| `arbitration.py` | `get_request_actions_kb()`, `get_counter_offer_kb()`, `get_rejection_confirm_kb()` |
| `channel_settings.py` | `get_channel_settings_kb()`, `get_settings_field_kb()`, `get_time_picker_kb()` |

---

## 12. Аналитика: что показывает каждый раздел

### 12.1 `main:analytics` → Аналитика рекламодателя

```
📊 Аналитика кампаний

Общее:
- Активных кампаний: N
- Всего размещений: N
- Охват суммарный: NNN подписчиков

Метрики эффективности:
- CPM (Cost Per Mille): N кр
- CTR (Click-Through Rate): N.N%
- ROI (Return on Investment): N%
- Конверсии: N

Топ-каналы по CTR:
- @channel1 — CTR 3.2%
- @channel2 — CTR 2.8%

Репутация: ⭐ N.N/10
```

### 12.2 `main:owner_analytics` → Аналитика владельца

```
📊 Статистика канала

Заработок:
- Текущий месяц: NNN кр
- Всего заработано: NNNN кр
- Ожидает выплаты: N кр

Размещения:
- Выполнено: N
- Отклонено: N
- Процент принятия: N%

Репутация: ⭐ N.N/10
Последние изменения: [история]
```

---

## 13. Notifications — типы уведомлений

| Событие | Кому | Текст |
|---------|------|-------|
| Новая заявка | owner | "📋 Новая заявка на размещение от @advertiser. Условия: N кр, дата: DD.MM" |
| Заявка принята | advertiser | "✅ Владелец @channel принял заявку. Оплатите N кр до DD.MM HH:MM" |
| Заявка отклонена | advertiser | "❌ Заявка отклонена. Причина: {rejection_reason}. Возврат N кр." |
| Контр-предложение | advertiser | "🔄 Владелец предложил новые условия: N кр, DD.MM" |
| Таймаут ответа | advertiser | "⏰ Владелец не ответил в срок. Возврат N кр." |
| Таймаут оплаты | owner | "⏰ Рекламодатель не оплатил в срок. Заявка аннулирована." |
| Оплата получена | owner | "💰 Получена оплата N кр (эскроу). Публикация: DD.MM HH:MM" |
| Публикация выполнена | advertiser + owner | "✅ Реклама опубликована в @channel. Выплата N кр зачислена." |
| Ошибка публикации | advertiser | "⚠️ Ошибка публикации. Возврат N кр." |
| Истёк срок тарифа | user | "⚠️ Ваш тариф Pro истекает через 3 дня." |
| Блокировка репутации | user | "🚫 Ваш аккаунт заблокирован на 7 дней. Причина: {reason}" |

---

## 14. Middleware

### 14.1 FSMTimeoutMiddleware (`src/bot/middlewares/fsm_timeout.py`)

Автоматически сбрасывает FSM состояние если пользователь не активен N минут.

```python
# Настройка таймаутов по типу состояния:
TIMEOUTS = {
    "PlacementStates": 30 * 60,     # 30 минут
    "ArbitrationStates": 24 * 60 * 60, # 24 часа
    "AddChannelStates": 10 * 60,    # 10 минут
    "FeedbackStates": 5 * 60,       # 5 минут
    "default": 15 * 60,             # 15 минут
}
```

При таймауте: очистить state, отправить сообщение "Сессия истекла. Используйте /start.", показать главное меню.

### 14.2 ThrottlingMiddleware (`src/bot/middlewares/throttling.py`)

Rate limiting на уровне пользователя. Хранит счётчики в Redis.

```python
THROTTLE_LIMITS = {
    "default": (5, 1),      # 5 запросов в 1 секунду
    "callback": (10, 1),    # 10 callback в 1 секунду
    "message": (3, 1),      # 3 сообщения в 1 секунду
}
```

При превышении: IgnoreError или "Слишком много запросов, подождите N сек."
