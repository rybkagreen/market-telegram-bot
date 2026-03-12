# RekHarborBot — Эталонный документ проекта v4.2

**Дата:** 12.03.2026
**Назначение:** основа для промптов Qwen Code и архитектурных решений
**Заменяет:** FINANCIAL_MODEL_REFERENCE_v4.1.md

---

## CHANGELOG v4.1 → v4.2

| Пункт | Решение |
|-------|---------|
| П-01 | P&L: ЮKassa комиссия разделена на две строки (пользователь vs платформа) |
| П-02 | Налоги владельцев: Вариант A (сами декларируют) + UI-подсказка + post-MVP флаг |
| П-03 | НПД → УСН 6%: `NPD_TAX_RATE` удалён, добавлен `PLATFORM_TAX_RATE = 0.06` |
| П-04 | Комиссия за вывод: `PAYOUT_FEE_RATE = 0.015`, новые поля PayoutRequest |
| П-05 | Маркетинг в P&L: 15 000 ₽/мес старт, 30 000 ₽/мес рост |
| П-06 | Velocity check в MVP: `VELOCITY_MAX_RATIO = 0.80`, окно 30 дней |

---

## РАЗДЕЛ 0 — КЛЮЧЕВЫЕ РЕШЕНИЯ (единый источник правды)

| Параметр | Значение | Примечание |
|---|---|---|
| Бонусные кредиты | ❌ Нет | Отложено на post-MVP |
| Способ оплаты | ЮKassa (карта / СБП) | Stars исключены |
| ЮKassa комиссия с пополнений | 3.5% поверх — платит пользователь | Не расход платформы |
| ЮKassa комиссия с подписок | 3.5% — платит платформа | ~2 170 ₽/мес при базовом сценарии |
| Минимальное пополнение | 500 ₽ (желаемая сумма на баланс) | |
| Максимальное пополнение | 300 000 ₽ | Лимит ЮKassa для самозанятых |
| Пополнение | Произвольная сумма | Быстрые кнопки [500, 1000, 2000, 5000, 10000, 20000] + ввод |
| Курс пополнения | 1 ₽ = 1 кредит, без надбавок | |
| Минимальная цена поста | 1 000 ₽ | Устанавливает владелец |
| Минимальный бюджет кампании | 2 000 ₽ | Системное ограничение |
| Комиссия платформы | 15% | Владелец получает 85% |
| Комиссия за вывод | 1.5% от суммы вывода | Покрывает банковский перевод |
| Минимальная выплата владельцу | 1 000 ₽ | Вручную администратором |
| Налог платформы | 6% (УСН) | НПД не применяется — превышение 2.4 млн/год |
| Налог владельцев | Вариант A — декларируют сами | UI-подсказка в кабинете; Вариант B post-MVP |
| Self-dealing | Запрещено на уровне сервиса | Нельзя размещать на своём канале |
| Velocity check | 80% от пополнений за 30 дней | Блокировка на ревью при превышении |
| Форматы публикации | 5 форматов | post_24h/48h/7d + pin_24h/48h |
| Целевой сегмент | Каналы 1K–50K подписчиков | MVP |

---

## РАЗДЕЛ 1 — АРХИТЕКТУРА СЧЕТОВ

### 1.1 Четыре логических пула

