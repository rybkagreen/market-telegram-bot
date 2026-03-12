# RekHarborBot — Project Context

> **v4.2 | 12.03.2026**
> Источник правды для всех промтов Qwen Code.
> При конфликте с любым другим файлом — этот документ и файлы на диске имеют приоритет.

---

## КРИТИЧЕСКИЕ ИЗМЕНЕНИЯ v4.2 (прочитай первым)

| # | Параметр | v3.x | v4.2 | Файл |
|---|----------|------|------|------|
| 1 | `PLATFORM_COMMISSION` | 0.20 | **0.15** | payments.py |
| 2 | `OWNER_SHARE` | 0.80 | **0.85** | payments.py |
| 3 | `NPD_TAX_RATE` | 0.04 | **удалён** | — |
| 4 | `PLATFORM_TAX_RATE` | — | **0.06** (УСН) | payments.py |
| 5 | `PAYOUT_FEE_RATE` | — | **0.015** | payments.py |
| 6 | `VELOCITY_MAX_RATIO` | — | **0.80** | payments.py |
| 7 | `VELOCITY_WINDOW_DAYS` | — | **30** | payments.py |
| 8 | `COOLDOWN_HOURS` | — | **24** | payments.py |
| 9 | `MIN_TOPUP` | 100 | **500** | payments.py |
| 10 | `MIN_PRICE_PER_POST` | 100 | **1000** | payments.py |
| 11 | `MIN_CAMPAIGN_BUDGET` | — | **2000** | payments.py |
| 12 | `MIN_PAYOUT` | 500 | **1000** | payments.py |
| 13 | `tariff_cost_starter` | 299/290 | **490** | settings.py |
| 14 | `tariff_cost_pro` | 990/999 | **1490** | settings.py |
| 15 | `tariff_cost_business` | 2999/2990 | **4990** | settings.py |
| 16 | Бонусные пакеты | были | **удалены** | payments.py |
| 17 | Форматы публикации | 1 | **5** | payments.py |
| 18 | Self-dealing | не было | **запрещено** | placement_request_service.py |
| 19 | Velocity check | post-MVP | **MVP** | payout_service.py |
| 20 | `PayoutRequest` | простая | **gross/fee/net** | payout.py |

---

## Project Overview

**RekHarborBot** — Telegram-бот, рекламная биржа. Каналы 1K–50K подписчиков (MVP).

| Field | Value |
|---|---|
| Python | 3.13 |
| Framework | aiogram 3.x |
| DB | PostgreSQL + SQLAlchemy 2.0 async |
| Queue | Celery + Redis |
| API | FastAPI |
| Migrations | Alembic |
| AI | Mistral official SDK (`mistralai>=1.12.4`) |
| Payments | YooKassa only (Stars и CryptoBot исключены) |
| Tax | ИП УСН 6% (выручка > 2.4 млн/год → не НПД) |

---

## Financial Constants v4.2

```python
# src/constants/payments.py — полная спецификация

from decimal import Decimal

PLATFORM_COMMISSION   = Decimal("0.15")   # 15% с размещений → не 0.20!
OWNER_SHARE           = Decimal("0.85")   # 85% владельцу → не 0.80!
YOOKASSA_FEE_RATE     = Decimal("0.035")  # платит пользователь поверх пополнения
PLATFORM_TAX_RATE     = Decimal("0.06")   # УСН 6% → не NPD_TAX_RATE!
PAYOUT_FEE_RATE       = Decimal("0.015")  # комиссия за вывод (новый v4.2)
VELOCITY_MAX_RATIO    = Decimal("0.80")   # макс. вывод/пополнения за 30 дней
VELOCITY_WINDOW_DAYS  = 30
COOLDOWN_HOURS        = 24
MIN_TOPUP             = Decimal("500")
MAX_TOPUP             = Decimal("300000")
MIN_CAMPAIGN_BUDGET   = Decimal("2000")
MIN_PRICE_PER_POST    = Decimal("1000")
MIN_PAYOUT            = Decimal("1000")

QUICK_TOPUP_AMOUNTS: list[int] = [500, 1000, 2000, 5000, 10000, 20000]

FORMAT_MULTIPLIERS: dict[str, Decimal] = {
    "post_24h": Decimal("1.0"),
    "post_48h": Decimal("1.4"),
    "post_7d":  Decimal("2.0"),
    "pin_24h":  Decimal("3.0"),
    "pin_48h":  Decimal("4.0"),
}

FORMAT_DURATIONS_SECONDS: dict[str, int] = {
    "post_24h": 86400,
    "post_48h": 172800,
    "post_7d":  604800,
    "pin_24h":  86400,
    "pin_48h":  172800,
}

PLAN_PRICES: dict[str, Decimal] = {
    "free":    Decimal("0"),
    "starter": Decimal("490"),
    "pro":     Decimal("1490"),
    "agency":  Decimal("4990"),  # enum code UserPlan: "business"
}

PLAN_LIMITS: dict[str, dict] = {
    "free":    {"active_campaigns": 1,  "ai_per_month": 0,  "formats": ["post_24h"]},
    "starter": {"active_campaigns": 5,  "ai_per_month": 3,  "formats": ["post_24h","post_48h"]},
    "pro":     {"active_campaigns": 20, "ai_per_month": 20, "formats": ["post_24h","post_48h","post_7d"]},
    "agency":  {"active_campaigns": -1, "ai_per_month": -1, "formats": ["post_24h","post_48h","post_7d","pin_24h","pin_48h"]},
}
```

