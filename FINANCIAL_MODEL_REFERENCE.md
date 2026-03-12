# RekHarborBot — Эталонный документ проекта v4.1

# Дата: 12.03.2026

# Назначение: основа для промптов Qwen Code

# Заменяет: FINANCIAL_MODEL_v3.md, FINANCIAL_MODEL_v4.md

-----

## РАЗДЕЛ 0 — КЛЮЧЕВЫЕ РЕШЕНИЯ (единый источник правды)

|Параметр                     |Значение                                  |Примечание                      |
|-----------------------------|------------------------------------------|--------------------------------|
|Бонусные кредиты             |❌ Нет                                     |Отложено на post-MVP            |
|Способ оплаты                |ЮKassa (карта / СБП)                      |Stars исключены                 |
|ЮKassa комиссия              |3.5% — добавляется поверх суммы пополнения|Пользователь платит комиссию    |
|Минимальное пополнение       |500 ₽ (желаемая сумма на баланс)          |                                |
|Максимальное пополнение      |300 000 ₽                                 |Лимит ЮKassa для самозанятых    |
|Пополнение                   |Произвольная сумма                        |Быстрые кнопки + ручной ввод    |
|Курс пополнения              |1 ₽ = 1 кредит, без надбавок              |                                |
|Минимальная цена поста       |1 000 ₽                                   |Устанавливает владелец          |
|Минимальный бюджет кампании  |2 000 ₽                                   |Системное ограничение           |
|Комиссия платформы           |15%                                       |Владелец получает 85%           |
|Минимальная выплата владельцу|1 000 ₽                                   |Вручную администратором         |
|Налог (НПД)                  |4% от дохода платформы                    |Самозанятый                     |
|Self-dealing                 |Запрещено на уровне сервиса               |Нельзя размещать на своём канале|
|Форматы публикации           |5 форматов                                |Пост 24ч/48ч/7д + Закреп 24ч/48ч|
|Целевой сегмент              |Каналы 1K–50K подписчиков                 |MVP                             |

-----

## РАЗДЕЛ 1 — АРХИТЕКТУРА СЧЕТОВ

### 1.1 Четыре логических пула (никогда не смешиваются)

```
┌─────────────────────────────────────────────────────────────┐
│  БАНКОВСКИЙ СЧЁТ ПЛАТФОРМЫ (ЮKassa)                         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ USER_POOL   │  │ ESCROW_POOL │  │ PROFIT_POOL │         │
│  │             │  │             │  │             │         │
│  │ balance_rub │  │ Заморожено  │  │ 15% комиссия│         │
│  │ всех        │  │ под активные│  │ с закрытых  │         │
│  │ рекламодат. │  │ размещения  │  │ сделок      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                             │
│  ┌─────────────┐                                           │
│  │ PAYOUT_POOL │                                           │
│  │             │                                           │
│  │ earned_rub  │                                           │
│  │ всех        │                                           │
│  │ владельцев  │                                           │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Поля модели User

```python
# src/db/models/user.py — добавить поля

class User(Base):
    # Баланс рекламодателя (реальные рубли)
    balance_rub: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0")
    )
    # Источник: пополнение через ЮKassa (net_amount)
    # Расход: заморозка в эскроу при создании размещения

    # Баланс владельца канала
    earned_rub: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0")
    )
    # Источник: 85% от released эскроу после публикации
    # Расход: вывод через PayoutRequest

    # Тарифные кредиты — ТОЛЬКО для покупки подписок, НЕ для размещений
    credits: int  # уже существует, не трогать
```

### 1.3 Системный счёт платформы (новая модель)

```python
# src/db/models/platform_account.py — СОЗДАТЬ