```
┌─────────────────────────────────────────────────────────────┐
│  БАНКОВСКИЙ СЧЁТ ПЛАТФОРМЫ (ЮKassa)                         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ USER_POOL   │  │ ESCROW_POOL │  │ PROFIT_POOL │         │
│  │ balance_rub │  │ Заморожено  │  │ 15% комиссия│         │
│  │ всех рекл.  │  │ под активные│  │ с закрытых  │         │
│  └─────────────┘  │ размещения  │  │ сделок      │         │
│                   └─────────────┘  └─────────────┘         │
│  ┌─────────────┐                                           │
│  │ PAYOUT_POOL │                                           │
│  │ earned_rub  │                                           │
│  │ всех влад.  │                                           │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Поля модели User

```python
balance_rub: Decimal  # Баланс рекламодателя — пополняется ЮKassa, расходуется на эскроу
earned_rub:  Decimal  # Баланс владельца — источник 85% released эскроу, расходуется на вывод
credits:     int      # Только для тарифных подписок, НЕ для размещений
```

### 1.3 Модель PayoutRequest — обновлённая (v4.2)

```python
class PayoutRequest(Base):
    # Существующие поля (не трогать)
    user_id:     int
    status:      str  # pending / processing / paid / rejected

    # Новые поля v4.2
    gross_amount: Decimal  # Запрошено владельцем (то что списывается с earned_rub)
    fee_amount:   Decimal  # 1.5% комиссия платформы за вывод
    net_amount:   Decimal  # Фактически перечисляется (gross - fee)
    tax_withheld: Decimal  # NULL в MVP (Вариант A); заполняется в post-MVP (Вариант B)
```

**Механика вывода:**
```
Владелец запрашивает:  10 000 ₽  → gross_amount
Комиссия 1.5%:           -150 ₽  → fee_amount
Перечисляется:          9 850 ₽  → net_amount
Уведомление в UI:       "Будет перечислено: 9 850 ₽ (комиссия платформы 1.5%)"
```

### 1.4 Модель PlatformAccount (singleton id=1)

```python
class PlatformAccount(Base):
    id:                  int = 1
    escrow_reserved:     Decimal  # = SUM(placements WHERE status='escrow')
    payout_reserved:     Decimal  # = SUM(payouts WHERE pending/processing)
    profit_accumulated:  Decimal  # = SUM(15% released эскроу + 1.5% payout fees)
    total_topups:        Decimal  # исторические пополнения (desired_balance)
    total_payouts:       Decimal  # исторические выплаты (net_amount)
    updated_at:          datetime
```

### 1.5 Инварианты балансов (health-check)

```python
assert SUM(users.balance_rub) <= real_bank_balance
assert platform.escrow_reserved == SUM(placements.final_price WHERE status='escrow')
assert platform.payout_reserved == SUM(payouts.gross_amount WHERE status IN ('pending','processing'))
assert SUM(users.earned_rub) <= (real_bank_balance - platform.escrow_reserved - platform.profit_accumulated)
```

---

## РАЗДЕЛ 2 — ПОПОЛНЕНИЕ БАЛАНСА

### 2.1 Принцип расчёта

Пользователь указывает желаемую сумму → платформа добавляет 3.5%:

```
Желаю на баланс:      10 000 ₽
Комиссия ЮKassa 3.5%:   +350 ₽
──────────────────────────────
Итого к оплате:       10 350 ₽
Зачисляется ровно:    10 000 ₽
```

### 2.2 UX — быстрые кнопки + ручной ввод

```
[500 ₽] [1 000 ₽] [2 000 ₽] [5 000 ₽] [10 000 ₽] [20 000 ₽]
Или введите сумму (мин. 500 ₽):
```

### 2.3 Реализация

```python
YOOKASSA_FEE_RATE = Decimal("0.035")
MIN_TOPUP         = Decimal("500")
MAX_TOPUP         = Decimal("300000")
QUICK_TOPUP_AMOUNTS: list[int] = [500, 1000, 2000, 5000, 10000, 20000]

def calculate_topup_payment(desired_balance: Decimal) -> dict:
    fee_amount   = (desired_balance * YOOKASSA_FEE_RATE).quantize(Decimal("0.01"))
    gross_amount = desired_balance + fee_amount
    return {
        "desired_balance": desired_balance,
        "fee_amount":      fee_amount,
        "gross_amount":    gross_amount,
    }

async def process_topup_webhook(session, payment_id, gross_amount, metadata):
    # Зачисляем DESIRED_BALANCE — не gross_amount!
    desired_balance = Decimal(metadata["desired_balance"])
    user.balance_rub += desired_balance
```

### 2.4 FSM состояния

```python
class TopupStates(StatesGroup):
    entering_amount  = State()  # ввод желаемой суммы
    confirming       = State()  # показ расчёта + подтверждение
    waiting_payment  = State()  # ожидание вебхука
