# DOC-04: Сервисы, Репозитории и Бизнес-логика

**RekHarborBot — Техническая документация v3.0**  
**Дата:** 2026-03-10 | Все сервисы, методы, правила

---

## 1. Архитектурный паттерн

```
Handler (aiogram)
  └── Service (src/core/services/)
        └── Repository (src/db/repositories/)
              └── SQLAlchemy Session (src/db/session.py)
```

- **Handlers** не работают с БД напрямую — только через сервисы
- **Сервисы** содержат бизнес-логику, оркестрируют репозитории
- **Репозитории** — только CRUD + запросы, без бизнес-правил
- **Исключения** объявлены в `src/core/exceptions.py`

---

## 2. Репозитории

### 2.1 BaseRepository (`src/db/repositories/base.py`)

```python
class BaseRepository:
    def __init__(self, session: AsyncSession): ...
    async def get(self, id: int) -> Model | None: ...
    async def get_all(self, limit=100, offset=0) -> list[Model]: ...
    async def create(self, **kwargs) -> Model: ...
    async def update(self, id: int, **kwargs) -> Model | None: ...
    async def delete(self, id: int) -> bool: ...
    async def exists(self, **filters) -> bool: ...
```

### 2.2 UserRepo (`src/db/repositories/user_repo.py`)

```python
async def get_by_telegram_id(telegram_id: int) -> User | None
async def get_or_create(telegram_id: int, first_name: str, ...) -> tuple[User, bool]
async def update_role(user_id: int, role: str) -> User
async def update_credits(user_id: int, delta: Decimal) -> User
async def get_by_plan(plan: str) -> list[User]
async def get_expiring_plans(days_ahead: int = 3) -> list[User]
async def increment_ai_counter(user_id: int) -> int
async def update_login_streak(user_id: int) -> int
async def ban(user_id: int, reason: str) -> User
async def unban(user_id: int) -> User
async def search(query: str, limit: int = 20) -> list[User]
```

### 2.3 CampaignRepo (`src/db/repositories/campaign_repo.py`)

```python
async def get_by_advertiser(advertiser_id: int, status=None, limit=20, offset=0) -> list[Campaign]
async def get_active_by_advertiser(advertiser_id: int) -> list[Campaign]
async def count_active(advertiser_id: int) -> int
async def update_status(campaign_id: int, status: CampaignStatus) -> Campaign
async def update_stats(campaign_id: int, views: int, clicks: int) -> Campaign
async def get_scheduled(before: datetime) -> list[Campaign]  # для Celery Beat
```

### 2.4 LogRepo (`src/db/repositories/log_repo.py`)

```python
async def create_log(campaign_id: int, channel_id: int, placement_request_id=None) -> MailingLog
async def update_status(log_id: int, status: MailingStatus, message_id=None, error=None) -> MailingLog
async def get_by_campaign(campaign_id: int) -> list[MailingLog]
async def count_by_status(campaign_id: int, status: MailingStatus) -> int
async def get_failed_retryable() -> list[MailingLog]  # статус=RETRY, для Celery
```

### 2.5 TransactionRepo (`src/db/repositories/transaction_repo.py`)

```python
async def create_topup(user_id: int, amount: Decimal) -> Transaction
async def create_payment(user_id: int, amount: Decimal, ref_id: int) -> Transaction
async def create_refund(user_id: int, amount: Decimal, ref_id: int) -> Transaction
async def create_escrow_freeze(user_id: int, amount: Decimal, placement_id: int) -> Transaction
async def create_escrow_release(user_id: int, amount: Decimal, placement_id: int) -> Transaction
async def get_by_user(user_id: int, limit=50, offset=0) -> list[Transaction]
async def get_balance_history(user_id: int, days: int = 30) -> list[Transaction]
```

### 2.6 PayoutRepo (`src/db/repositories/payout_repo.py`)