class PlatformAccount(Base):
    """Singleton — всегда одна запись (id=1)."""
    __tablename__ = "platform_account"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    # Текущие обязательства
    escrow_reserved:    Mapped[Decimal] = mapped_column(Numeric(14,2), default=Decimal("0"))
    # = SUM(PlacementRequest.final_price WHERE status='escrow')

    payout_reserved:    Mapped[Decimal] = mapped_column(Numeric(14,2), default=Decimal("0"))
    # = SUM(PayoutRequest.amount WHERE status IN ('pending','processing'))

    # Прибыль платформы
    profit_accumulated: Mapped[Decimal] = mapped_column(Numeric(14,2), default=Decimal("0"))
    # = SUM(15% от released эскроу)

    # Исторические итоги (для аудита)
    total_topups:       Mapped[Decimal] = mapped_column(Numeric(14,2), default=Decimal("0"))
    total_payouts:      Mapped[Decimal] = mapped_column(Numeric(14,2), default=Decimal("0"))

    updated_at: Mapped[datetime] = mapped_column(onupdate=func.now())
```

### 1.4 Инварианты балансов (health-check)

```python
# src/api/routers/health.py

# 1. Деньги пользователей не превышают реальный остаток на счёте
assert SUM(users.balance_rub) <= real_bank_balance

# 2. Эскроу = сумма активных заморозок
assert platform.escrow_reserved == SUM(
    placement_requests.final_price WHERE status='escrow'
)

# 3. Резерв выплат = сумма ожидающих выплат
assert platform.payout_reserved == SUM(
    payout_requests.amount WHERE status IN ('pending','processing')
)

# 4. earned_rub пользователей покрыты реальными деньгами
assert SUM(users.earned_rub) <= (
    real_bank_balance - platform.escrow_reserved - platform.profit_accumulated
)
```

-----

## РАЗДЕЛ 2 — ПОПОЛНЕНИЕ БАЛАНСА

### 2.1 Принцип расчёта

Пользователь указывает **желаемую сумму на баланс** → платформа считает
**итоговую сумму к оплате** с учётом комиссии ЮKassa:

```
Желаю на баланс:     10 000 ₽
Комиссия ЮKassa 3.5%:  +350 ₽
─────────────────────────────
Итого к оплате:      10 350 ₽
Будет зачислено:     10 000 ₽  ← ровно то что указал
```

### 2.2 UX flow

```
[💳 Пополнить баланс]
    │
    ├─ Шаг 1: выбор желаемой суммы
    │
    │  ┌───────────────────────────────────────────┐
    │  │  💳 ПОПОЛНЕНИЕ БАЛАНСА                    │
    │  │                                           │
    │  │  Текущий баланс: 350 ₽                   │
    │  │                                           │
    │  │  Сколько зачислить на баланс?             │
    │  │                                           │
    │  │  [500 ₽] [1 000 ₽] [2 000 ₽] [5 000 ₽]  │
    │  │  [10 000 ₽]  [20 000 ₽]                  │
    │  │                                           │
    │  │  Или введите сумму (мин. 500 ₽):         │
    │  └───────────────────────────────────────────┘
    │
    └─ Шаг 2: подтверждение с расчётом
    
       ┌───────────────────────────────────────────┐
       │  💳 ПОДТВЕРЖДЕНИЕ                         │
       │                                           │
       │  Будет зачислено:     10 000 ₽            │
       │  Комиссия ЮKassa:       +350 ₽            │
       │  ─────────────────────────────            │
       │  Итого к оплате:      10 350 ₽            │
       │                                           │
       │  [✅ Перейти к оплате]  [🔙 Назад]        │
       └───────────────────────────────────────────┘
```

### 2.3 Реализация

```python
# src/core/services/billing_service.py

YOOKASSA_FEE_RATE = Decimal("0.035")
MIN_TOPUP         = Decimal("500")
MAX_TOPUP         = Decimal("300000")

def calculate_topup_payment(desired_balance: Decimal) -> dict:
    """
    Рассчитывает сколько нужно заплатить чтобы получить desired_balance на счёт.
    Вызывается до создания платежа — для показа пользователю.
    """
    fee_amount   = (desired_balance * YOOKASSA_FEE_RATE).quantize(Decimal("0.01"))
    gross_amount = desired_balance + fee_amount
    return {
        "desired_balance": desired_balance,  # зачислить на balance_rub
        "fee_amount":      fee_amount,       # комиссия ЮKassa в рублях
        "gross_amount":    gross_amount,     # сумма платежа в ЮKassa
    }