```

---

## РАЗДЕЛ 3 — ФОРМАТЫ ПУБЛИКАЦИИ

### 3.1 Пять форматов

| Формат | Действия | Множитель | Длительность |
|--------|----------|-----------|--------------|
| `post_24h` | Публикует, удаляет через 24 ч | ×1.0 (базовый) | 86 400 сек |
| `post_48h` | Публикует, удаляет через 48 ч | ×1.4 | 172 800 сек |
| `post_7d` | Публикует, удаляет через 7 дней | ×2.0 | 604 800 сек |
| `pin_24h` | Публикует + закрепляет, открепляет и удаляет через 24 ч | ×3.0 | 86 400 сек |
| `pin_48h` | Публикует + закрепляет, открепляет и удаляет через 48 ч | ×4.0 | 172 800 сек |

```python
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
```

### 3.2 Доступность по тарифам

```python
PLAN_LIMITS: dict[str, dict] = {
    "free":    {"active_campaigns": 1,  "ai_per_month": 0,  "formats": ["post_24h"]},
    "starter": {"active_campaigns": 5,  "ai_per_month": 3,  "formats": ["post_24h","post_48h"]},
    "pro":     {"active_campaigns": 20, "ai_per_month": 20, "formats": ["post_24h","post_48h","post_7d"]},
    "agency":  {"active_campaigns": -1, "ai_per_month": -1, "formats": ["post_24h","post_48h","post_7d","pin_24h","pin_48h"]},
}
```

### 3.3 Права бота в канале

| Право | Форматы | Обязательность |
|-------|---------|----------------|
| `post_messages` | все | уже есть |
| `delete_messages` | все | новое — обязательное |
| `pin_messages` | pin_24h, pin_48h | для закрепов |

---

## РАЗДЕЛ 4 — ЖИЗНЕННЫЙ ЦИКЛ ДЕНЕГ

### 4.1 Пополнение

```
desired=10 000 → gross=10 350 → ЮKassa удерживает 350 → на счёт платформы 10 000
user.balance_rub += 10 000
platform.total_topups += 10 000
Transaction(TOPUP, 10 000)
```

### 4.2 Создание размещения → Эскроу

```
final_price = price_per_post × FORMAT_MULTIPLIERS[format]
Проверки:
  ✅ final_price >= MIN_CAMPAIGN_BUDGET (2 000)
  ✅ user.balance_rub >= final_price
  ✅ format в PLAN_LIMITS[user.plan]["formats"]
  ✅ channel.owner_id != user.id  (self-dealing!)

user.balance_rub          -= final_price
platform.escrow_reserved  += final_price
Transaction(ESCROW_FREEZE, final_price)
```

### 4.3 Успешная публикация → Разблокировка

```
owner_amount  = final_price × 0.85
platform_fee  = final_price × 0.15

owner.earned_rub            += owner_amount
platform.escrow_reserved    -= final_price
platform.profit_accumulated += platform_fee

Transaction(ESCROW_RELEASE, owner_amount, owner_id)
Transaction(PLATFORM_FEE,   platform_fee)
```

### 4.4 Выплата владельцу (v4.2 — с комиссией)

```
Владелец запрашивает gross_amount (мин. 1 000 ₽)
Проверки:
  ✅ owner.earned_rub >= gross_amount
  ✅ нет активного PayoutRequest
  ✅ velocity check: (payouts_30d + gross_amount) / topups_30d <= 0.80

fee_amount  = (gross_amount × 0.015).quantize(0.01)
net_amount  = gross_amount - fee_amount

owner.earned_rub          -= gross_amount
platform.payout_reserved  += gross_amount
platform.profit_accumulated += fee_amount  ← комиссия сразу в прибыль