```python
async def create_payout(owner_id: int, amount: Decimal, placement_id=None) -> Payout
async def get_pending() -> list[Payout]  # для обработки
async def get_by_owner(owner_id: int, limit=20) -> list[Payout]
async def get_available_amount(owner_id: int) -> Decimal  # сумма к выплате
async def update_status(payout_id: int, status: PayoutStatus, processed_at=None) -> Payout
```

### 2.7 PlacementRequestRepo (создаётся в Этапе 2)

```python
async def create(advertiser_id, campaign_id, channel_id, proposed_price, final_text, ...) -> PlacementRequest
    # expires_at = now() + 24h автоматически

async def get_by_id(placement_id: int) -> PlacementRequest | None
async def get_by_advertiser(advertiser_id, status=None, limit=20, offset=0) -> list[PlacementRequest]
async def get_by_channel(channel_id, status=None, limit=20, offset=0) -> list[PlacementRequest]
async def get_pending_for_owner(owner_id: int) -> list[PlacementRequest]
    # JOIN telegram_chats по owner_id, фильтр status=PENDING_OWNER

async def get_expired() -> list[PlacementRequest]
    # expires_at < now() AND status IN (PENDING_OWNER, COUNTER_OFFER)

async def update_status(placement_id, status, rejection_reason=None) -> PlacementRequest | None
async def accept(placement_id, final_price=None, final_schedule=None) -> PlacementRequest | None
    # Если final_* не переданы → копировать из proposed_*
    # status → PENDING_PAYMENT

async def reject(placement_id, rejection_reason: str) -> PlacementRequest | None
    # status → CANCELLED

async def counter_offer(placement_id, proposed_price=None, proposed_schedule=None) -> PlacementRequest | None
    # counter_offer_count += 1, last_counter_at = now(), expires_at = now() + 24h
    # Если counter_offer_count >= 3 после инкремента → вернуть None

async def set_escrow(placement_id, escrow_transaction_id) -> PlacementRequest | None
    # status → ESCROW

async def set_published(placement_id, published_at=None) -> PlacementRequest | None
    # status → PUBLISHED, published_at = now()

async def count_pending_for_owner(owner_id: int) -> int
    # Для счётчика в кнопке меню

async def count_cancellations_in_30_days(advertiser_id: int) -> int
    # Для правила "3 отмены за 30 дней"
```

### 2.8 ChannelSettingsRepo (создаётся в Этапе 2)

```python
async def get_by_channel(channel_id: int) -> ChannelSettings | None
async def get_or_create_default(channel_id: int, owner_id: int) -> ChannelSettings
    # Создаёт с дефолтными значениями из констант ChannelSettings.*

async def upsert(channel_id, owner_id, **kwargs) -> ChannelSettings
    # Валидация — в сервисе, не здесь

async def get_by_owner(owner_id: int) -> list[ChannelSettings]
async def delete(channel_id: int) -> bool
```

### 2.9 ReputationRepo (создаётся в Этапе 2)

```python
async def get_by_user(user_id: int) -> ReputationScore | None
async def get_or_create(user_id: int) -> ReputationScore
    # default score=5.0

async def update_score(user_id, role, delta, new_score) -> ReputationScore | None
async def set_block(user_id, role, blocked_until, reason=None) -> ReputationScore | None
    # blocked_until=None → снять блокировку

async def increment_violations(user_id, role) -> ReputationScore | None
async def add_history(user_id, action, delta, new_score, role, placement_request_id=None, comment=None) -> ReputationHistory
async def get_history(user_id, role=None, limit=20, offset=0) -> list[ReputationHistory]
async def get_users_with_expired_blocks() -> list[ReputationScore]
    # blocked_until < now(), для Celery авто-разблокировки

async def count_invalid_rejections_streak(user_id: int) -> int
    # Последовательные reject_invalid_* в истории
```

---

## 3. Сервисы

### 3.1 BillingService (`src/core/services/billing_service.py`)

Управление балансом и платежами.