---

## User Roles

| Роль | Enum | Доступ |
|------|------|--------|
| Новый | `new` | Онбординг |
| Рекламодатель | `advertiser` | Кампании, аналитика |
| Владелец | `owner` | Каналы, выплаты |
| Обе роли | `both` | Комбинированное меню |
| Администратор | `admin` | `User.is_admin=True` |

---

## Database Models

### User

| Поле | Тип | Назначение |
|------|-----|------------|
| `balance_rub` | Numeric(12,2) | Баланс для размещений (пополняется ЮKassa) |
| `earned_rub` | Numeric(12,2) | Заработок владельца до выплаты |
| `credits` | Numeric(12,2) | Только для тарифных подписок — НЕ для размещений |
| `plan` | UserPlan | free/starter/pro/**business**/admin |
| `is_admin` | bool | Не путать с `TelegramChat.bot_is_admin` |
| `advertiser_xp` | int | НЕ ТРОГАТЬ — геймификация |
| `owner_xp` | int | НЕ ТРОГАТЬ |

### PlatformAccount (singleton id=1) — НОВАЯ

```python
class PlatformAccount(Base):
    __tablename__ = "platform_account"
    id:                  int     # всегда 1
    escrow_reserved:     Decimal # = SUM(placements.final_price WHERE status='escrow')
    payout_reserved:     Decimal # = SUM(payouts.gross_amount WHERE pending/processing)
    profit_accumulated:  Decimal # = SUM(15% эскроу + 1.5% payout fees)
    total_topups:        Decimal # исторические desired_balance
    total_payouts:       Decimal # исторические net_amount
    updated_at:          datetime
```

### PayoutRequest — обновлённая (v4.2)

```python
# Новые поля (добавить миграцией):
gross_amount: Decimal  # запрошено владельцем
fee_amount:   Decimal  # gross × 0.015
net_amount:   Decimal  # gross - fee (фактически перечисляется)
tax_withheld: Decimal  # NULL (MVP Вариант A); post-MVP Вариант B
```

**Механика:**
```
gross=10000 → fee=150 → net=9850
UI: "Будет перечислено: 9 850 ₽ (комиссия платформы 1.5%)"
earned_rub -= gross_amount
platform.profit_accumulated += fee_amount  # сразу
```

### PlacementRequest — новые поля

```python
class PublicationFormat(str, Enum):
    POST_24H = "post_24h"
    POST_48H = "post_48h"
    POST_7D  = "post_7d"
    PIN_24H  = "pin_24h"
    PIN_48H  = "pin_48h"

publication_format:   PublicationFormat = POST_24H
message_id:           int | None = None
scheduled_delete_at:  datetime | None = None
deleted_at:           datetime | None = None
```

Статусы: `PENDING_OWNER → COUNTER_OFFER → PENDING_PAYMENT → ESCROW → PUBLISHED → COMPLETED`

### ChannelSettings — новые поля

```python
allow_format_post_24h: bool = True
allow_format_post_48h: bool = True
allow_format_post_7d:  bool = False
allow_format_pin_24h:  bool = False
allow_format_pin_48h:  bool = False
```

### Transaction enum — дополнение

```python
PAYOUT_FEE = "payout_fee"  # новый тип v4.2: 1.5% комиссия за вывод
```

Удалены (не использовать): `SPEND`, `ADJUSTMENT`, `BONUS`, `WITHDRAWAL`.

---

## Service Contracts

### BillingService — `__init__(self)` без аргументов