PayoutRequest(gross=gross_amount, fee=fee_amount, net=net_amount)
→ Администратор переводит net_amount вручную
→ platform.payout_reserved  -= gross_amount
→ platform.total_payouts    += net_amount
```

### 4.5 Отмена / Возврат

| Сценарий | Рекламодатель | Владелец | Платформа | Δ Реп. рекл. |
|---|---|---|---|---|
| Отмена до эскроу | +100% | 0 | 0 | 0 |
| Отмена после эскроу, до подтв. | +100% | 0 | 0 | −5 |
| Отмена после подтв. владельцем | +50% | +42.5% | +7.5% | −20 |
| Владелец отклонил | +100% | 0 | 0 | 0 |
| Техническая ошибка | +100% | 0 | 0 | 0 |

---

## РАЗДЕЛ 5 — ТАРИФНАЯ МОДЕЛЬ

### 5.1 Тарифы

| Тариф | Цена/мес | Enum code | Кампании | AI/мес | Форматы |
|-------|----------|-----------|----------|--------|---------|
| Free | 0 ₽ | `free` | 1 | ❌ | post_24h |
| Starter | 490 ₽ | `starter` | 5 | 3 | + post_48h |
| Pro | 1 490 ₽ | `pro` | 20 | 20 | + post_7d |
| Agency | 4 990 ₽ | `business` ⚠️ | Безлим | Безлим | Все 5 |

⚠️ Тариф "Agency" в `UserPlan` enum называется `business`. `PLAN_DISPLAY_NAMES["business"] = "Agency"`.

```python
PLAN_PRICES: dict[str, Decimal] = {
    "free":    Decimal("0"),
    "starter": Decimal("490"),
    "pro":     Decimal("1490"),
    "agency":  Decimal("4990"),
}
```

### 5.2 Конкурентное позиционирование

| Платформа | Комиссия | Доля владельца | Авто-удаление | Закреп |
|-----------|----------|----------------|---------------|--------|
| Telega.in | ~30% | 70% | ❌ | ❌ |
| Epicstars | ~25–35% | 75% | ❌ | ❌ |
| **RekHarborBot** | **15%** | **85%** | **✅** | **✅** |

---

## РАЗДЕЛ 6 — ФИНАНСОВАЯ МОДЕЛЬ (P&L пересчитан)

### 6.1 Константы v4.2

```python
PLATFORM_COMMISSION   = Decimal("0.15")   # 15% с размещений
OWNER_SHARE           = Decimal("0.85")   # 85% владельцу
YOOKASSA_FEE_RATE     = Decimal("0.035")  # платит пользователь поверх пополнения
PLATFORM_TAX_RATE     = Decimal("0.06")   # УСН 6% (выручка > 2.4 млн/год → не НПД)
PAYOUT_FEE_RATE       = Decimal("0.015")  # комиссия платформы за вывод
VELOCITY_WINDOW_DAYS  = 30
VELOCITY_MAX_RATIO    = Decimal("0.80")   # макс. вывод / пополнения за 30 дней
COOLDOWN_HOURS        = 24               # пополнение→размещение→вывод в течение 24ч
MIN_TOPUP             = Decimal("500")
MAX_TOPUP             = Decimal("300000")
MIN_CAMPAIGN_BUDGET   = Decimal("2000")
MIN_PRICE_PER_POST    = Decimal("1000")
MIN_PAYOUT            = Decimal("1000")
QUICK_TOPUP_AMOUNTS: list[int] = [500, 1000, 2000, 5000, 10000, 20000]
```

### 6.2 P&L (100 рекламодателей, 20 каналов) — v4.2

**Допущения:**
50 Free / 30 Starter / 15 Pro / 5 Agency.
Средний чек: Free 2K, Starter 4K, Pro 7K, Agency 12K.
Кампаний в месяц: Free 1, Starter 3, Pro 5, Agency 15.

```
ДОХОДЫ
────────────────────────────────────────────────────────
Тарифные подписки:
  Starter (30 × 490):                  14 700 ₽
  Pro     (15 × 1 490):                22 350 ₽
  Agency  ( 5 × 4 990):                24 950 ₽
  ───────────────────────────────────────────────
  Итого подписки:                      62 000 ₽