```python
async def topup(user_id: int, amount: Decimal, payment_method: str) -> Transaction
    # Проверить: amount >= MIN_TOPUP (100 кр)
    # Зачислить на баланс user.credits += amount
    # Создать Transaction(type=TOPUP)

async def charge(user_id: int, amount: Decimal, campaign_id: int) -> Transaction
    # Проверить баланс достаточен
    # Списать user.credits -= amount
    # Создать Transaction(type=PAYMENT)
    # Если недостаточно → raise InsufficientFundsError

async def refund(user_id: int, amount: Decimal, reference_id: int) -> Transaction
    # Вернуть на баланс user.credits += amount
    # Создать Transaction(type=REFUND)

async def freeze_escrow_for_placement(placement_id, advertiser_id, amount) -> Transaction
    # (добавлено в Этапе 2)
    # user.credits -= amount
    # Transaction(type=ESCROW_FREEZE)
    # Если недостаточно → raise InsufficientFundsError

async def release_escrow_for_placement(placement_id, owner_id, total_amount) -> tuple[Transaction, Transaction]
    # (добавлено в Этапе 2)
    # owner_amount = total_amount * 0.80
    # commission = total_amount * 0.20
    # Зачислить owner_amount → owner.credits
    # Transaction(type=ESCROW_RELEASE) для owner
    # Transaction(type=COMMISSION) для платформы

async def partial_refund(user_id: int, amount: Decimal, placement_id: int) -> Transaction
    # Частичный возврат (50% при отмене после эскроу)

async def check_balance(user_id: int, required: Decimal) -> bool
    # True если credits >= required

async def get_balance(user_id: int) -> Decimal
async def get_transactions(user_id: int, limit=50) -> list[Transaction]
```

### 3.2 MailingService (`src/core/services/mailing_service.py`)

Публикация рекламных постов.

```python
async def send_campaign(campaign_id: int) -> dict[int, bool]
    # Для каждого канала в кампании: отправить через sender.py
    # Вернуть {channel_id: success_bool}

async def send_to_channel(campaign_id: int, channel_id: int) -> bool
    # Одна отправка: Bot API → channel
    # При успехе: MailingLog(status=SENT), обновить Campaign.views_total
    # При ошибке: MailingLog(status=FAILED или RETRY)

async def publish_placement(placement_id: int) -> bool
    # (добавлено в Этапе 2)
    # Получить PlacementRequest
    # Опубликовать final_text в channel_id через sender.py
    # При успехе: MailingLog(status=SENT, placement_request_id=placement_id)
    # При ошибке: MailingLog(status=FAILED), вернуть False
    # Таймаут 1 час, потом False

async def retry_failed(log_id: int) -> bool
    # Повторить неудачную отправку

async def get_send_stats(campaign_id: int) -> dict
    # {sent: N, failed: N, total: N, success_rate: N%}
```

### 3.3 PlacementRequestService (создаётся в Этапе 2)

Оркестратор полного флоу размещения.

