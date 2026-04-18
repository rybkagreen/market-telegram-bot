# RekHarborBot — Project Context

> **v4.4 | 08.04.2026**
> Источник правды для всех промтов Qwen Code.
> При конфликте с любым другим файлом — этот документ и файлы на диске имеют приоритет.

---

## КРИТИЧЕСКИЕ ИЗМЕНЕНИЯ v4.4 (прочитай первым)

| # | Изменение | v4.3 | v4.4 | Файл |
|---|-----------|------|------|------|
| 1 | **Billing prices** | 299/999/2999 (хардкод) | **490/1490/4990 (settings)** | billing.py |
| 2 | **Login-code rate limit** | нет | **10/час per IP** | auth_login_code.py |
| 3 | **Redis connection** | per-request pool | **shared pool (dependencies.py)** | dependencies.py |
| 4 | **is_active check** | нет в Login Widget | **проверка banned** | auth_login_widget.py |
| 5 | **Webhook error handling** | bare except Exception | **specific exceptions + retry** | billing.py |
| 6 | **Telegram widget 500** | column language_code missing | **migration t1u2v3w4x5y6** | migration |
| 7 | **SonarQube config** | mini_app only | **src + mini_app + web_portal** | sonar-project.properties |
| 8 | **Accessibility** | table без заголовков | **<thead> + <th scope>** | AdminDashboard.tsx |
| 9 | **Keyboard navigation** | 9 divs без onKeyDown | **role=button, tabIndex** | 8 файлов web_portal |
| 10 | **Unused params** | S1172 warnings (45) | **_ prefix + noqa** | notifications.py, stub_ord_provider.py |
| 11 | **Deployment rules** | нет | **ОБЯЗАТЕЛЬНЫЙ rebuild nginx без кэша** | QWEN.md |

---

## КРИТИЧЕСКИЕ ИЗМЕНЕНИЯ v4.3 (прочитай первым)