```python
def calculate_topup_payment(desired_balance: Decimal) -> dict:
    # → {"desired_balance": D, "fee_amount": D, "gross_amount": D}
    # fee = desired × 0.035, gross = desired + fee

async def process_topup_webhook(session, payment_id, gross_amount, metadata):
    # Зачислять metadata["desired_balance"] — НЕ gross_amount!

async def freeze_escrow(session, user_id, placement_id, amount):
    # SELECT FOR UPDATE
    # assert amount >= MIN_CAMPAIGN_BUDGET (2000)
    # assert user.balance_rub >= amount

async def release_escrow(session, placement_id):
    # owner_amount = final_price × 0.85
    # platform_fee = final_price × 0.15
    # platform.profit_accumulated += platform_fee
```

### PayoutService

```python
async def check_velocity(session, user_id, requested_amount) -> None:
    # topups_30d = SUM топапы за 30 дней
    # payouts_30d = SUM выплаты за 30 дней
    # if topups_30d == 0: return
    # ratio = (payouts_30d + requested_amount) / topups_30d
    # if ratio > 0.80: raise VelocityCheckError(...)

async def create_payout(session, user_id, gross_amount) -> PayoutRequest:
    # Проверки: earned_rub >= gross, нет активного PayoutRequest
    # await self.check_velocity(...)
    # fee = (gross × 0.015).quantize(0.01)
    # net = gross - fee
    # earned_rub -= gross
    # platform.payout_reserved += gross
    # platform.profit_accumulated += fee
    # Transaction(PAYOUT_FEE, fee)
```

### PlacementRequestService

```python
async def create_placement_request(session, advertiser_id, channel_id, ...) -> PlacementRequest:
    # 1. ПЕРВАЯ проверка (до расчётов):
    if channel.owner_id == advertiser_id:
        raise SelfDealingError("Нельзя размещать рекламу на собственном канале")
    # 2. Проверка формата по тарифу:
    if publication_format not in PLAN_LIMITS[advertiser.plan]["formats"]:
        raise PlanLimitError(...)
    # 3. Расчёт цены:
    final_price = channel_settings.price_per_post × FORMAT_MULTIPLIERS[publication_format]
    # 4. Проверка MIN_CAMPAIGN_BUDGET:
    if final_price < MIN_CAMPAIGN_BUDGET:
        raise ValueError(...)
```

⚠️ В репозитории: `create_placement()`, не `create()`!

### Exceptions (`src/core/exceptions.py`) — добавить

```python
class SelfDealingError(ValueError): pass
class VelocityCheckError(PermissionError): pass
class InsufficientPermissionsError(PermissionError): pass
class PlanLimitError(PermissionError): pass
```

### Celery (`src/tasks/publication_tasks.py`) — НОВЫЙ

```python
@celery_app.task(queue="critical", max_retries=3)
async def publish_placement(placement_id): ...
    # check_bot_permissions → send_message → optional pin
    # release_escrow → schedule delete/unpin ETA
    # retry(countdown=3600) при ошибке

@celery_app.task(queue="critical")
async def delete_published_post(placement_id): ...
    # except TelegramBadRequest: pass → status=COMPLETED

@celery_app.task(queue="critical")
async def unpin_and_delete_post(placement_id): ...
    # unpin → delete → except TelegramBadRequest: pass
```

### MistralAIService

```python
from mistralai import Mistral
client = Mistral(api_key=settings.mistral_api_key)
await client.chat.complete_async(model=settings.ai_model, ...)
# Переменные: MISTRAL_API_KEY, AI_MODEL=mistral-medium-latest
# OpenRouter УДАЛЁН — OPENROUTER_API_KEY не существует
```

---

## FSM States

### TopupStates (НОВЫЙ)
```python
class TopupStates(StatesGroup):
    entering_amount  = State()  # ввод суммы
    confirming       = State()  # показ desired/fee/gross
    waiting_payment  = State()  # ожидание вебхука
```

### PlacementStates, ArbitrationStates, ChannelSettingsStates — без изменений
### CampaignCreateState — НЕ ТРОГАТЬ (13 состояний)

---

## Menu Architecture v3.0 (НЕ МЕНЯТЬ)

- Главное: `main:cabinet` | `main:change_role` | `main:help` | `main:feedback`
- Advertiser: `main:analytics` | `main:create_campaign` | `main:my_campaigns` | `main:b2b` | `main:main_menu`
- Owner: `main:owner_analytics` | `main:my_channels` | `main:my_requests` | `main:payouts` | `main:main_menu`

⚠️ `main:analytics` ≠ `main:owner_analytics`

---

## UI Elements (v4.2)

### Cabinet владельца — налоговая подсказка
```
💰 Начислено за месяц: {monthly_earned} ₽
earned_rub: {earned_rub} ₽ (доступно к выводу)
📋 Вы самостоятельно несёте ответственность за уплату налогов
```

