# RekHarborBot — Документ миграции контекста
**Дата:** 12 марта 2026  
**Назначение:** Перенос полного контекста проекта в новый чат  
**Статус на момент создания:** Этапы 0–2 завершены. Этапы 3–7 в процессе.  
**Предыдущий документ:** 11.03.2026 (устарел — см. раздел 15 «Дельта изменений»)

---

## 1. РОЛЬ АССИСТЕНТА

Ты — senior Python-разработчик и архитектурный советник проекта **RekHarborBot**. Знаешь проект глубоко. Помогаешь с анализом, планированием, написанием кода и промптов для Qwen Code (исполнитель кода на сервере).

**Язык общения:** русский. Код и идентификаторы — английский.

---

## 2. ЧТО ТАКОЕ ПРОЕКТ

**RekHarborBot** — Telegram-бот, рекламная биржа для Telegram-каналов. Аналоги: Telega.in, Epicstars.

- Рекламодатель покупает размещение в каналах через арбитраж
- Владелец канала получает **80%**, платформа берёт **20%** комиссии
- **1 кредит = 1 RUB** (фиксированный курс)
- Роли: `advertiser`, `owner`, `both`, `admin`, `new`
- Тарифы: Free / Starter 299 кр / Pro 990 кр / Agency 2999 кр/мес

**Стек:** Python 3.13, aiogram 3.x, SQLAlchemy 2.0 async, FastAPI, Celery + Redis, PostgreSQL, Alembic.  
**AI:** Mistral (официальный API, SDK `mistralai>=1.12.4`). Переменная: `AI_MODEL=mistral-medium-latest`.  
**Платежи:** CryptoBot, ЮKassa, Telegram Stars.  
**Сервер:** `/opt/market-telegram-bot` на Ubuntu 22.04, Poetry.

---

## 3. РЕАЛЬНАЯ СТРУКТУРА ПРОЕКТА