async def initiate_topup(
    self, session: AsyncSession,
    user_id: int,
    desired_balance: Decimal,
) -> str:
    if desired_balance < MIN_TOPUP:
        raise ValueError(f"Минимальная сумма пополнения — {MIN_TOPUP} ₽")
    if desired_balance > MAX_TOPUP:
        raise ValueError(f"Максимальная сумма пополнения — {MAX_TOPUP} ₽")

    calc = self.calculate_topup_payment(desired_balance)

    payment = await yookassa_service.create_payment(
        amount=calc["gross_amount"],         # пользователь платит это
        description="Пополнение баланса RekHarborBot",
        metadata={
            "user_id":         str(user_id),
            "type":            "topup",
            "desired_balance": str(calc["desired_balance"]),  # зачислить именно это
        }
    )
    return payment.confirmation_url

async def process_topup_webhook(
    self, session: AsyncSession,
    payment_id: str,
    gross_amount: Decimal,
    metadata: dict,
) -> None:
    user_id         = int(metadata["user_id"])
    desired_balance = Decimal(metadata["desired_balance"])

    # Зачисляем ЖЕЛАЕМУЮ сумму — ровно то что пользователь видел в UI
    user = await user_repo.get_for_update(session, user_id)
    user.balance_rub += desired_balance

    platform = await platform_repo.get_for_update(session, id=1)
    platform.total_topups += desired_balance

    await transaction_repo.create(session,
        type=TransactionType.TOPUP,
        amount=desired_balance,
        user_id=user_id,
        meta={
            "gross":    str(gross_amount),
            "fee":      str(gross_amount - desired_balance),
        }
    )
```

### 2.4 FSM состояния

```python
# src/bot/states/billing.py

class TopupStates(StatesGroup):
    entering_amount   = State()  # ввод желаемой суммы
    confirming        = State()  # показ расчёта + подтверждение
    waiting_payment   = State()  # ожидание вебхука от ЮKassa
```

-----

## РАЗДЕЛ 3 — ФОРМАТЫ ПУБЛИКАЦИИ

### 3.1 Пять форматов

|Формат    |Действия бота                                          |Коэфф. к цене  |
|----------|-------------------------------------------------------|---------------|
|`post_24h`|Публикует. Удаляет через 24 ч                          |× 1.0 (базовый)|
|`post_48h`|Публикует. Удаляет через 48 ч                          |× 1.4          |
|`post_7d` |Публикует. Удаляет через 7 дней                        |× 2.0          |
|`pin_24h` |Публикует + закрепляет. Открепляет и удаляет через 24 ч|× 3.0          |
|`pin_48h` |Публикует + закрепляет. Открепляет и удаляет через 48 ч|× 4.0          |

```python
# src/constants/payments.py

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

### 3.2 Права бота в канале

|Право            |Для форматов    |Запрашивать при добавлении|
|-----------------|----------------|--------------------------|
|`post_messages`  |все             |✅ уже есть                |
|`delete_messages`|все             |✅ новое — обязательное    |
|`pin_messages`   |pin_24h, pin_48h|✅ новое — для закрепов    |

```python
# src/core/services/publication_service.py

async def check_bot_permissions(
    self, channel_id: int, fmt: str
) -> None:
    bot_member = await bot.get_chat_member(channel_id, bot.id)

    if not bot_member.can_delete_messages:
        raise InsufficientPermissionsError(
            "Боту нужно право удалять сообщения для авто-удаления поста"
        )
    if fmt in ("pin_24h", "pin_48h") and not bot_member.can_pin_messages:
        raise InsufficientPermissionsError(
            "Боту нужно право закреплять сообщения для этого формата"
        )
```

### 3.3 Расширение модели ChannelSettings