Оборот размещений:
  Free    (50 × 1  × 2 000):          100 000 ₽
  Starter (30 × 3  × 4 000):          360 000 ₽
  Pro     (15 × 5  × 7 000):          525 000 ₽
  Agency  ( 5 × 15 × 12 000):         900 000 ₽
  ───────────────────────────────────────────────
  Итого оборот:                      1 885 000 ₽
  Комиссия платформы (15%):            282 750 ₽

Комиссия за выводы (1.5%):
  Предположим 50% владельцев выводят в месяц
  Средний вывод ~8 000 ₽ × 10 владельцев × 1.5%:  1 200 ₽

  Итого валовая выручка:               345 950 ₽

ПЕРЕМЕННЫЕ ЗАТРАТЫ
────────────────────────────────────────────────────────
ЮKassa с подписок (62 000 × 3.5%):     -2 170 ₽
  Пояснение: комиссия с пополнений — за счёт пользователей (не расход платформы)

УСН 6% от валовой выручки:
  (345 950 × 6%):                      -20 757 ₽

  Итого переменные:                    -22 927 ₽

ФИКСИРОВАННЫЕ ЗАТРАТЫ
────────────────────────────────────────────────────────
  Сервер:                               -2 000 ₽
  Домен + SSL (3 500 ÷ 12):               -292 ₽
  Mistral API (оценка):                   -500 ₽
  Маркетинг (старт мес 1–3):           -15 000 ₽
  ───────────────────────────────────────────────
  Итого фиксированные (старт):         -17 792 ₽

══════════════════════════════════════════════════════════
ЧИСТАЯ ПРИБЫЛЬ (старт):                305 231 ₽/мес
Маржинальность:                             88.2%
══════════════════════════════════════════════════════════

При маркетинге 30 000 ₽ (фаза роста):
  Фиксированные:                       -32 792 ₽
  Чистая прибыль (рост):               290 231 ₽/мес
  Маржинальность:                           83.9%

Распределение оборота размещений:
  Владельцам каналов (85%):          1 602 250 ₽
  Платформе (15%):                     282 750 ₽
```

### 6.3 Breakeven

```
Фаза старт (маркетинг 15 000 ₽):
  Фиксированные: 17 792 ₽
  Переменная маржа: ~94%
  Breakeven ≈ 18 950 ₽ выручки
            = ~39 подписок Starter
            = ~11 кампаний Agency (12 000 × 15% = 1 800 ₽)

Без маркетинга:
  Breakeven ≈ 2 980 ₽ (как в v4.1)
```

### 6.4 Влияние форматов на средний чек

| Микс форматов | Средний чек | Рост оборота |
|---|---|---|
| 100% post_24h | 4 000 ₽ | базовый |
| + 15% post_48h (×1.4) | 4 240 ₽ | +6% |
| + 5% pin_24h (×3.0) | 4 540 ₽ | +13.5% |

---

## РАЗДЕЛ 7 — SELF-DEALING ЗАЩИТА

### 7.1 Проблема
Пользователь с ролью `both` размещает рекламу на своём канале и получает 85% обратно. При наличии бонусов — прямой арбитраж. **Решение:** запрет на уровне сервиса + velocity check.

### 7.2 Код

```python
async def create_placement_request(session, advertiser_id, channel_id, ...) -> PlacementRequest:
    channel = await channel_repo.get(session, channel_id)
    if channel.owner_id == advertiser_id:
        raise SelfDealingError("Нельзя размещать рекламу на собственном канале")
```

### 7.3 Velocity check (MVP)

```python
VELOCITY_WINDOW_DAYS  = 30
VELOCITY_MAX_RATIO    = Decimal("0.80")
COOLDOWN_HOURS        = 24

async def check_velocity(session, user_id, requested_amount) -> None:
    topups_30d  = await transaction_repo.sum_topups(session, user_id, days=30)
    payouts_30d = await payout_repo.sum_payouts(session, user_id, days=30)
    if topups_30d == 0:
        return  # нет пополнений — нечего проверять
    ratio = (payouts_30d + requested_amount) / topups_30d
    if ratio > VELOCITY_MAX_RATIO:
        raise VelocityCheckError(
            "Вывод заморожен на ревью администратора. Свяжитесь с поддержкой."
        )