```
src/
├── api/
│   ├── auth_utils.py
│   ├── dependencies.py
│   ├── main.py
│   └── routers/
│       ├── analytics.py
│       ├── auth.py
│       ├── billing.py
│       ├── campaigns.py
│       ├── channel_settings.py       ← Этап 6, частично
│       ├── channels.py
│       ├── placements.py             ← Этап 6, частично
│       └── reputation.py             ← Этап 6, частично
├── bot/
│   ├── filters/admin.py
│   ├── handlers/
│   │   ├── admin/         ← ai.py, analytics.py, campaigns.py, users.py, stats.py, monitoring.py
│   │   ├── advertiser/    ← analytics.py, analytics_chats.py, b2b.py, campaign_analytics.py,
│   │   │                     campaign_create_ai.py (НЕ ТРОГАТЬ), campaigns.py, comparison.py
│   │   ├── billing/       ← billing.py, templates.py
│   │   ├── infra/         ← callback_schemas.py
│   │   ├── owner/         ← channel_owner.py, channels_db.py, channels_db_mediakit.py
│   │   ├── placement/     ← arbitration.py, channel_settings.py, placement.py
│   │   └── shared/        ← cabinet.py, feedback.py, help.py, notifications.py, start.py
│   ├── keyboards/
│   │   ├── admin/admin.py
│   │   ├── advertiser/    ← campaign.py, campaign_ai.py (НЕ ТРОГАТЬ), campaign_analytics.py, comparison.py
│   │   ├── billing/billing.py
│   │   ├── owner/mediakit.py
│   │   ├── placement/     ← arbitration.py, channel_settings.py, placement.py
│   │   └── shared/        ← cabinet.py, channels_catalog.py, feedback.py, main_menu.py, pagination.py
│   ├── main.py
│   ├── middlewares/       ← fsm_timeout.py, throttling.py
│   ├── states/            ← ПЛОСКАЯ структура (не вложенная):
│   │                         admin.py, arbitration.py, campaign.py, campaign_create.py (НЕ ТРОГАТЬ),
│   │                         channel_owner.py, channel_settings.py, channels.py, comparison.py,
│   │                         feedback.py, mediakit.py, onboarding.py, placement.py
│   └── utils/             ← message_utils.py, safe_callback.py
├── config/settings.py     ← НЕ src/core/config.py
├── constants/             ← ai.py, content_filter.py, legal.py, parser.py, payments.py, tariffs.py
├── core/
│   ├── exceptions.py
│   └── services/          ← analytics_service.py, b2b_package_service.py, badge_service.py,
│                             billing_service.py, campaign_analytics_ai.py, category_classifier.py,
│                             comparison_service.py, cryptobot_service.py, link_tracking_service.py,
│                             mailing_service.py, mediakit_service.py, mistral_ai_service.py,
│                             notification_service.py, payout_service.py, placement_request_service.py,
│                             rating_service.py, reputation_service.py, review_service.py,
│                             timing_service.py, token_logger.py, user_role_service.py,
│                             xp_service.py (НЕ ТРОГАТЬ), yookassa_service.py
├── db/
│   ├── base.py
│   ├── migrations/        ← НЕ alembic/versions/ !
│   │   └── versions/      ← 38 миграций здесь
│   ├── models/            ← analytics.py, b2b_package.py, badge.py, campaign.py, category.py,
│   │                         channel_mediakit.py, channel_rating.py, channel_settings.py,
│   │                         content_flag.py, crypto_payment.py, mailing_log.py, notification.py,
│   │                         payout.py, placement_request.py, reputation_history.py,
│   │                         reputation_score.py, review.py, transaction.py, user.py,
│   │                         yookassa_payment.py
│   ├── repositories/      ← base.py, campaign_repo.py, category_repo.py, channel_settings_repo.py,
│   │                         chat_analytics.py, log_repo.py, notification_repo.py, payout_repo.py,
│   │                         placement_request_repo.py, reputation_repo.py, transaction_repo.py,
│   │                         user_repo.py
│   └── session.py
├── tasks/                 ← badge_tasks.py, billing_tasks.py, celery_app.py, celery_config.py,
│                             cleanup_tasks.py, gamification_tasks.py, mailing_tasks.py,
│                             notification_tasks.py, parser_tasks.py, placement_tasks.py, rating_tasks.py
└── utils/
    ├── content_filter/    ← filter.py, stopwords_ru.json
    └── telegram/          ← channel_rules_checker.py, llm_classifier.py, parser.py,
                              russian_lang_detector.py, sender.py, topic_classifier.py
```

---

## 4. АРХИТЕКТУРНЫЕ РЕШЕНИЯ (зафиксированы)

### 4.1 Валютная модель (двухвалютная система)
- `User.balance_rub` (Decimal) — рублёвый баланс для оплаты размещений
- `User.earned_rub` (Decimal) — заработанные рубли владельца канала (до выплаты)
- `User.credits` (Numeric) — кредиты для оплаты тарифных планов
- **1 кредит = 1 RUB** (фиксированный курс)
- `PayoutCurrency` enum содержит USDT/TON/RUB — не удалять (сломает миграции), default = RUB
- Мультивалютность отложена до явного бизнес-требования

### 4.2 Администратор — единый паттерн
- **`User.is_admin: bool`** — единственный источник правды для доступа к admin-панели
- **`UserPlan.ADMIN`** — остаётся для тарифных лимитов (безлимитные кампании, чаты). НЕ УДАЛЯТЬ
- **`settings.admin_ids`** — остаётся, используется только при `/start` для автовыставления `is_admin=True`
- `AdminFilter` проверяет `user.is_admin` из БД через session
- `_is_admin(user_id)` в `main_menu.py` — удалена, заменена параметром `is_admin: bool`

### 4.3 TransactionType enum
```python
TOPUP = "topup"
SPEND = "spend"
REFUND = "refund"
BONUS = "bonus"
ADJUSTMENT = "adjustment"
ESCROW_FREEZE = "escrow_freeze"
ESCROW_RELEASE = "escrow_release"
COMMISSION = "commission"
```

### 4.4 PlacementRequestRepo
Метод `create()` переименован в `create_placement()` — несовместимый override с BaseRepository.