```python
async def create_request(advertiser_id, campaign_id, channel_id, proposed_price, final_text, ...) -> PlacementRequest
    # Проверки:
    # 1. is_blocked(advertiser_id, "advertiser") → raise BlockedUserError
    # 2. proposed_price >= ChannelSettings.MIN_PRICE_PER_POST → raise ValidationError
    # 3. channel существует и is_active=True → raise ChannelNotFoundError
    # Вызвать placement_repo.create()

async def owner_accept(placement_id, owner_id, final_price=None, final_schedule=None) -> PlacementRequest
    # Проверки: заявка существует, принадлежит каналу owner_id, статус==PENDING_OWNER, expires_at не истёк
    # placement_repo.accept()
    # notification_service.notify(advertiser_id, "placement_accepted")

async def owner_reject(placement_id, owner_id, rejection_reason: str) -> PlacementRequest
    # validate_rejection_reason(rejection_reason) → если невалидна: штраф репутации + raise ValidationError
    # placement_repo.reject()
    # billing_service.refund(advertiser_id, 100%)
    # notification_service.notify(advertiser_id, "placement_rejected")

async def owner_counter_offer(placement_id, owner_id, proposed_price=None, proposed_schedule=None) -> PlacementRequest
    # Проверка: counter_offer_count < 3
    # placement_repo.counter_offer() → если None: raise MaxCounterOffersError
    # notification_service.notify(advertiser_id, "counter_offer")

async def advertiser_accept_counter(placement_id, advertiser_id) -> PlacementRequest
    # Проверка: статус==COUNTER_OFFER, заявка принадлежит advertiser_id
    # status → PENDING_PAYMENT

async def advertiser_cancel(placement_id, advertiser_id) -> PlacementRequest
    # Логика штрафов по статусу:
    # PENDING_OWNER или PENDING_PAYMENT:
    #   → refund 100%, reputation delta = -5 (CANCEL_BEFORE)
    # ESCROW:
    #   → refund 50%, reputation delta = -20 (CANCEL_AFTER)
    # Проверить систематические отмены:
    #   count_cancellations_in_30_days() >= 3 → ещё -20 (CANCEL_SYSTEMATIC)
    # billing_service.refund() или partial_refund()
    # reputation_service.on_advertiser_cancel()

async def process_payment(placement_id, advertiser_id) -> PlacementRequest
    # Проверка: статус==PENDING_PAYMENT, advertiser_id совпадает
    # billing_service.freeze_escrow_for_placement()
    # placement_repo.set_escrow(escrow_transaction_id)

async def process_publication_success(placement_id, published_at=None) -> PlacementRequest
    # placement_repo.set_published()
    # billing_service.release_escrow_for_placement() → 80%/20%
    # payout_service.request_payout_for_placement()
    # reputation_service.on_publication(advertiser_id, owner_id)

async def process_publication_failure(placement_id, reason) -> PlacementRequest
    # status → FAILED → REFUNDED
    # billing_service.refund(advertiser_id, 100%)
    # Репутация без изменений (техошибка)

async def auto_expire(placement_id: int) -> PlacementRequest
    # Вызывается Celery
    # status → CANCELLED, refund 100%
    # notification_service.notify(advertiser_id, "placement_expired")

async def validate_rejection_reason(reason: str) -> bool
    # len(reason) >= 10
    # re.search(r'[а-яёa-z]', reason, re.IGNORECASE)
    # not in blacklist ("asdfgh", "aaaaaa", "123456" и т.п.)
```

### 3.4 ReputationService (создаётся в Этапе 2)