### Топап — двухшаговый
```
Шаг 1: выбор суммы → [500][1000][2000][5000][10000][20000] или ввод
Шаг 2: подтверждение → "Зачислить: 10 000 ₽ / Комиссия: 350 ₽ / К оплате: 10 350 ₽"
```

### Вывод — с комиссией
```
"Будет перечислено: 9 850 ₽ (комиссия платформы 1.5%)"
```

---

## Environment Variables

| Variable | Value / Source |
|---|---|
| `BOT_TOKEN` | Telegram BotFather |
| `ADMIN_IDS` | `123456789,987654321` |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `MISTRAL_API_KEY` | console.mistral.ai |
| `AI_MODEL` | `mistral-medium-latest` |
| `YOOKASSA_SHOP_ID` | ЮKassa |
| `YOOKASSA_SECRET_KEY` | ЮKassa |
| `YOOKASSA_RETURN_URL` | `https://t.me/YOUR_BOT_USERNAME` |

Не существует: `OPENROUTER_API_KEY`, `CRYPTOBOT_TOKEN`, `STARS_ENABLED`

---

## Tariffs

| Тариф | Цена | Enum | settings.py attr |
|-------|------|------|-----------------|
| Free | 0 ₽ | `free` | `tariff_cost_free=0` |
| Starter | 490 ₽ | `starter` | `tariff_cost_starter=490` |
| Pro | 1 490 ₽ | `pro` | `tariff_cost_pro=1490` |
| Agency | 4 990 ₽ | `business` ⚠️ | `tariff_cost_business=4990` |

```python
# src/constants/tariffs.py
PLAN_DISPLAY_NAMES: dict[str, str] = {
    "free": "Free", "starter": "Starter", "pro": "Pro", "business": "Agency"
}
PLAN_EMOJIS: dict[str, str] = {
    "free": "🆓", "starter": "🚀", "pro": "💎", "business": "🏢"
}
```

---

## Code Quality

```bash
ruff check src/ --fix && ruff format src/
mypy src/ --ignore-missing-imports
bandit -r src/ -ll
flake8 src/ --max-line-length=120 --extend-ignore=E203,W503
alembic check && alembic current
```

Target: Ruff 0, MyPy 0, Bandit High 0, Flake8 0.

---

## Common Bugs

| Баг | Fix |
|-----|-----|
| `safe_callback_edit(callback.message, ...)` | `safe_callback_edit(callback, ...)` |
| `reply_markup=kb_builder` | `reply_markup=kb_builder.as_markup()` |
| `create()` вместо `create_placement()` | Использовать `create_placement()` |
| Celery падает на TelegramBadRequest | `except TelegramBadRequest: pass` |
| `alembic/` в корне | `Config("alembic.ini")` с явным путём в run_migrations.py |
| Зачисление gross вместо desired | `metadata["desired_balance"]` в webhook |

---

## NEVER TOUCH

```
src/core/services/xp_service.py
src/bot/handlers/advertiser/campaign_create_ai.py
src/bot/keyboards/advertiser/campaign_ai.py
src/bot/keyboards/shared/main_menu.py
src/bot/states/campaign_create.py
src/db/migrations/versions/  ← только читать
```

---

## Sprint Map

| Спринт | Содержание | Зависит от |
|--------|------------|-----------|
| S-01 | Constants + Settings + Tariffs | — |
| S-02 | DB Models (5 файлов + exceptions) | S-01 |
| S-03 | Alembic Migrations (6 шт.) | S-02 |
| S-04 | Repositories (platform_account + updates) | S-03 |
| S-05 | BillingService v4.2 | S-04 |
| S-06 | PayoutService v4.2 (velocity, fee) | S-04 |
| S-07 | PublicationService + Celery tasks | S-05 |
| S-08 | PlacementRequestService | S-05, S-06 |
| S-09 | FSM States + Keyboards | S-01 |
| S-10 | Handler: топап (двухшаговый) | S-05, S-09 |
| S-11 | Handler: channel_settings (форматы) | S-08, S-09 |
| S-12 | Handler: campaign creation (формат + цена) | S-08, S-09 |
| S-13 | Cabinet + Admin dashboard | S-05, S-06 |
| S-14 | Health-check API | S-04 |
| S-15 | Tests | S-05..S-08 |

---

## Refactoring Status

| Этап | Статус |
|------|--------|
| 0 — Меню v3.0 | ✅ |
| 1 — Модели + миграции | ✅ |
| 2 — Репозитории + сервисы | ✅ |
| 3–7 | 🔄 частично |
| **v4.2 финансовая модель** | ❌ S-01 следующий |

*RekHarborBot QWEN.md v4.2 | 12.03.2026*