### 4.5 BillingService
- `__init__(self)` — БЕЗ аргументов
- Реальный метод возврата: `refund_failed_placement(self, placement_id: int) -> bool`
- Методы эскроу: `freeze_escrow_for_placement` (~870), `release_escrow_for_placement` (~934), `release_escrow_funds` (~592)
- Двухвалютная система: `add_balance_rub()`, `buy_credits_for_plan()`, `freeze_campaign_funds()`

### 4.6 MailingService
- Добавлен параметр `bot: Bot | None = None` в `__init__`
- Бот больше не импортируется через `from src.bot.main import bot` внутри метода

### 4.7 AI-провайдер — только Mistral
- Единственный провайдер: **Mistral официальный SDK** (`from mistralai import Mistral`)
- Инициализация: `Mistral(api_key=settings.mistral_api_key)`
- Вызов: `await client.chat.complete_async(model=settings.ai_model, ...)`
- OpenRouter полностью удалён из проекта (была произведена замена 12.03.2026)

### 4.8 run_migrations.py (исправлен 12.03.2026)
- `Config("alembic.ini")` — с явным путём к конфигу
- Хардкод DATABASE_URL удалён — URL берётся из env.py
- Причина: `Config()` без аргумента создавал директорию `alembic/` в корне проекта

---

## 5. МОДЕЛИ ДАННЫХ (актуальное состояние)

### User (`src/db/models/user.py`)
Ключевые поля:
- `id`, `telegram_id` (UNIQUE), `username`, `first_name`
- `balance_rub` (Decimal) — баланс для размещений
- `earned_rub` (Decimal) — заработок владельца
- `credits` (Numeric) — баланс кредитов для тарифов
- `plan` (UserPlan enum: FREE/STARTER/PRO/BUSINESS/ADMIN)
- `plan_expires_at`, `plan_expiry_notified_at`
- `advertiser_xp`, `owner_xp`, `advertiser_level`, `owner_level` — геймификация (НЕ ТРОГАТЬ)
- `is_banned`, `is_active`, `notifications_enabled`
- `is_admin: bool` — флаг доступа к admin-панели
- `terms_accepted_at: datetime | None` — пользовательское соглашение
- `referral_code`, `referred_by_id`
- `login_streak_days`, `max_streak_days`, `last_login_at`
- `total_spent`, `total_earned`

### Transaction (`src/db/models/transaction.py`)
TransactionType enum: TOPUP, SPEND, REFUND, BONUS, ADJUSTMENT, ESCROW_FREEZE, ESCROW_RELEASE, COMMISSION

### PlacementRequest (`src/db/models/placement_request.py`)
Статусы: `pending_owner → counter_offer → pending_payment → escrow → published / failed / refunded / cancelled`  
Поля: `proposed_*` и `final_*` — до/после арбитража. `meta_json` (JSONB), `media_file_id` (String)  
Константы класса: `MIN_PRICE_PER_POST=100`, `PLATFORM_COMMISSION=0.20`, `MAX_POSTS_PER_DAY=5`, `MIN_HOURS_BETWEEN_POSTS=4`

### YooKassaPayment (`src/db/models/yookassa_payment.py`) ← НОВАЯ
Поля: `id`, `payment_id`, `user_id`, `amount_rub`, `credits`, `status`, `description`, `confirmation_url`, `idempotency_key`, `created_at`, `paid_at`

### ChannelMediakit (`src/db/models/channel_mediakit.py`) ← НОВАЯ
Поля: `id`, `channel_id`, `owner_user_id`, `custom_description`, `logo_file_id`, `banner_file_id`, `show_metrics` (JSONB), `theme_color`, `is_public`, `views_count`, `downloads_count`

### TopicCategory (`src/db/models/category.py`) ← НОВАЯ
Поля: `id`, `topic`, `subcategory`, `display_name_ru`, `is_active`, `sort_order`

### Миграции (38 штук, HEAD актуальный)
```
82cd153da6b8  initial_schema
  ↓ ... (старые миграции)
20260307_180000  add_channel_settings_and_placement_fields
  ↓
20260308_121947  merge_sprint3_migrations
  ↓
20260309_001000  make_payout_placement_id_nullable
  ↓
20260310_000000  backfill_subcategories
  ↓
20260311_000000_007  add_is_admin_to_users
  ↓
20260311_120000_008  add_yookassa_payment
  ↓
20260312_120000_009  add_terms_accepted_at_to_users
  ↓
20260312_160000_012  add_balance_rub_and_earned_rub_to_users  ← текущий HEAD (применена)
```