```

---

## РАЗДЕЛ 8 — НАЛОГИ И ПРАВОВЫЕ АСПЕКТЫ

### 8.1 Платформа — УСН 6%

- Годовая выручка при базовом сценарии: ~4.1 млн ₽ → превышает лимит НПД (2.4 млн)
- Применяемый режим: **ИП на УСН «доходы» 6%**
- Константа в коде: `PLATFORM_TAX_RATE = Decimal("0.06")`
- Налоговая база: валовая выручка платформы (комиссии + подписки + payout fees)

### 8.2 Владельцы каналов — Вариант A (MVP)

**Реализация:**
- Платформа перечисляет `net_amount = gross × 0.985` — без удержания налога
- Оферта содержит: «Владелец самостоятельно несёт ответственность за уплату налогов»
- UI-блок в кабинете владельца:

```
💰 Начислено за месяц: {monthly_earned} ₽
📋 Не забудьте задекларировать доход самостоятельно
```

**Post-MVP — Вариант B (агентская схема):**
- `PayoutRequest.tax_withheld` — поле уже есть в модели (NULL в MVP)
- Платформа удерживает НПД/налог при выплате
- Требует: договор оферты с агентскими условиями, отдельный учёт

---

## РАЗДЕЛ 9 — ТИПЫ ТРАНЗАКЦИЙ

```python
class TransactionType(str, Enum):
    TOPUP                      = "topup"
    ESCROW_FREEZE              = "escrow_freeze"
    ESCROW_RELEASE             = "escrow_release"
    PLATFORM_FEE               = "platform_fee"
    REFUND_FULL                = "refund_full"
    REFUND_PARTIAL             = "refund_partial"
    CANCEL_PENALTY             = "cancel_penalty"            # 7.5% платформе
    OWNER_CANCEL_COMPENSATION  = "owner_cancel_compensation" # 42.5% владельцу
    PAYOUT                     = "payout"
    PAYOUT_FEE                 = "payout_fee"               # 1.5% — новый в v4.2
    CREDITS_BUY                = "credits_buy"