```python
# Константы
DELTA_PUBLICATION      = +1.0
DELTA_REVIEW_5STAR     = +2.0
DELTA_REVIEW_4STAR     = +1.0
DELTA_REVIEW_3STAR     = 0.0
DELTA_REVIEW_2STAR     = -1.0
DELTA_REVIEW_1STAR     = -2.0
DELTA_CANCEL_BEFORE    = -5.0
DELTA_CANCEL_AFTER     = -20.0
DELTA_CANCEL_SYSTEMATIC = -20.0
DELTA_REJECT_INVALID_1 = -10.0
DELTA_REJECT_INVALID_2 = -15.0
DELTA_REJECT_INVALID_3 = -20.0
DELTA_REJECT_FREQUENT  = -5.0
DELTA_RECOVERY_30DAYS  = +5.0
SCORE_MIN = 0.0
SCORE_MAX = 10.0
SCORE_AFTER_BAN = 2.0
BAN_DURATION_DAYS = 7
PERMANENT_BAN_VIOLATIONS = 5

async def on_publication(advertiser_id, owner_id, placement_request_id) -> None
    # +1.0 advertiser_score
    # +1.0 owner_score

async def on_review(reviewer_id, reviewed_id, reviewer_role, stars, placement_request_id) -> None
    # Определить роль reviewed_id (обратная от reviewer_role)
    # Применить дельту по шкале звёзд

async def on_advertiser_cancel(advertiser_id, placement_request_id, after_confirmation) -> None
    # after_confirmation=True → CANCEL_AFTER (-20)
    # after_confirmation=False → CANCEL_BEFORE (-5)
    # Проверить count_cancellations_in_30_days >= 3 → ещё CANCEL_SYSTEMATIC (-20)

async def on_invalid_rejection(owner_id, placement_request_id) -> None
    # streak = count_invalid_rejections_streak(owner_id)
    # streak == 1 → REJECT_INVALID_1 (-10)
    # streak == 2 → REJECT_INVALID_2 (-15)
    # streak >= 3 → REJECT_INVALID_3 (-20) + бан 7 дней
    # При бане: set_block(owner_id, "owner", now()+7days)

async def on_frequent_rejections(owner_id: int) -> None
    # REJECT_FREQUENT (-5)

async def on_30days_clean(user_id: int, role: str) -> None
    # RECOVERY_30DAYS (+5)

async def check_and_unblock(user_id: int) -> bool
    # Если blocked_until < now():
    #   снять блокировку
    #   сбросить score до SCORE_AFTER_BAN (2.0)
    #   записать BAN_RESET
    #   return True

async def is_blocked(user_id: int, role: str) -> bool
async def get_score(user_id: int, role: str) -> float
    # 5.0 если записи нет

async def _apply_delta(user_id, role, delta, action, placement_request_id=None, comment=None) -> float
    # Приватный. Применить дельту.
    # new_score = clamp(current + delta, SCORE_MIN, SCORE_MAX)
    # reputation_repo.update_score()
    # reputation_repo.add_history()
    # Если new_score <= 0 или violations >= PERMANENT_BAN_VIOLATIONS → перманентная блокировка
    # return new_score
```

### 3.5 XPService (`src/core/services/xp_service.py`) — НЕ ТРОГАТЬ

```python
# 7 уровней (0-6), отдельно для advertiser и owner
LEVELS = {
    0: {"name": "Новичок",    "xp_required": 0},
    1: {"name": "Начинающий", "xp_required": 100},
    2: {"name": "Активный",   "xp_required": 300},
    3: {"name": "Опытный",    "xp_required": 700},
    4: {"name": "Эксперт",    "xp_required": 1500},
    5: {"name": "Мастер",     "xp_required": 3000},
    6: {"name": "Легенда",    "xp_required": 6000},
}

async def add_xp(user_id: int, role: str, amount: int) -> tuple[int, int, bool]
    # Вернуть (new_xp, new_level, leveled_up)

async def get_xp_for_next_level(current_xp: int, current_level: int) -> int
async def check_level_up(user_id: int, role: str) -> bool
```

### 3.6 BadgeService (`src/core/services/badge_service.py`) — НЕ ТРОГАТЬ

```python
async def check_and_award(user_id: int, role: str, event_type: str, value: int) -> list[Badge]
    # Проверить все возможные бейджи для события
    # Наградить незаработанные

async def get_user_badges(user_id: int) -> list[UserBadge]
async def get_available_badges(role: str) -> list[Badge]
```

### 3.7 NotificationService (`src/core/services/notification_service.py`)

```python
async def notify(user_id: int, event_type: str, data: dict = None) -> None
    # Отправить уведомление через Telegram Bot API
    # Записать в notifications таблицу

async def notify_owner_new_request(owner_id: int, placement_id: int) -> None
async def notify_advertiser_accepted(advertiser_id: int, placement_id: int) -> None
async def notify_advertiser_rejected(advertiser_id: int, placement_id: int, reason: str) -> None
async def notify_advertiser_counter(advertiser_id: int, placement_id: int) -> None
async def notify_publication_success(advertiser_id: int, owner_id: int, placement_id: int) -> None
async def notify_publication_failed(advertiser_id: int, placement_id: int) -> None
async def notify_plan_expiring(user_id: int, days_left: int) -> None
async def get_unread(user_id: int) -> list[Notification]
async def mark_read(notification_id: int) -> None
```