---

## 6. ФАЙЛЫ — НИКОГДА НЕ ТРОГАТЬ

```
src/core/services/xp_service.py
src/bot/handlers/advertiser/campaign_create_ai.py
src/bot/keyboards/advertiser/campaign_ai.py
src/bot/keyboards/shared/main_menu.py      ← тексты кнопок и callback_data
src/bot/handlers/shared/start.py           ← только если не указано явно
src/bot/states/campaign_create.py
src/db/migrations/versions/               ← только читать, новые создавать отдельно
```

---

## 7. СТАТУС РЕФАКТОРИНГА

| Этап | Содержание | Статус |
|------|------------|--------|
| 0 | Архитектура меню (main_menu.py, analytics.py, start.py) | ✅ 100% |
| 1 | Модели данных + 38 миграций Alembic | ✅ 100% |
| 2 | Репозитории + Сервисы + устранение mypy-ошибок | ✅ 100% |
| **3** | **Handlers: placement.py, arbitration.py, channel_settings.py** | **🔄 ~60%** |
| **4** | **FSM States** | **🔄 ~40%** |
| **5** | **Keyboards: placement/, arbitration/, channel_settings/** | **🔄 ~50%** |
| **6** | **API routers: placements.py, channel_settings.py, reputation.py** | **🔄 ~30%** |
| **7** | **Тесты (6 файлов)** | **🔄 ~40%** |

---

## 8. АРХИТЕКТУРА МЕНЮ v3.0 (реализована, не менять)

**Главное меню (shared, 4 кнопки):**  
`main:cabinet`, `main:change_role`, `main:help`, `main:feedback`

**Advertiser меню (5 кнопок):**  
`main:analytics`, `main:create_campaign`, `main:my_campaigns`, `main:b2b`, `main:main_menu`

**Owner меню (5 кнопок):**  
`main:owner_analytics`, `main:my_channels`, `main:my_requests`, `main:payouts`, `main:main_menu`

⚠️ `main:analytics` ≠ `main:owner_analytics` — разные callback, разные handlers, разные данные.

---

## 9. ФИНАНСОВАЯ МОДЕЛЬ (ЮKassa — актуальная спека)

### Пакеты пополнения через ЮKassa

| Сумма (₽) | Кредиты | Бонус |
|-----------|---------|-------|
| 100       | 100     | —     |
| 300       | 330     | +10%  |
| 500       | 575     | +15%  |
| 1 000     | 1 200   | +20%  |
| 3 000     | 3 750   | +25%  |

### Роль ЮKassa
- ✅ Входящие платежи от рекламодателей
- ❌ Исходящие выплаты владельцам (платформа платит сама)
- ❌ Эскроу-операции (внутренние)
- ❌ Денежные возвраты — только кредиты на баланс

### Политика возвратов
- Технический сбой до заморозки эскроу: 100% → кредиты на баланс
- Сбой после заморозки эскроу: 50% → кредиты на баланс
- По желанию пользователя: не предусмотрен

---

## 10. БИЗНЕС-ПРАВИЛА

### Флоу заявки на размещение
```
pending_owner → counter_offer → pending_payment → escrow → published
     ↓               ↓                ↓              ↓
  rejected        cancelled        refunded        failed → refunded
```

### SLA таймеры
- Ответ владельца: 24ч
- Оплата: 24ч
- Контр-предложение: 24ч × макс 3 раунда
- Повтор публикации: 1ч
- Бан: 7 дней → сброс репутации до 2.0

### Штрафы репутации (advertiser)
- Отмена до подтверждения: −5
- Отмена после эскроу: −20
- 3 отмены за 30 дней: −20 + предупреждение

### Штрафы репутации (owner)
- Невалидный отказ 1й: −10
- Невалидный отказ 2й: −15
- Невалидный отказ 3й: −20 + бан 7 дней

### Восстановление репутации
- 30 дней без нарушений: +5
- После бана: сброс до 2.0
- 5+ нарушений: перманентная блокировка

### Финансовые константы
- Комиссия платформы: 20%
- Владелец получает: 80%
- Возврат до эскроу: 100% кредитами
- Возврат после эскроу: 50% кредитами
- Минимальная цена поста: 100 кредитов
- Минимальная выплата: 500 кредитов

### Валидация rejection_reason
```python
min_length = 10 символов
must_contain = re.search(r'[а-яёa-z]', reason, re.IGNORECASE)
blacklist = ["asdfgh", "aaaaaa", "123456", "qwerty", "нет", "no", "не хочу"]
```

---

## 11. ПАТТЕРНЫ ОШИБОК И СТАНДАРТНЫЕ ИСПРАВЛЕНИЯ

### str|None → .split()
```python
# БЫЛО (ошибка):
parts = callback.data.split(":")
# СТАЛО:
if callback.data is None:
    return
parts = callback.data.split(":")
```

### safe_callback_edit — неправильный аргумент
```python
# БЫЛО: await safe_callback_edit(callback.message, text, ...)
# СТАЛО: await safe_callback_edit(callback, text, ...)
```

### InlineKeyboardBuilder без .as_markup()
```python
# БЫЛО: reply_markup=kb_builder
# СТАЛО: reply_markup=kb_builder.as_markup()
```

### int|None где ожидается int
```python
if channel.owner_user_id is None:
    logger.error(...)
    return
await service.method(owner_id=channel.owner_user_id)
```

### _notify_* функции без return type
```python
async def _notify_create_request(...) -> None:
```

---

## 12. КОНФИГУРАЦИЯ

```python
# src/config/settings.py — ключевые переменные
bot_token: str                    # BOT_TOKEN
database_url: PostgresDsn         # DATABASE_URL
redis_url: RedisDsn               # REDIS_URL
mistral_api_key: str              # MISTRAL_API_KEY
ai_model: str                     # AI_MODEL = "mistral-medium-latest"
ai_timeout: int                   # AI_TIMEOUT = 60
ai_max_tokens: int                # AI_MAX_TOKENS = 1500
ai_temperature: float             # AI_TEMPERATURE = 0.7
admin_ids_raw: str                # ADMIN_IDS → парсится в list[int]
platform_commission: float        # PLATFORM_COMMISSION = 0.20
min_price_per_post: int           # MIN_PRICE_PER_POST = 100
min_payout: int                   # MIN_PAYOUT = 500
placement_timeout_hours: int      # PLACEMENT_TIMEOUT_HOURS = 24
payment_timeout_hours: int        # PAYMENT_TIMEOUT_HOURS = 24
max_counter_offers: int           # MAX_COUNTER_OFFERS = 3
yookassa_shop_id: str             # YOOKASSA_SHOP_ID
yookassa_secret_key: str          # YOOKASSA_SECRET_KEY
yookassa_return_url: str          # YOOKASSA_RETURN_URL
tariff_cost_free: int             # 0
tariff_cost_starter: int          # 299
tariff_cost_pro: int              # 990  ← проверить (возможно 999)
tariff_cost_business: int         # 2999 ← тариф называется agency в документации
```

⚠️ **Требует проверки:** `tariff_cost_pro` (990 или 999?) и имя тарифа `business` vs `agency`

---

## 13. КАК РАБОТАТЬ С ПРОМПТАМИ ДЛЯ QWEN CODE

### Протокол взаимодействия (JSON-формат)

Все промты генерировать по JSON-протоколу со следующими полями:

```json
{
  "task": "название задачи",
  "stage": "номер этапа 0-7",
  "context": "что уже сделано, что является зависимостью",
  "specifications": {
    "description": "детальное описание",
    "business_constants": "все числовые константы явно",
    "patterns": "Repository / Service Layer / FSM"
  },
  "files_to_create": [{"path": "src/...", "purpose": "зачем"}],
  "files_to_modify": [{"path": "src/...", "changes": "что именно"}],
  "files_to_read": [{"path": "src/...", "reason": "зачем читать"}],
  "never_touch": ["список файлов"],
  "acceptance_criteria": ["ruff = 0", "mypy = 0"],
  "checklist": ["прочитан каждый файл", "анализ пройден", "отчёт заполнен"]
}
```

### Золотые правила промптинга Qwen
- Всегда: "прочитай файл перед правкой" (`sed -n 'X,Yp' file`)
- Явно прописывать все бизнес-константы (штрафы, таймеры)
- Указывать реальные сигнатуры методов из `confirmed_facts`
- Формат отчёта: валидный JSON без markdown-обёртки
- Никогда не трогать файлы из `never_touch`
- Шаги: сначала READ, потом MODIFY

### Interaction protocol
```
step_1: read_before_write — каждый файл читать перед изменением
step_2: one_file_at_a_time — файлы строго по одному
step_3: static_analysis — ruff + mypy + bandit + flake8 после каждого этапа
step_4: structured_report — markdown-отчёт с разделами
```

---

## 14. КОМАНДЫ ДЛЯ ПРОВЕРКИ СОСТОЯНИЯ

```bash
# Текущий счёт mypy
poetry run mypy src/ --ignore-missing-imports 2>&1 | grep "^src/" | sed 's/:[0-9]*:.*//' | sort | uniq -c | sort -rn | head -20