```python
# src/db/models/channel_settings.py — добавить поля

# Разрешённые форматы (владелец включает/выключает)
allow_format_post_24h: Mapped[bool] = mapped_column(default=True)
allow_format_post_48h: Mapped[bool] = mapped_column(default=True)
allow_format_post_7d:  Mapped[bool] = mapped_column(default=False)
allow_format_pin_24h:  Mapped[bool] = mapped_column(default=False)
allow_format_pin_48h:  Mapped[bool] = mapped_column(default=False)

# Минимальная базовая цена поста (системная константа)
# MIN_PRICE_PER_POST = 1 000 ₽
```

### 3.4 Расширение модели PlacementRequest

```python
# src/db/models/placement_request.py — добавить поля

class PublicationFormat(str, Enum):
    POST_24H = "post_24h"
    POST_48H = "post_48h"
    POST_7D  = "post_7d"
    PIN_24H  = "pin_24h"
    PIN_48H  = "pin_48h"

publication_format:   Mapped[PublicationFormat] = mapped_column(
    default=PublicationFormat.POST_24H
)
message_id:           Mapped[int | None] = mapped_column(nullable=True)
scheduled_delete_at:  Mapped[datetime | None] = mapped_column(nullable=True)
deleted_at:           Mapped[datetime | None] = mapped_column(nullable=True)
```

### 3.5 Celery задачи публикации

```python
# src/tasks/publication_tasks.py — СОЗДАТЬ

@celery_app.task(queue="critical", bind=True, max_retries=3)
async def publish_placement(self, placement_id: int) -> None:
    """Публикует пост и планирует удаление."""
    placement = await placement_repo.get(placement_id)
    fmt = placement.publication_format

    try:
        await publication_service.check_bot_permissions(placement.channel_id, fmt)

        msg = await bot.send_message(placement.channel_id, placement.ad_text)
        placement.message_id = msg.message_id

        if fmt in ("pin_24h", "pin_48h"):
            await bot.pin_chat_message(
                placement.channel_id, msg.message_id,
                disable_notification=True
            )

        duration = FORMAT_DURATIONS_SECONDS[fmt]
        placement.scheduled_delete_at = datetime.utcnow() + timedelta(seconds=duration)
        placement.status = PlacementStatus.PUBLISHED

        # Разблокировать эскроу
        await billing_service.release_escrow(placement_id)

        # Запланировать удаление
        if fmt in ("pin_24h", "pin_48h"):
            unpin_and_delete_post.apply_async(
                args=[placement_id], eta=placement.scheduled_delete_at
            )
        else:
            delete_published_post.apply_async(
                args=[placement_id], eta=placement.scheduled_delete_at
            )

    except Exception as exc:
        self.retry(exc=exc, countdown=3600)  # повтор через 1 час


@celery_app.task(queue="critical")
async def delete_published_post(placement_id: int) -> None:
    placement = await placement_repo.get(placement_id)
    if placement.status != PlacementStatus.PUBLISHED:
        return
    try:
        await bot.delete_message(placement.channel_id, placement.message_id)
    except TelegramBadRequest:
        pass  # уже удалён вручную — не критично
    finally:
        placement.deleted_at = datetime.utcnow()
        placement.status = PlacementStatus.COMPLETED


@celery_app.task(queue="critical")
async def unpin_and_delete_post(placement_id: int) -> None:
    placement = await placement_repo.get(placement_id)
    if placement.status != PlacementStatus.PUBLISHED:
        return
    try:
        await bot.unpin_chat_message(placement.channel_id, placement.message_id)
        await bot.delete_message(placement.channel_id, placement.message_id)
    except TelegramBadRequest:
        pass
    finally:
        placement.deleted_at = datetime.utcnow()
        placement.status = PlacementStatus.COMPLETED
```

-----

## РАЗДЕЛ 4 — ЖИЗНЕННЫЙ ЦИКЛ ДЕНЕГ

### 4.1 Пополнение баланса

```
Пользователь вводит desired_balance = 10 000 ₽
    │
    ├─ gross_amount = 10 000 + (10 000 × 0.035) = 10 350 ₽  ← платит
    ├─ ЮKassa удерживает 350 ₽, на счёт платформы: 10 000 ₽
    ├─ user.balance_rub += 10 000  ← зачисляем desired_balance
    ├─ platform.total_topups += 10 000
    └─ Transaction(TOPUP, 10 000)
```