```

---

## РАЗДЕЛ 10 — ЧЕКЛИСТ РЕАЛИЗАЦИИ

### 🔴 Критические (блокируют запуск)

```
[ ] constants/payments.py: полная замена (v4.2 константы)
[ ] config/settings.py: тарифные цены 490/1490/4990
[ ] constants/tariffs.py: PLAN_DISPLAY_NAMES, PLAN_EMOJIS
[ ] Миграция: balance_rub, earned_rub → users
[ ] Миграция: platform_account (singleton)
[ ] Миграция: publication_format, message_id, scheduled_delete_at → placement_requests
[ ] Миграция: allow_format_* → channel_settings
[ ] Миграция: gross_amount, fee_amount, net_amount, tax_withheld → payout_requests
[ ] Миграция: PAYOUT_FEE → transaction_type enum
[ ] BillingService: calculate_topup_payment()
[ ] BillingService: freeze_escrow() с MIN_CAMPAIGN_BUDGET
[ ] BillingService: release_escrow() — сплит 85/15
[ ] PayoutService: check_velocity() — VELOCITY_MAX_RATIO=0.80
[ ] PayoutService: create_payout() — расчёт fee 1.5%, net_amount
[ ] PublicationService: check_bot_permissions()
[ ] PublicationService: publish_with_format()
[ ] Celery: publish_placement, delete_published_post, unpin_and_delete_post
[ ] PlacementRequestService: FORMAT_MULTIPLIERS + self-dealing check
[ ] Exceptions: SelfDealingError, VelocityCheckError, InsufficientPermissionsError
```

### 🟡 Важные (до первых пользователей)

```
[ ] FSM TopupStates: entering_amount → confirming → waiting_payment
[ ] Handler billing: двухшаговый топап с расчётом
[ ] Handler payout: показ gross/fee/net перед подтверждением
[ ] Cabinet: balance_rub и earned_rub раздельно + налоговая подсказка
[ ] Admin panel: platform_account dashboard
[ ] Health-check API: инварианты балансов
[ ] Уведомление при добавлении канала: нужны права delete + pin
```

### 🟢 Тесты

```
[ ] calculate_topup_payment(10000) → gross=10350, fee=350, desired=10000
[ ] Пополнение 499 ₽ → ValueError; 500 ₽ → OK
[ ] freeze + release → owner +85%, platform +15%, сумма = 100%
[ ] Бюджет 1 999 ₽ → ошибка; 2 000 ₽ → OK
[ ] Free + pin_24h → PlanLimitError
[ ] Self-dealing → SelfDealingError
[ ] Velocity: вывод 81% → VelocityCheckError; 79% → OK
[ ] Payout fee: gross=10000, fee=150, net=9850
[ ] Отмена после эскроу → 50%/42.5%/7.5% = 100%
[ ] Celery ETA: post_24h удаляется через 86400 сек
[ ] TelegramBadRequest при delete → не падаем, status=COMPLETED
[ ] ruff + mypy + bandit + flake8 → 0 ошибок
```

---

## РАЗДЕЛ 11 — ФАЙЛЫ К ИЗМЕНЕНИЮ

| Файл | Тип | Изменение | Приоритет |
|------|-----|-----------|-----------|
| `src/constants/payments.py` | Заменить | Все константы v4.2, убрать бонусы | 🔴 |
| `src/config/settings.py` | Изменить | Тарифные цены | 🔴 |
| `src/constants/tariffs.py` | Дополнить | PLAN_DISPLAY_NAMES, PLAN_EMOJIS | 🔴 |
| `src/db/models/user.py` | Изменить | balance_rub, earned_rub | 🔴 |
| `src/db/models/platform_account.py` | Создать | Singleton | 🔴 |
| `src/db/models/payout.py` | Изменить | gross/fee/net/tax_withheld | 🔴 |
| `src/db/models/placement_request.py` | Изменить | publication_format, message_id | 🔴 |
| `src/db/models/channel_settings.py` | Изменить | allow_format_* | 🔴 |
| `src/db/models/transaction.py` | Изменить | + PAYOUT_FEE enum | 🔴 |
| `src/core/exceptions.py` | Дополнить | SelfDealingError, VelocityCheckError | 🔴 |
| `src/core/services/billing_service.py` | Изменить | Топап, freeze/release | 🔴 |
| `src/core/services/payout_service.py` | Изменить | check_velocity, fee расчёт | 🔴 |
| `src/core/services/publication_service.py` | Изменить | send + pin + permissions | 🔴 |
| `src/tasks/publication_tasks.py` | Создать | Celery publish/delete/unpin | 🔴 |
| `src/core/services/placement_request_service.py` | Изменить | FORMAT_MULTIPLIERS, self-dealing | 🔴 |
| `src/bot/states/billing.py` | Изменить | TopupStates | 🟡 |
| `src/bot/handlers/billing/billing.py` | Изменить | UI топапа | 🟡 |
| `src/bot/handlers/owner/channel_settings.py` | Изменить | UI форматов | 🟡 |
| `src/bot/handlers/shared/cabinet.py` | Изменить | Два баланса + налоговая подсказка | 🟡 |
| `src/bot/handlers/admin/users.py` | Изменить | platform_account | 🟡 |

## ФАЙЛЫ НЕ ТРОГАТЬ НИКОГДА

```
src/core/services/xp_service.py
src/bot/handlers/advertiser/campaign_create_ai.py
src/bot/keyboards/advertiser/campaign_ai.py
src/bot/keyboards/shared/main_menu.py
src/bot/states/campaign_create.py
src/db/migrations/versions/  ← только читать существующие
```

---

*RekHarborBot Reference Document v4.2 | 12.03.2026*
*Следующий шаг: промпты Qwen по спринтам S-01 → S-14*