# Ruff
poetry run ruff check src/ --output-format=concise

# Статус миграций
cd /opt/market-telegram-bot && poetry run alembic current

# Дерево файлов
tree -f src --noreport | grep "\.py$" | grep -v __pycache__

# Поиск OpenRouter (должно быть 0 результатов после замены)
grep -rn "openrouter" src/ --include="*.py" -i

# Проверка миграций в правильной директории
grep "script_location" alembic.ini
```

---

## 15. ДЕЛЬТА ИЗМЕНЕНИЙ (11.03 → 12.03.2026)

| Параметр | Было (11.03) | Стало (12.03) |
|----------|-------------|---------------|
| AI провайдер | OpenRouter | Mistral official SDK |
| Переменная | `openrouter_api_key` | `mistral_api_key` + `ai_model` |
| Валютная модель | только `credits` | `balance_rub` + `credits` + `earned_rub` |
| Миграция 007 | создана, не применена | применена |
| HEAD миграции | 007 | 012 |
| Всего миграций | ~32 | 38 |
| Новые модели | — | `YooKassaPayment`, `ChannelMediakit`, `TopicCategory` |
| `terms_accepted_at` | — | добавлено в `User` |
| Статус Этапа 2 | 🔄 mypy 119 ошибок | ✅ завершён |
| `run_migrations.py` | `Config()` без аргумента | `Config("alembic.ini")` |
| Директория `alembic/` в корне | появлялась | исправлено |

---

## 16. ВАЖНЫЕ ПРЕДУПРЕЖДЕНИЯ

### ⚠️ XP ≠ Репутация
- `User.advertiser_xp/owner_xp/advertiser_level/owner_level` — геймификация, НЕ ТРОГАТЬ
- `ReputationScore` — отдельная система доверия (0.0–10.0)

### ⚠️ Два разных поля is_admin
- `User.is_admin` — администратор платформы
- `TelegramChat.bot_is_admin` — бот является администратором канала. НЕ ПУТАТЬ

### ⚠️ UserPlan.ADMIN ≠ User.is_admin
- `UserPlan.ADMIN` — тарифный план с безлимитами
- `User.is_admin` — булев флаг доступа к admin-панели

### ⚠️ PlacementRequestRepo.create_placement()
Метод переименован из `create()` — если в новом коде нужно создать заявку, использовать `create_placement()`.

### ⚠️ bot в MailingService
`bot: Bot | None = None` — опциональный параметр. При создании MailingService в production передавать реальный экземпляр бота.

### ⚠️ min_payout расхождение
В `settings.py` может быть `MIN_PAYOUT = 100`, но бизнес-правило: **500 кредитов**. Приоритет — бизнес-правило.

### ⚠️ tariff_cost_pro
Спецификация ЮKassa говорит 990 ₽, в коде может быть 999. Требует явной проверки.

### ⚠️ Название тарифа Agency
В коде тариф может называться `business`, в документации — `agency`. Требует проверки.

---

*Документ обновлён 12.03.2026 на основе аудита Qwen Code и диалога с архитектурным советником.*