### 4.2 Создание размещения → Эскроу

```
Рекламодатель выбирает канал + формат
    │
    ├─ final_price = channel.price_per_post × FORMAT_MULTIPLIERS[format]
    ├─ ✅ final_price >= MIN_CAMPAIGN_BUDGET (2 000 ₽)
    ├─ ✅ user.balance_rub >= final_price
    ├─ ✅ format в PLAN_LIMITS[user.plan]["formats"]
    ├─ ✅ channel.owner_id != user.id  (self-dealing check)
    │
    ├─ user.balance_rub       -= final_price
    ├─ platform.escrow_reserved += final_price
    └─ Transaction(ESCROW_FREEZE, final_price)
```

### 4.3 Успешная публикация → Разблокировка

```
Бот опубликовал пост, message_id сохранён
    │
    ├─ owner_amount    = final_price × 0.85
    ├─ platform_amount = final_price × 0.15
    │
    ├─ owner.earned_rub             += owner_amount
    ├─ platform.escrow_reserved     -= final_price
    ├─ platform.profit_accumulated  += platform_amount
    │
    ├─ Transaction(ESCROW_RELEASE, owner_amount, owner_id)
    ├─ Transaction(PLATFORM_FEE,   platform_amount)
    └─ Уведомить обе стороны
```

### 4.4 Выплата владельцу

```
Владелец запрашивает вывод (мин. 1 000 ₽)
    │
    ├─ ✅ owner.earned_rub >= 1 000
    ├─ ✅ нет активного PayoutRequest у владельца
    │
    ├─ owner.earned_rub         -= requested_amount
    ├─ platform.payout_reserved += requested_amount
    ├─ PayoutRequest(status='pending')
    ├─ Уведомить администратора (@adbelin / David)
    │
    ├─ Администратор переводит вручную 09:00–22:00 МСК
    ├─ PayoutRequest.status = 'paid'
    ├─ platform.payout_reserved  -= requested_amount
    ├─ platform.total_payouts    += requested_amount
    └─ Уведомить владельца
```

### 4.5 Отмена / Возврат

|Сценарий                                        |Рекламодатель|Владелец|Платформа|Репутация|
|------------------------------------------------|-------------|--------|---------|---------|
|Отмена до эскроу                                |+100%        |0       |0        |0        |
|Отмена после эскроу, до подтверждения владельцем|+100%        |0       |0        |−5       |
|Отмена после подтверждения владельцем           |+50%         |+42.5%  |+7.5%    |−20      |
|Владелец отклонил                               |+100%        |0       |0        |0        |
|Техническая ошибка (бот удалён и т.п.)          |+100%        |0       |0        |0        |

-----

## РАЗДЕЛ 5 — ТАРИФНАЯ МОДЕЛЬ

### 5.1 Тарифы по инструментам (не по деньгам)

|Тариф      |Цена/мес|Активных кампаний|AI-генерация|Аналитика       |Доступные форматы|
|-----------|--------|-----------------|------------|----------------|-----------------|
|**Free**   |0 ₽     |1                |❌           |Базовая         |post_24h         |
|**Starter**|490 ₽   |5                |3/мес       |Расширенная     |+ post_48h       |
|**Pro**    |1 490 ₽ |20               |20/мес      |Полная + экспорт|+ post_7d        |
|**Agency** |4 990 ₽ |Безлим           |Безлим      |Полная + API    |Все 5 форматов   |

```python
# src/constants/payments.py

PLAN_PRICES: dict[str, Decimal] = {
    "free":    Decimal("0"),
    "starter": Decimal("490"),
    "pro":     Decimal("1490"),
    "agency":  Decimal("4990"),
}

PLAN_LIMITS: dict[str, dict] = {
    "free":    {"active_campaigns": 1,  "ai_per_month": 0,  "formats": ["post_24h"]},
    "starter": {"active_campaigns": 5,  "ai_per_month": 3,  "formats": ["post_24h", "post_48h"]},
    "pro":     {"active_campaigns": 20, "ai_per_month": 20, "formats": ["post_24h", "post_48h", "post_7d"]},
    "agency":  {"active_campaigns": -1, "ai_per_month": -1, "formats": ["post_24h", "post_48h", "post_7d", "pin_24h", "pin_48h"]},
}
```