### 3.8 AnalyticsService (`src/core/services/analytics_service.py`)

```python
# Для рекламодателя
async def get_advertiser_stats(advertiser_id: int) -> dict
    # active_campaigns, total_placements, total_reach
    # avg_cpm, avg_ctr, avg_roi
    # top_channels_by_ctr

# Для владельца
async def get_owner_stats(owner_id: int) -> dict
    # monthly_earnings, total_earnings, pending_payout
    # accepted_count, rejected_count, acceptance_rate

# Общие
async def get_campaign_stats(campaign_id: int) -> dict
async def get_channel_performance(channel_id: int) -> dict
async def calculate_cpm(campaign_id: int) -> float
async def calculate_ctr(campaign_id: int) -> float
async def calculate_roi(campaign_id: int) -> float
```

### 3.9 MistralAIService (`src/core/services/mistral_ai_service.py`)

```python
async def generate_ad_text(topic: str, channel_description: str, tone: str) -> list[str]
    # Вернуть 3 варианта текста
    # Модель из settings.AI_MODEL

async def classify_channel_topic(description: str, title: str) -> tuple[str, float]
    # Вернуть (topic, confidence)

async def filter_content_level3(text: str) -> tuple[bool, str]
    # Вернуть (is_allowed, reason_if_denied)
```

### 3.10 ContentFilter (`src/utils/content_filter/filter.py`)

3-уровневая фильтрация контента:

```
L1 — regex: быстрая проверка стоп-слов (stopwords_ru.json + кастомный список)
     Пороги: HIGH_RISK (≥3 совпадений → блокировать), MEDIUM_RISK (1-2 → на проверку L2)

L2 — pymorphy3: нормализация слов, проверка корней
     Обрабатывает словоформы и падежи

L3 — LLM: пограничные случаи, семантический анализ
     Вызывается только если L1+L2 неопределённы
     Модель: settings.AI_MODEL
```

### 3.11 PayoutService (`src/core/services/payout_service.py`)

```python
async def request_payout(owner_id: int, amount: Decimal) -> Payout
    # amount >= MIN_PAYOUT (100 кр)
    # Payout(status=PENDING)

async def request_payout_for_placement(owner_id, amount, placement_request_id) -> Payout
    # (добавлено в Этапе 2)

async def process_payout(payout_id: int) -> Payout
    # PENDING → PROCESSING → PAID/FAILED

async def get_available_amount(owner_id: int) -> Decimal
    # Сумма из успешных размещений, ещё не выплаченных

async def get_history(owner_id: int, limit=20) -> list[Payout]
```

### 3.12 UserRoleService (`src/core/services/user_role_service.py`)

```python
async def set_role(user_id: int, role: str) -> User
async def add_role(user_id: int, new_role: str) -> User
    # new + advertiser → advertiser
    # advertiser + owner → both
    # owner + advertiser → both

async def remove_role(user_id: int, remove: str) -> User
    # both - advertiser → owner
    # both - owner → advertiser

async def get_effective_role(user_id: int) -> str
async def can_create_campaign(user_id: int) -> bool
async def can_register_channel(user_id: int) -> bool
```

---

## 4. Бизнес-правила: сводная таблица

### 4.1 Арбитраж и таймеры

| Событие | Таймер | Действие при истечении |
|---------|--------|----------------------|
| Ответ владельца на заявку | 24 часа | Авто-отмена, refund 100%, уведомление advertiser |
| Оплата после принятия | 24 часа | Заявка аннулируется, уведомление owner |
| Контр-предложение | 24 часа | Авто-отмена раунда |
| Максимум раундов контр-предложений | 3 раунда | После 3-го: только принять/отклонить |
| Retry публикации при ошибке | 1 час | После retry: FAILED + refund 100% |

### 4.2 Возвраты