| # | Изменение | v4.2 | v4.3 | Файл |
|---|-----------|------|------|------|
| 1 | **Выплаты** | CryptoBot API | **Ручные через admin** | payout_service.py |
| 2 | **B2B пакеты** | были | **удалены** | billing.py, main_menu.py |
| 3 | **Admin панель Mini App** | нет | **7 экранов, 11 endpoints** | admin.py, mini_app/src/screens/admin/ |
| 4 | **Feedback система** | нет | **полная (пользователь → админ)** | feedback.py, UserFeedback |
| 5 | **ESCROW-001** | release при публикации | **release ТОЛЬКО после удаления поста** | publication_service.py |
| 6 | **FSM States** | частично | **5 файлов + 2 middleware** | states/, middlewares/ |
| 7 | **Ruff SIM102/SIM103** | есть | **исправлены** | services/*.py |
| 8 | **is_banned** | используется | **заменено на is_active** | dependencies.py |
| 9 | **Тесты** | 39 | **101 тест** | tests/ |
| 10 | **Документация** | 1 файл | **20+ отчётов** | docs/, reports/ |
| 11 | **Юридические профили** | нет | **LegalProfile + Contract** | legal_profile.py, contract.py |
| 12 | **ОРД-регистрация** | нет | **OrdRegistration** | ord_registration.py, ord_service.py |
| 13 | **Аудит-лог** | нет | **AuditLog** | audit_log.py, audit_middleware.py |
| 14 | **Шифрование полей** | нет | **Field Encryption** | field_encryption.py |
| 15 | **GlitchTip** | Sentry | **GlitchTip + Sentry** | settings.py, celery_config.py |
| 16 | **SonarQube** | нет | **SonarQube** | sonar-project.properties |
| 17 | **Gitleaks** | нет | **Gitleaks** | .gitleaks.toml |
| 18 | **Реферальная программа** | нет | **ReferralStats** | useReferralStats.ts |
| 19 | **Видео в кампаниях** | нет | **VideoUploader** | CampaignVideo.tsx |
| 20 | **Трекинг ссылок** | нет | **ClickTracking** | click_tracking.py |

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
| Payments | YooKassa only (Stars и CryptoBot исключены в v4.3) |
| Tax | ИП УСН 6% (выручка > 2.4 млн/год → не НПД) |
| Admin UI | Mini App + Telegram Bot (v4.3) |
| Feedback | Full system (user → admin → response) (v4.3) |

---

## 🤖 AGENT ROUTING (Auto-Dispatch)

При получении задачи автоматически вызывай нужного суб-агента из `.qwen/agents/`:

| Агент | Зона ответственности |
|-------|---------------------|
| `@backend-core` | aiogram handlers, SQLAlchemy 2 async repos, Celery tasks, Alembic migrations, FastAPI routers, бизнес-логика, FSM states, escrow/payout/placement сервисы |
| `@frontend-miniapp` | React/TS Mini App, Zustand stores, TanStack Query, API контракты, UI/UX, CSS modules, admin screens, referral UI, video upload, link tracking |
| `@devops-sre` | Docker Compose, Nginx, CI/CD, Xray/Privoxy proxy, healthchecks, secrets, GlitchTip, SonarQube, Gitleaks, Flower, backup/restore |
| `@qa-analysis` | pytest + testcontainers, ruff, mypy, bandit, flake8, coverage gates ≥80%, SonarQube quality gates |
| `@prompt-orchestrator` | Многошаговые задачи: research → implementation prompt → verification, архитектура, рефакторинг, миграции, technical debt audits |
| `@docs-architect-aaa` | Документация: Diátaxis framework, Mermaid диаграммы, AAA структура, code-verified references, onboarding materials |

**Правила:**
- Не выполняй код за пределами своей зоны без явного вызова суб-агента
- Для комплексных задач сначала вызови `@prompt-orchestrator` для декомпозиции
- Для тестирования изменений вызывай `@qa-analysis` после `@backend-core` или `@frontend-miniapp`

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
    "business":  {"active_campaigns": -1, "ai_per_month": -1, "formats": ["post_24h","post_48h","post_7d","pin_24h","pin_48h"]},  # HOTFIX: НЕ 'agency'!
}
```

**⚠️ HOTFIX:** `UserPlan.BUSINESS.value == 'business'`, поэтому `PLAN_LIMITS` использует ключ `'business'` (НЕ `'agency'`). `'agency'` встречается только в `PLAN_PRICES` для обратной совместимости.

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

### PayoutRequest — обновлённая (v4.2/v4.3)

```python
# Новые поля (добавить миграцией):
gross_amount: Decimal  # запрошено владельцем
fee_amount:   Decimal  # gross × 0.015
net_amount:   Decimal  # gross - fee (фактически перечисляется)
tax_withheld: Decimal  # NULL (MVP Вариант A); post-MVP Вариант B

# v4.3: Выплаты ручные — admin одобряет вручную через /admin панель
# CryptoBot service удалён, payout_service.py Шаг 5 — ручная выплата
```

**Механика:**
```
gross=10000 → fee=150 → net=9850
UI: "Будет перечислено: 9 850 ₽ (комиссия платформы 1.5%)"
earned_rub -= gross_amount
platform.profit_accumulated += fee_amount  # сразу
status = 'pending' → admin одобряет вручную → 'completed'
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

## v4.3 New Database Models

### LegalProfile (v4.3)

```python
class LegalProfile(Base):
    __tablename__ = "legal_profiles"
    id:                  int     # PK
    user_id:             int     # FK → users.id (unique)
    legal_status:        LegalStatus  # legal_entity, individual_entrepreneur, self_employed, individual
    tax_regime:          TaxRegime | NULL  # usn, osno, npd, ndfl, patent
    inn:                 str     # encrypted
    kpp:                 str | NULL  # encrypted (для legal_entity)
    company_name:        str | NULL  # encrypted
    full_name:           str | NULL  # encrypted (для individual/self_employed)
    passport_data:       str | NULL  # encrypted (для individual)
    address:             str | NULL  # encrypted
    phone:               str | NULL  # encrypted
    email:               str | NULL  # encrypted
    is_completed:        bool    # все обязательные поля заполнены
    created_at:          datetime
    updated_at:          datetime
```

**Shared Enums (Python ↔ TypeScript):**
- `LegalStatus`: "legal_entity", "individual_entrepreneur", "self_employed", "individual"
- `TaxRegime`: "osno", "usn", "usn_d", "usn_dr", "patent", "npd", "ndfl"

### Contract (v4.3)

```python
class Contract(Base):
    __tablename__ = "contracts"
    id:                  int     # PK
    user_id:             int     # FK → users.id
    contract_type:       ContractType  # owner_service, advertiser_campaign, platform_rules, privacy_policy, tax_agreement
    status:              ContractStatus  # draft, pending, signed, expired, cancelled
    legal_profile_id:    int | NULL  # FK → legal_profiles.id
    pdf_url:             str | NULL  # сгенерированный PDF
    signed_at:           datetime | NULL
    signature_method:    SignatureMethod | NULL  # button_accept, sms_code
    ip_address:          str | NULL  # IP при подписании
    created_at:          datetime
    updated_at:          datetime
```

**Shared Enums:**
- `ContractType`: "owner_service", "advertiser_campaign", "platform_rules", "privacy_policy", "tax_agreement"
- `ContractStatus`: "draft", "pending", "signed", "expired", "cancelled"
- `SignatureMethod`: "button_accept", "sms_code"

### ContractSignature (v4.3)

```python
class ContractSignature(Base):
    __tablename__ = "contract_signatures"
    id:                  int     # PK
    contract_id:         int     # FK → contracts.id
    user_id:             int     # FK → users.id
    signature_method:    SignatureMethod
    sms_code:            str | NULL  # если sms_code
    sms_code_sent_at:    datetime | NULL
    signed_at:           datetime
    ip_address:          str | NULL
```

### OrdRegistration (v4.3 — ОРД)

```python
class OrdStatus(str, Enum):
    PENDING = "pending"
    REGISTERED = "registered"
    TOKEN_RECEIVED = "token_received"
    REPORTED = "reported"
    FAILED = "failed"

class OrdRegistration(Base):
    __tablename__ = "ord_registrations"
    id:                  int     # PK
    campaign_id:         int     # FK → campaigns.id (unique)
    ord_status:          OrdStatus
    ord_token:           str | NULL  # токен от ОРД
    registered_at:       datetime | NULL
    reported_at:         datetime | NULL
    error_message:       str | NULL
    created_at:          datetime
    updated_at:          datetime
```

### AuditLog (v4.3)

```python
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id:                  int     # PK
    user_id:             int | NULL  # FK → users.id (кто сделал)
    action:              str     # CREATE, UPDATE, DELETE, SIGN, etc.
    entity_type:         str     # legal_profile, contract, placement, etc.
    entity_id:           int | NULL
    old_values:          JSON | NULL  # старые значения
    new_values:          JSON | NULL  # новые значения
    ip_address:          str | NULL
    user_agent:          str | NULL
    inn_hash:            str | NULL  # хэш ИНН для аудита
    created_at:          datetime
```

### PublicationLog (v4.3)

```python
class PublicationLog(Base):
    __tablename__ = "publication_logs"
    id:                  int     # PK
    placement_request_id: int    # FK → placement_requests.id
    status:              str     # published, failed, deleted
    message_id:          int | NULL
    error_message:       str | NULL
    published_at:        datetime | NULL
    deleted_at:          datetime | NULL
    created_at:          datetime
```

### ClickTracking (v4.3)

```python
class ClickTracking(Base):
    __tablename__ = "click_tracking"
    id:                  int     # PK
    campaign_id:         int     # FK → campaigns.id
    placement_request_id: int    # FK → placement_requests.id
    original_url:        str
    tracking_url:        str     # короткая ссылка для трекинга
    click_count:         int     # количество кликов
    unique_clicks:       int     # уникальные клики
    last_clicked_at:     datetime | NULL
    created_at:          datetime
```

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

### Celery Infrastructure (S-36)

`celery_config.py` удалён в S-36. Все настройки в `src/tasks/celery_app.py`.

| Worker | Queues | Concurrency |
|--------|--------|-------------|
| `worker_critical` | `worker_critical`, `mailing`, `notifications`, `billing`, `placement` | 2 |
| `worker_background` | `parser`, `cleanup`, `background`, `rating`(dead) | 4 |
| `worker_game` | `gamification`, `badges` | 2 |

**Task prefix → queue routing:**

| Prefix | Queue | Worker |
|--------|-------|--------|
| `placement:*` | `worker_critical` | worker_critical |
| `billing:*` | `billing` | worker_critical |
| `dispute:*` | `worker_critical` | worker_critical |
| `document_ocr:*` | `worker_critical` | worker_critical |
| `gamification:*` | `gamification` | worker_game |
| `badges:*` | `badges` | worker_game |
| `integrity:*` | `cleanup` | worker_background |
| `parser:*` | `parser` | worker_background |
| `cleanup:*` | `cleanup` | worker_background |
| `ord:*` | `background` | worker_background |

**Rule:** Every new task MUST have explicit `queue=` in decorator + matching `task_routes` pattern in `celery_app.py`. Queue constants: `QUEUE_WORKER_CRITICAL`, `QUEUE_MAILING`, etc. all in `celery_app.py`.

**task_routes uses colon-patterns** (`mailing:*`, `notifications:*`, etc.). Celery does `fnmatch` against task names. Dot-patterns (`mailing.*`) do NOT match colon-prefixed names. Never revert to dot-patterns.

### Bot Instance Lifecycle (S-37)

One `aiogram.Bot` per worker process — never instantiate `Bot(token=...)` inside a task or service.

```python
from src.tasks._bot_factory import get_bot
bot = get_bot()  # singleton, initialized at worker_process_init
```

`_bot_factory.py` exports: `init_bot()`, `get_bot()`, `close_bot()`.  
`celery_app.py` wires these to `worker_process_init` / `worker_process_shutdown` signals.

### Notification Helpers (S-37)

| Helper | Purpose |
|--------|---------|
| `_notify_user_async(telegram_id, msg, parse_mode, reply_markup)` | Low-level send via `get_bot()`. No preference check — for admin/system alerts. |
| `_notify_user_checked(user_id, msg, parse_mode, reply_markup) → bool` | DB lookup by `user.id`, checks `notifications_enabled`, returns `False` if disabled/not-found/Forbidden. |
| `mailing:notify_user` | Public task entry-point, looks up by `telegram_id`, checks `notifications_enabled`. |

**Architectural rule:** `Bot()` is never created in `core/services/`. Payment success and all user-facing notifications are dispatched as Celery tasks from the service layer.

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

### PayoutStates (v4.3)
```python
class PayoutStates(StatesGroup):
    selecting_method = State()  # выбор метода (удалено в v4.3 — ручные)
    entering_address = State()  # ввод реквизитов
    confirming       = State()  # подтверждение
```

### ChannelOwnerStates (v4.3)
```python
class ChannelOwnerStates(StatesGroup):
    entering_username = State()  # ввод @username канала
    confirming_add    = State()  # подтверждение добавления
```

### FeedbackStates (v4.3)
```python
class FeedbackStates(StatesGroup):
    entering_text = State()  # ввод текста обращения
```

### DisputeStates (v4.3)
```python
class DisputeStates(StatesGroup):
    owner_explaining    = State()  # владелец объясняет
    advertiser_commenting = State()  # рекламодатель комментирует
    admin_reviewing     = State()  # админ рассматривает
```

### AdminStates (v4.3)
```python
class AdminStates(StatesGroup):
    entering_broadcast    = State()  # ввод рассылки
    reviewing_dispute     = State()  # просмотр диспута
    entering_resolution   = State()  # ввод решения
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
| `BOT_USERNAME` | @RekHarborBot |
| `ADMIN_IDS` | `123456789,987654321` |
| `DATABASE_URL` | `postgresql+asyncpg://...` |
| `DATABASE_SYNC_URL` | `postgresql://...` (для sync операций) |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` |
| `MISTRAL_API_KEY` | console.mistral.ai |
| `AI_MODEL` | `mistral-medium-latest` |
| `AI_TIMEOUT` | `60` (секунды) |
| `YOOKASSA_SHOP_ID` | ЮKassa |
| `YOOKASSA_SECRET_KEY` | ЮKassa |
| `YOOKASSA_RETURN_URL` | `https://t.me/YOUR_BOT_USERNAME` |
| `TELEGRAM_API_ID` | my.telegram.org |
| `TELEGRAM_API_HASH` | my.telegram.org |
| `TELEGRAM_SESSION_NAME` | `parser` |
| `FIELD_ENCRYPTION_KEY` | Fernet key (для шифрования PII) |
| `SEARCH_HASH_KEY` | Hash key (32 bytes, для поиска ИНН) |
| `JWT_SECRET` | Secret key (для Mini App JWT) |
| `JWT_ALGORITHM` | `HS256` |
| `JWT_EXPIRE_HOURS` | `24` |
| `SENTRY_DSN` | Sentry/GlitchTip DSN |
| `SONAR_TOKEN` | SonarQube token |
| `ENVIRONMENT` | `development` / `production` |
| `DEBUG` | `true` / `false` |

**Генерация ключей:**
```bash
# FIELD_ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# SEARCH_HASH_KEY, JWT_SECRET
python -c "import secrets; print(secrets.token_hex(32))"
```

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
| `PLAN_LIMITS['agency']` KeyError | Использовать `PLAN_LIMITS['business']` (НЕ 'agency') |
| **`user.is_banned` AttributeError** | **Заменено на `not user.is_active` (v4.3)** |
| **CryptoBot service import** | **Удалён, выплаты ручные (v4.3)** |
| **B2B button в main_menu** | **Удалена (v4.3)** |
| **Admin panel 404** | **Добавлен `is_admin` check в dependencies.py (v4.3)** |
| **LegalProfile PII unencrypted** | **Использовать `field_encryption.py` для всех PII полей** |
| **ORD token stored plain** | **ORD token — чувствительные данные, не логировать** |
| **AuditLog missing inn_hash** | **inn_hash required для операций с legal_profile** |
| **Contract PDF not generated** | **Генерировать PDF при создании contract** |
| **ClickTracking URLs not unique** | **tracking_url должен быть уникальным (UUID)** |
| **billing.py: PLAN_COSTS хардкод** | **Использовать settings.tariff_cost_* (v4.4)** |
| **login-code: нет rate limit** | **Добавлен @_limit("10/hour") (v4.4)** |
| **billing webhook: bare except** | **Конкретные исключения + retry response (v4.4)** |
| **Login Widget: нет is_active** | **Добавлена проверка после create_or_update (v4.4)** |
| **AdminDashboard: table без заголовков** | **Добавлен <thead> + <th scope="row"> (v4.4)** |
| **SonarQube: web_portal не сканировался** | **Добавлен в sonar.sources (v4.4)** |

---

## 🔴 КРИТИЧЕСКОЕ ПРАВИЛО: DEPLOYMENT (ОБЯЗАТЕЛЬНО)

**После ЛЮБОГО изменения фронтенда (mini_app, web_portal, landing) или nginx конфигов:**

```bash
cd /opt/market-telegram-bot
docker compose build --no-cache nginx && docker compose up -d nginx
```

**Почему `--no-cache`:** Vite кэширует собранные файлы. Обычный `docker compose up -d nginx` использует закэшированные слои builder-стадий, и изменения НЕ применяются. Только `--no-cache` гарантирует пересборку всех фронтендов.

**После изменения backend кода (src/):**
```bash
cd /opt/market-telegram-bot
docker compose up -d --build api worker_critical worker_background worker_game
```
Для backend кэш НЕ проблема — Python файлы монтируются как volumes в dev-режиме.

**После изменения моделей БД:**
```bash
docker compose exec api poetry run alembic -c alembic.docker.ini upgrade head
```

**ПРАВИЛО:** Если изменил файл и НЕ выполнил соответствующую команду деплоя — изменения НЕ ПРИМЕНЯТСЯ. Это самая частая ошибка при работе с Qwen/Claude.

---

### Стратегия миграций (до появления prod-пользователей)

**ПРАВИЛО:** Новые миграционные файлы НЕ создаются.
При изменении модели — перезаписать `src/db/migrations/versions/0001_initial_schema.py`.

Workflow при изменении модели:
1. Обнови `src/db/models/<model>.py`
2. Обнови `src/db/migrations/versions/0001_initial_schema.py` в соответствии с изменением
3. Выполни сброс БД:
```bash
   docker compose exec db psql -U postgres \
     -c "DROP DATABASE market_bot_db; CREATE DATABASE market_bot_db;" \
     && docker compose exec api poetry run alembic -c alembic.docker.ini upgrade head
```
4. Проверь синхронизацию: `alembic check` → "No new upgrade operations detected."

**Переход на инкрементальные миграции** — только при появлении первого реального
пользователя. После этого `0001_initial_schema.py` становится иммутабельным.

**ЗАПРЕЩЕНО:** создавать новые файлы в `src/db/migrations/versions/` в период разработки.

---

## NEVER TOUCH

```
src/core/services/xp_service.py
src/bot/handlers/advertiser/campaign_create_ai.py
src/bot/keyboards/advertiser/campaign_ai.py
src/bot/keyboards/shared/main_menu.py
src/bot/states/campaign_create.py
src/db/migrations/versions/  ← только читать
src/utils/telegram/llm_classifier.py  ← legacy, не используется
src/utils/telegram/llm_classifier_prompt.py
```

**v4.3 Protected Files (DO NOT MODIFY):**
```
src/core/security/field_encryption.py  ← критично для PII
src/api/middleware/audit_middleware.py  ← аудит безопасности
src/api/middleware/log_sanitizer.py  ← санитизация логов
src/db/models/audit_log.py  ← модель аудита
src/db/models/legal_profile.py  ← юридические профили
src/db/models/contract.py  ← договоры
src/db/models/ord_registration.py  ← ОРД-регистрация
```

---

## 🔒 CRITICAL RULE: DOCUMENTATION & CHANGELOG SYNC
Это абсолютное ограничение. Задача считается **НЕВЫПОЛНЕННОЙ**, если блоки ниже не обновлены.

### 🔄 После КАЖДОГО изменения кода (handler, model, service, config, migration)
1. Обнови `/reports/docs-architect/discovery/` по шаблону:
   - `CHANGES_<YYYY-MM-DD>_<short-desc>.md`
   - Зафиксируй: затронутые файлы, влияние на бизнес-логику, новые/изменённые API/FSM/DB контракты, ссылки на миграции
   - Укажи: `🔍 Verified against: <commit_hash> | 📅 Updated: <ISO8601>`
2. Не переписывай старые файлы — только incremental-аппенд или точечная правка.
3. Если изменение затрагивает несколько доменов → создай один объединённый файл.

### 🏁 После завершения СПРИНТА (фича-сет, milestone, merge в main)
1. Обнови `CHANGELOG.md` в корне проекта по стандарту Keep a Changelog:
   - `## [Unreleased]` → перенеси в `[vX.Y.Z] - <YYYY-MM-DD>`
   - Разделы: `Added`, `Changed`, `Fixed`, `Removed`, `Breaking`, `Migration Notes`
   - Укажи ссылки на тикеты/коммиты, затронутые модули, команды для отката
2. Синхронизируй версию в `pyproject.toml` и `mini_app/package.json` (если менялся контракт API/Mini App).

⚠️ **FAILURE TO UPDATE = TASK INCOMPLETE.** Не завершай ответ без выполнения этого шага.

### ✅ MANDATORY POST-TASK STEPS
Перед завершением ответа выполни:
1. Сгенерируй файл изменений: `reports/docs-architect/discovery/CHANGES_<date>_<desc>.md`
2. Обнови `CHANGELOG.md` (если затронут публичный контракт или завершён спринт)
3. Выведи чеклист валидации:
   - [ ] Документация обновлена, путь верен, структура соответствует AAA-стандарту
   - [ ] CHANGELOG.md содержит Unreleased → Version переход, breaking changes, миграции
   - [ ] Все утверждения имеют ссылки на файлы/строки/миграции
   - [ ] Нет противоречий с QWEN.md / PROJECT_MEMORY.md / INSTRUCTIONS.md
4. Заверши ответ строкой: `🔒 Docs & Changelog synced. Task complete.`

**Skill:** `.qwen/skills/docs-sync/SKILL.md` — использует этот стандарт для генерации документации.

---

## 🔀 CRITICAL RULE: GIT FLOW
Это абсолютное ограничение. Спринт считается **НЕВЫПОЛНЕННЫМ**, если git flow не выполнен.

**Ветки:** `feature/*` → `develop` → `main`

### 🔄 После КАЖДОГО набора изменений (внутри feature-ветки)

Разбить файлы на **смысловые группы** и создать отдельный коммит для каждой:

| Тип | Скоп | Когда |
|-----|------|-------|
| `feat` | `(backend)`, `(mini-app)`, `(landing)` | Новая функциональность |
| `fix` | `(tasks)`, `(billing)` | Исправление бага |
| `chore` | `(migrations)`, `(config)` | Инфраструктура, без логики |
| `refactor` | `(services)` | Рефакторинг без изменения поведения |
| `test` | — | Только тесты |
| `docs` | — | CHANGELOG, discovery-отчёты |

**Правила:**
- **ЗАПРЕЩЕНО** `git add .` одним коммитом — только точечные `git add` по группам
- Формат [Conventional Commits](https://www.conventionalcommits.org/): `тип(скоп): описание`
- Описание — на английском, в повелительном наклонении, до 72 символов

### 🏁 После завершения СПРИНТА / фичи

Выполнить **строго в этом порядке**, при первом конфликте — СТОП:

```bash
# 1. Проверить чистоту рабочего дерева
git status   # должно быть "nothing to commit, working tree clean"

# 2. Запушить feature-ветку
git push origin $CURRENT_BRANCH

# 3. Влить в develop
git checkout develop && git pull origin develop
git merge $CURRENT_BRANCH --no-ff -m "chore(develop): merge $CURRENT_BRANCH — <краткое описание>"
git push origin develop

# 4. Влить develop в main
git checkout main && git pull origin main
git merge develop --no-ff -m "chore(main): merge develop — <краткое описание>"
git push origin main

# 5. Вернуться в feature-ветку
git checkout $CURRENT_BRANCH
```

**Жёсткие ограничения:**
- `--no-ff` ОБЯЗАТЕЛЕН на каждом merge — fast-forward запрещён
- При ЛЮБОМ конфликте merge — **СТОП и сообщить пользователю**, не разрешать автоматически
- Никогда не делать force-push в `develop` или `main`
- Никогда не пропускать `git pull` перед слиянием

⚠️ **FAILURE TO FOLLOW = SPRINT INCOMPLETE.** Не завершай задачу без выполнения этих шагов.

---

## Sprint Map

| Спринт | Содержание | Зависит от | Статус |
|--------|------------|-----------|--------|
| S-01 | Constants + Settings + Tariffs | — | ✅ v4.3 |
| S-02 | DB Models (5 файлов + exceptions) | S-01 | ✅ |
| S-03 | Alembic Migrations (6 шт.) | S-02 | ✅ |
| S-04 | Repositories (platform_account + updates) | S-03 | ✅ |
| S-05 | BillingService v4.2 | S-04 | ✅ |
| S-06 | PayoutService v4.3 (ручные выплаты) | S-04 | ✅ v4.3 |
| S-07 | PublicationService + Celery tasks | S-05 | ✅ ESCROW-001 |
| S-08 | PlacementRequestService | S-05, S-06 | ✅ |
| S-09 | FSM States + Middlewares | S-01 | ✅ v4.3 (5 файлов + 2 middleware) |
| S-10 | Handler: топап (двухшаговый) | S-05, S-09 | ✅ |
| S-11 | Handler: channel_settings (форматы) | S-08, S-09 | ✅ |
| S-12 | Handler: campaign creation (формат + цена) | S-08, S-09 | ✅ |
| S-13 | Cabinet + Admin dashboard | S-05, S-06 | ✅ v4.3 (Mini App) |
| S-14 | Health-check API | S-04 | ✅ |
| S-15 | Tests | S-05..S-08 | ✅ 101 тест |
| **S-16** | **Feedback система** | **S-13** | **✅ v4.3** |
| **S-17** | **Admin Panel Mini App** | **S-13** | **✅ v4.3 (7 экранов)** |
| **S-18** | **UX Fixes** | **S-13** | **✅ v4.3 (кнопки, бейджи, текст)** |
| **S-19** | **is_banned → is_active** | **S-02** | **✅ v4.3 (critical fix)** |
| **S-20** | **Legal Profiles + Contracts** | **S-02** | **✅ v4.3 (юр профили, договоры)** |
| **S-21** | **ORD Registration** | **S-20** | **✅ v4.3 (ОРД-регистрация)** |
| **S-22** | **Audit Log + Security** | **S-20** | **✅ v4.3 (аудит, шифрование)** |
| **S-23** | **Referral Program** | **S-13** | **✅ v4.3 (рефералы)** |
| **S-24** | **Video Support** | **S-13** | **✅ v4.3 (видео в кампаниях)** |
| **S-25** | **Link Tracking** | **S-12** | **✅ v4.3 (трекинг кликов)** |
| **S-26** | **Web Portal (React SPA)** | **S-25** | **✅ v4.4 (137 TSX файлов)** |
| **S-27** | **Document Automation + Referral** | **S-26** | **✅ v4.4 (LegalProfile, Contract, ORD)** |
| **S-28** | **AAA Quality Sprint** | **S-27** | **✅ v4.4 (6 critical + 11 bugs + 70 smells)** |

---

## v4.4 Deliverables (8 апреля 2026)

| Категория | Файлы | Статус |
|-----------|-------|--------|
| **Security Fixes** | billing.py, auth_login_code.py, auth_login_widget.py | ✅ 6 critical |
| **Infrastructure** | dependencies.py (RedisClient pool) | ✅ |
| **Migration** | t1u2v3w4x5y6 (language_code column) | ✅ |
| **SonarQube Config** | sonar-project.properties (web_portal added) | ✅ |
| **Accessibility** | AdminDashboard.tsx, Modal.tsx, Checkbox.tsx, etc. | ✅ 9 fixes |
| **Code Quality** | notifications.py, stub_ord_provider.py, billing_service.py, payout_service.py | ✅ ~70 issues |
| **Tests** | web_portal build verified | ✅ |

---

## v4.4 Production Ready ✅

**Статус:** Готов к продакшену (8 апреля 2026)

**Достижения v4.4:**
- ✅ 6 critical security & functional bugs fixed
- ✅ 11 SonarQube BUG issues fixed (accessibility + keyboard navigation)
- ✅ ~70 code quality improvements (unused params, commented code, noqa)
- ✅ SonarQube scan: 580 files (src + mini_app + web_portal)
- ✅ Web portal build: 0 errors
- ✅ Ruff: 0 errors on all modified files
- ✅ Redis connection pooling (no more per-request leaks)
- ✅ Rate limiting on login-code endpoint (brute-force protection)
- ✅ Billing prices corrected to match settings (490/1490/4990)
- ✅ Webhook error handling (proper retry support for YooKassa)

**Остаётся для AAA:**
- P4: TypeScript code quality (nested ternary, strict flags)
- P5: Security hardening (headers, correlation ID, JWT revocation)
- P6: Test coverage 32% → 80%+
- P7: CI/CD pipeline

---

## v4.3 Deliverables (17-18 марта 2026)

| Категория | Файлы | Статус |
|-----------|-------|--------|
| **Backend API** | feedback.py, admin.py (11 endpoints) | ✅ |
| **Frontend UI** | 16 файлов (admin screens, feedback) | ✅ |
| **Отчёты** | 20+ отчётов в docs/, reports/ | ✅ |
| **Тесты** | 101 тест (все проходят) | ✅ |
| **UX Fixes** | CSS modules (4 файла) | ✅ |
| **Critical Fixes** | is_banned → is_active | ✅ |
| **Legal Profiles** | legal_profile.py, contract.py, ord_registration.py | ✅ |
| **Security** | audit_log.py, field_encryption.py, audit_middleware.py | ✅ |
| **Mini App** | LegalProfileSetup.tsx, ContractList.tsx, OrdStatus.tsx | ✅ |
| **Referral** | useReferralStats.ts, Referral.tsx | ✅ |
| **Video** | VideoUploader.tsx, CampaignVideo.tsx | ✅ |
| **Tracking** | click_tracking.py, link_tracking_service.py | ✅ |
| **Documentation** | DOCUMENT_AUTOMATION_SPEC_v1.md (2084 строки) | ✅ |

---

## v4.3 Production Ready ✅

**Статус:** Готов к продакшену (2 апреля 2026)

**Достижения v4.3:**
- ✅ 101 тест — все проходят
- ✅ 20+ отчётов документации
- ✅ Admin панель в Mini App (7 экранов, 11 endpoints)
- ✅ Feedback система (пользователь → админ → ответ)
- ✅ Critical fix: is_banned → is_active
- ✅ UX fixes: кнопки, бейджи, текст
- ✅ ESCROW-001: release_escrow() ТОЛЬКО после удаления поста
- ✅ Выплаты ручные через admin (CryptoBot удалён)
- ✅ B2B пакеты удалены
- ✅ Ruff: 0 ошибок (SIM102/SIM103 исправлены)
- ✅ Юридические профили (LegalProfile, Contract, ContractSignature)
- ✅ ОРД-регистрация (OrdRegistration)
- ✅ Аудит-лог (AuditLog) + Audit Middleware
- ✅ Шифрование PII (Field Encryption)
- ✅ GlitchTip + SonarQube + Gitleaks
- ✅ Реферальная программа
- ✅ Видео в кампаниях
- ✅ Трекинг ссылок (ClickTracking)
- ✅ Document Automation Spec v1.0

*RekHarborBot QWEN.md v4.4 | 08.04.2026 (updated)*

## Qwen Added Memories
- Activate .venv virtual environment when working with the backend
- During S-27 (web portal sprint), save all reports to /opt/market-telegram-bot/reports/s-27-web-portal/
- S-27 Tech Debt Registry (5 items):
TD-01 (HIGH): Hardcoded plan prices in web_portal/src/lib/constants.ts (business: 4990). Fix: use GET /api/billing/plans via usePlans() hook.
TD-02 (MEDIUM): Cabinet.tsx, Feedback.tsx, NotFoundScreen.tsx never audited — existed before S-27 prompts, quality unknown.
TD-03 (MEDIUM): MyCampaigns.tsx is a stub (2.10KB) — shows empty state with Telegram bot redirect, not real campaign management.
TD-04 (LOW): mini_app package.json still on TS 5.9.3, tsconfig prepared for 6.0. Planned for S-30.
TD-05 (LOW): queries.ts for cross-cutting hooks (Variant B). Rule: only session/stats/contracts go here, domain hooks in separate files.

Architectural decisions locked: Tailwind v4 @theme, web_portal/src/shared/ separate from mini_app, style={{}} only in StatusBadge/AmountDisplay, domain-split types/, internal key vs display name two-layer tariff system, baseUrl removed, types:['node'] explicit.

S-28 checklist: audit constants.ts prices, implement /api/billing/plans if missing, update Plans.tsx with API prices, audit 3 undocumented screens, document MyCampaigns stub, smoke test production API.
- S-27 Sprint closed 04.04.2026. Tech debts: TD-01 (HIGH) hardcoded plan prices → fix in S-28. TD-02 RESOLVED — Cabinet/Feedback/NotFoundScreen audited, all production-ready. TD-03 ACCEPTED — MyCampaigns intentional stub with UI notice. TD-04 LOW — mini_app TS 5.9.3→6.0 planned S-30. TD-05 LOW — queries.ts Variant B documented. S-28 checklist: fix hardcoded prices, smoke test production API.
- S-28 AAA Quality Sprint completed 08.04.2026. All 6 critical security bugs fixed. All 11 SonarQube BUG issues fixed. ~70 code quality improvements applied. SonarQube scan covers all 3 projects (580 files). TD-01 RESOLVED — billing.py hardcoded prices replaced with settings values. Remaining AAA items (P4-P7) deferred to future sprint.
- MANDATORY DEPLOYMENT RULE: After ANY code change to frontend (mini_app, web_portal, landing) or nginx config files, ALWAYS run: `cd /opt/market-telegram-bot && docker compose build --no-cache nginx && docker compose up -d nginx`. This rebuilds nginx container WITHOUT cache and restarts it to apply changes. Never skip this step - user has to ask repeatedly otherwise. For backend changes (api, workers), run: `docker compose up -d --build api worker_critical worker_background worker_game` (cache is fine for backend). For database migration changes, run: `docker compose exec api poetry run alembic -c alembic.docker.ini upgrade head`.