### 5.2 Конкурентное преимущество

|Платформа       |Комиссия|Доля владельца|Авто-удаление|Закреп|
|----------------|--------|--------------|-------------|------|
|Telega.in       |~30%    |70%           |❌            |❌     |
|Epicstars       |~25%    |75%           |❌            |❌     |
|**RekHarborBot**|**15%** |**85%**       |**✅**        |**✅** |

-----

## РАЗДЕЛ 6 — ФИНАНСОВАЯ МОДЕЛЬ

### 6.1 Константы

```python
PLATFORM_COMMISSION  = Decimal("0.15")
OWNER_SHARE          = Decimal("0.85")
YOOKASSA_FEE_RATE    = Decimal("0.035")
NPD_TAX_RATE         = Decimal("0.04")
MIN_TOPUP            = Decimal("500")
MAX_TOPUP            = Decimal("300000")
MIN_CAMPAIGN_BUDGET  = Decimal("2000")
MIN_PRICE_PER_POST   = Decimal("1000")
MIN_PAYOUT           = Decimal("1000")
```

### 6.2 P&L (100 рекламодателей, 20 каналов)

**Допущения:**
50 Free / 30 Starter / 15 Pro / 5 Agency.
Средний чек: Free 2K, Starter 4K, Pro 7K, Agency 12K.
Кампаний в месяц: Free 1, Starter 3, Pro 5, Agency 15.

```
ДОХОДЫ
────────────────────────────────────────────────────
Тарифные подписки:
  Starter (30 × 490):               14 700 ₽
  Pro     (15 × 1 490):             22 350 ₽
  Agency  ( 5 × 4 990):             24 950 ₽
  ──────────────────────────────────────────
  Итого подписки:                   62 000 ₽

Оборот размещений:
  Free    (50 × 1  × 2 000):       100 000 ₽
  Starter (30 × 3  × 4 000):       360 000 ₽
  Pro     (15 × 5  × 7 000):       525 000 ₽
  Agency  ( 5 × 15 × 12 000):      900 000 ₽
  ──────────────────────────────────────────
  Итого оборот:                  1 885 000 ₽
  Комиссия платформы (15%):        282 750 ₽

  Итого валовая выручка:           344 750 ₽

ПЕРЕМЕННЫЕ ЗАТРАТЫ
────────────────────────────────────────────────────
ЮKassa с подписок (62 000 × 3.5%):   -2 170 ₽
  (комиссия с пополнений — за счёт пользователей)

НПД 4% от валовой выручки:
  (344 750 × 4%):                   -13 790 ₽

  Итого переменные:                 -15 960 ₽

ФИКСИРОВАННЫЕ ЗАТРАТЫ
────────────────────────────────────────────────────
  Сервер:                            -2 000 ₽
  Домен + SSL (3 500 ÷ 12):            -292 ₽
  Claude API (оценка):                 -500 ₽
  ──────────────────────────────────────────
  Итого фиксированные:               -2 792 ₽

═══════════════════════════════════════════════════════
ЧИСТАЯ ПРИБЫЛЬ:                     325 998 ₽/мес
Маржинальность:                           94.6%
═══════════════════════════════════════════════════════

Распределение оборота размещений:
  Владельцам каналов (85%):       1 602 250 ₽  ← стимул регистрироваться
  Платформе (15%):                  282 750 ₽
```

### 6.3 Breakeven

```
Фиксированные: 2 792 ₽/мес
Переменная маржа: ~95%

Breakeven ≈ 2 940 ₽ выручки
= 6 подписок Starter
= 1 кампания Agency (12 000 × 15% = 1 800 ₽) + 2 Starter
```

### 6.4 Влияние форматов на средний чек

Если 20% рекламодателей выбирают платные форматы:

|Микс форматов        |Средний чек|Рост оборота|
|---------------------|-----------|------------|
|100% post_24h        |4 000 ₽    |базовый     |
|+ 15% post_48h (×1.4)|4 240 ₽    |+6%         |
|+ 5% pin_24h (×3.0)  |4 540 ₽    |+13.5%      |

-----

## РАЗДЕЛ 7 — SELF-DEALING ЗАЩИТА

### 7.1 Проблема

Пользователь с ролью `both` пополняет 10 000 ₽, размещает рекламу
на своём канале, получает 8 500 ₽ назад как владелец. Потеря только 15%.
При бонусах/скидках становится арбитражем против платформы.

### 7.2 Решение

```python
# src/core/services/placement_request_service.py

async def create_placement_request(
    self, session, advertiser_id, channel_id, ...
) -> PlacementRequest:

    channel = await channel_repo.get(session, channel_id)
    if channel.owner_id == advertiser_id:
        raise SelfDealingError(
            "Нельзя размещать рекламу на собственном канале"
        )
    # ... продолжение создания заявки
```

### 7.3 Дополнительные меры (post-MVP)

|Мера          |Триггер                                                           |
|--------------|------------------------------------------------------------------|
|Velocity check|Вывод > 80% от суммы пополнений за 30 дней                        |
|Cooldown      |Пополнение → размещение → вывод в течение 24ч → заморозка на ревью|

-----

## РАЗДЕЛ 8 — ТИПЫ ТРАНЗАКЦИЙ

```python
# src/db/models/transaction.py — дополнить enum

class TransactionType(str, Enum):
    TOPUP           = "topup"           # Пополнение через ЮKassa
    ESCROW_FREEZE   = "escrow_freeze"   # Заморозка под размещение
    ESCROW_RELEASE  = "escrow_release"  # Разблокировка → владельцу (85%)
    PLATFORM_FEE    = "platform_fee"    # Комиссия платформы (15%)
    REFUND_FULL     = "refund_full"     # Возврат 100%
    REFUND_PARTIAL  = "refund_partial"  # Возврат 50% при отмене после эскроу
    CANCEL_PENALTY  = "cancel_penalty"  # Штраф платформы 7.5%
    OWNER_CANCEL_COMPENSATION = "owner_cancel_compensation"  # 42.5% владельцу
    PAYOUT          = "payout"          # Выплата владельцу
    CREDITS_BUY     = "credits_buy"     # Покупка тарифных кредитов
```

-----

## РАЗДЕЛ 9 — ЧЕКЛИСТ РЕАЛИЗАЦИИ

### 🔴 Критические (блокируют запуск)

```
[ ] Миграция: balance_rub, earned_rub → таблица users
[ ] Миграция: создать таблицу platform_account (singleton id=1)
[ ] Миграция: publication_format, message_id, scheduled_delete_at → placement_requests
[ ] Миграция: allow_format_* → channel_settings
[ ] Миграция: обновить MIN_PRICE_PER_POST до 1 000 ₽
[ ] Миграция: дополнить enum transaction_type
[ ] constants/payments.py: полная замена (новые тарифы, комиссии, форматы, лимиты)
[ ] BillingService: calculate_topup_payment() — расчёт gross из desired
[ ] BillingService: initiate_topup() — произвольная сумма
[ ] BillingService: process_topup_webhook() — зачисление desired_balance
[ ] BillingService: freeze_escrow() — SELECT FOR UPDATE + MIN_CAMPAIGN_BUDGET
[ ] BillingService: release_escrow() — сплит 85/15
[ ] BillingService: check_self_dealing()
[ ] BillingService: check_format_allowed_for_plan()
[ ] PublicationService: check_bot_permissions()
[ ] PublicationService: publish_with_format() — send + optional pin
[ ] Celery: publish_placement task
[ ] Celery: delete_published_post task
[ ] Celery: unpin_and_delete_post task
[ ] PlacementRequestService: расчёт final_price с FORMAT_MULTIPLIERS
[ ] PlacementRequestService: вызов check_self_dealing
[ ] PayoutService: SELECT FOR UPDATE при списании earned_rub
[ ] config/settings.py: обновить тарифные цены
```