| Сценарий | % возврата | Δ Репутация advertiser |
|----------|------------|----------------------|
| Владелец отклонил | 100% | 0 |
| Advertiser отменил (до эскроу) | 100% | −5 |
| Advertiser отменил (после эскроу) | 50% | −20 |
| 3 отмены за 30 дней | — | ещё −20 + ⚠️ предупреждение |
| Техошибка (бот удалён, канал заблокирован) | 100% | 0 |
| Таймаут ответа владельца | 100% | 0 |
| Таймаут оплаты | 100% | 0 |

### 4.3 Штрафы репутации owner

| Действие | Δ Репутация | Последствия |
|----------|-------------|-------------|
| Невалидный отказ (1й) | −10 | — |
| Невалидный отказ (2й подряд) | −15 | — |
| Невалидный отказ (3й подряд) | −20 | Бан 7 дней |
| Частые отказы (>50%) | −5 | — |
| Отказ с валидной причиной | 0 | — |

### 4.4 Восстановление репутации

| Событие | Δ Репутация | Кому |
|---------|-------------|------|
| Успешная публикация | +1 | advertiser + owner |
| Отзыв 5⭐ | +2 | получатель отзыва |
| Отзыв 4⭐ | +1 | — |
| Отзыв 3⭐ | 0 | — |
| Отзыв 2⭐ | −1 | — |
| Отзыв 1⭐ | −2 | — |
| 30 дней без нарушений | +5 | — |
| После бана (сброс) | → 2.0 | после окончания бана |

### 4.5 Блокировки

| Условие | Тип блокировки | Продолжительность |
|---------|----------------|-------------------|
| 3й невалидный отказ подряд | owner_blocked | 7 дней |
| Score ≤ 0 | role_blocked | Перманентная |
| violations ≥ 5 | role_blocked | Перманентная |
| is_banned (глобально) | full_ban | Перманентная (admin) |

### 4.6 Валидация rejection_reason

```python
# Правила валидной причины отклонения:
min_length = 10 символов
must_contain = re.search(r'[а-яёa-z]', reason, re.IGNORECASE)
blacklist = ["asdfgh", "aaaaaa", "123456", "qwerty", "нет", "no", "не хочу"]
# Невалидная причина → ReputationService.on_invalid_rejection()
```

### 4.7 B2B пакеты

| Пакет | Цена | Каналов | Бюджет/канал | Ожидаемый охват | Срок |
|-------|------|---------|--------------|-----------------|------|
| Стартап | 1500 кр | 5 | 300 кр | ~25 000 | 7 дней |
| Бизнес | 5000 кр | 10 | 500 кр | ~60 000 | 14 дней |
| Премиум | 25 000 кр | 25 | 1000 кр | ~200 000 | 30 дней |

### 4.8 Тарифные лимиты

| Параметр | Free | Start | Pro | Agency |
|----------|------|-------|-----|--------|
| Активных кампаний | 1 | 3 | 10 | Unlimited |
| AI запросов/мес | 5 | 30 | 100 | Unlimited |
| Каналов в кампании | 3 | 10 | 50 | Unlimited |
| Аналитика (дни) | 7 | 30 | 90 | 365 |
| B2B доступ | ❌ | ❌ | ✅ | ✅ |

---

## 5. Исключения (`src/core/exceptions.py`)

```python
class RekHarborError(Exception): ...           # Базовое
class InsufficientFundsError(RekHarborError): ...
class BlockedUserError(RekHarborError): ...
class ChannelNotFoundError(RekHarborError): ...
class PlacementNotFoundError(RekHarborError): ...
class MaxCounterOffersError(RekHarborError): ... # counter_offer_count >= 3
class ValidationError(RekHarborError): ...      # невалидные данные (rejection_reason и т.п.)
class PlacementExpiredError(RekHarborError): ... # expires_at истёк
class PermissionError(RekHarborError): ...      # не владелец канала / не advertiser
```