### 🟡 Важные (до первых пользователей)

```
[ ] FSM TopupStates: entering_amount → confirming → waiting_payment
[ ] Handler billing: UI двухшагового пополнения с расчётом
[ ] Handler channel_settings: UI включения/выключения форматов
[ ] Handler campaign creation: шаг выбора формата + расчёт цены
[ ] Cabinet: показывать balance_rub и earned_rub раздельно
[ ] Admin panel: показывать platform_account (escrow/profit/payout_reserved)
[ ] Health-check endpoint: проверка инвариантов
[ ] Уведомление владельцу при добавлении канала: нужны права delete + pin
```

### 🟢 Тесты

```
[ ] calculate_topup_payment(10000) → gross=10350, fee=350, desired=10000
[ ] Пополнение 499 ₽ → ValueError; 500 ₽ → OK
[ ] freeze + release → все балансы сходятся до копейки
[ ] Бюджет 1 999 ₽ → ошибка; 2 000 ₽ → OK
[ ] Free тариф + pin_24h → ошибка формата
[ ] Self-dealing → SelfDealingError
[ ] Отмена после эскроу → 50% / 42.5% / 7.5%
[ ] Celery ETA: пост удаляется ровно через N секунд
[ ] TelegramBadRequest при удалении → не падаем, статус COMPLETED
[ ] ruff + mypy + bandit + flake8 → 0 ошибок
```

-----

## РАЗДЕЛ 10 — ФАЙЛЫ К ИЗМЕНЕНИЮ

|Файл                                            |Тип     |Изменение                                          |Приоритет|
|------------------------------------------------|--------|---------------------------------------------------|---------|
|`src/constants/payments.py`                     |Заменить|Новые константы, тарифы, форматы, лимиты           |🔴        |
|`src/db/models/user.py`                         |Изменить|balance_rub, earned_rub                            |🔴        |
|`src/db/models/platform_account.py`             |Создать |Singleton системного счёта                         |🔴        |
|`src/db/models/channel_settings.py`             |Изменить|allow_format_*                                     |🔴        |
|`src/db/models/placement_request.py`            |Изменить|publication_format, message_id, scheduled_delete_at|🔴        |
|`src/db/models/transaction.py`                  |Изменить|Дополнить enum                                     |🔴        |
|`src/core/services/billing_service.py`          |Изменить|Топап, freeze/release 85/15, self-dealing          |🔴        |
|`src/core/services/publication_service.py`      |Изменить|send + pin + check permissions                     |🔴        |
|`src/tasks/publication_tasks.py`                |Создать |delete/unpin Celery tasks                          |🔴        |
|`src/core/services/placement_request_service.py`|Изменить|FORMAT_MULTIPLIERS, self-dealing                   |🔴        |
|`src/config/settings.py`                        |Изменить|Цены тарифов                                       |🟡        |
|`src/bot/states/billing.py`                     |Изменить|TopupStates                                        |🟡        |
|`src/bot/handlers/billing/billing.py`           |Изменить|UI произвольного пополнения                        |🟡        |
|`src/bot/handlers/owner/channel_settings.py`    |Изменить|UI форматов                                        |🟡        |
|`src/bot/handlers/shared/cabinet.py`            |Изменить|Два баланса                                        |🟡        |
|`src/bot/handlers/admin/users.py`               |Изменить|platform_account                                   |🟡        |

## ФАЙЛЫ НЕ ТРОГАТЬ НИКОГДА

```
src/core/services/xp_service.py
src/bot/handlers/advertiser/campaign_create_ai.py
src/bot/keyboards/advertiser/campaign_ai.py
src/bot/keyboards/shared/main_menu.py
src/bot/states/campaign_create.py
src/db/migrations/versions/  ← только читать существующие
```

-----

*RekHarborBot Reference Document v4.1 | 12.03.2026*
*Следующий шаг: промпты Qwen по Разделу 9 (чеклист реализации)*
