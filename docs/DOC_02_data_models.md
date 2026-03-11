# DOC-02: Модели данных

**RekHarborBot — Техническая документация v3.0**  
**Дата:** 2026-03-10 | Все поля, типы, ограничения, связи

---

## Соглашения

- Все модели наследуют от `Base` (`src/db/base.py`, `DeclarativeBase`)
- Все временные поля — `DateTime(timezone=True)`
- `created_at` / `updated_at` — во всех основных моделях
- FK с `ondelete="CASCADE"` если запись бессмысленна без родителя
- FK с `ondelete="SET NULL"` если запись сохраняет смысл без родителя
- `Mapped[X]` + `mapped_column()` — стиль SQLAlchemy 2.0

---

## 1. User (`src/db/models/user.py`)

Центральная модель. Один пользователь = один Telegram аккаунт.

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `telegram_id` | BigInteger UNIQUE | No | — | Telegram user_id |
| `username` | String(64) | Yes | None | @username без @ |
| `first_name` | String(128) | No | — | Имя в Telegram |
| `last_name` | String(128) | Yes | None | — |
| `role` | String(20) | No | `"new"` | new/advertiser/owner/both/admin |
| `credits` | Numeric(12,2) | No | 0.00 | Баланс кредитов |
| `plan` | String(20) | No | `"free"` | free/start/pro/agency |
| `plan_expires_at` | DateTime | Yes | None | Дата окончания тарифа |
| `plan_expiry_notified_at` | DateTime | Yes | None | Когда отправлено уведомление |
| `ai_provider` | String(50) | Yes | None | Провайдер AI для пользователя |
| `ai_model` | String(100) | Yes | None | Конкретная модель |
| `ai_requests_count` | Integer | No | 0 | Счётчик AI запросов |
| `language_code` | String(10) | Yes | None | Код языка Telegram |
| `russian_score` | Float | Yes | None | Вероятность русскоязычного пользователя |
| `is_banned` | Boolean | No | False | Глобальная блокировка |
| `ban_reason` | String(500) | Yes | None | — |
| `notifications_enabled` | Boolean | No | True | Глобальный toggle уведомлений |
| `login_streak` | Integer | No | 0 | Дней подряд в боте |
| `last_login_date` | Date | Yes | None | Дата последнего входа |
| `referral_code` | String(20) UNIQUE | Yes | None | Реферальный код пользователя |
| `referred_by_id` | Integer FK→users.id | Yes | None | Кто пригласил |
| `complaint_count` | Integer | No | 0 | Жалобы на пользователя |
| `is_blacklisted` | Boolean | No | False | Чёрный список |
| `blacklist_reason` | String(500) | Yes | None | — |
| **XP и уровни (геймификация)** | | | | |
| `advertiser_xp` | Integer | No | 0 | XP рекламодателя |
| `owner_xp` | Integer | No | 0 | XP владельца |
| `advertiser_level` | Integer | No | 0 | Уровень рекламодателя (0-6) |
| `owner_level` | Integer | No | 0 | Уровень владельца (0-6) |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

**⚠️ XP/levels не связаны с ReputationScore — разные системы.**

**Relationships:**
- `campaigns` → list[Campaign] (back_populates)
- `telegram_chats` → list[TelegramChat] (каналы владельца)
- `badges` → list[UserBadge]
- `payouts` → list[Payout]
- `reputation_score` → ReputationScore (one-to-one)
- `referred_users` → list[User] (self-referential)

---

## 2. TelegramChat (`src/db/models/analytics.py`)

Telegram-канал в базе. Создаётся при парсинге или opt-in регистрации.

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `telegram_id` | BigInteger UNIQUE | No | — | Telegram channel id |
| `username` | String(64) UNIQUE | Yes | None | @handle |
| `title` | String(255) | No | — | Название канала |
| `description` | String(1000) | Yes | None | Описание |
| `owner_id` | Integer FK→users.id | Yes | None | Владелец (SET NULL) |
| `member_count` | Integer | No | 0 | Подписчиков |
| `avg_views` | Integer | No | 0 | Среднее просмотров |
| `last_er` | Float | Yes | None | Engagement Rate (%) |
| `rating` | Float | No | 5.0 | Рейтинг канала (0-10) |
| `topic` | String(100) | Yes | None | Тематика (AI классификация) |
| `subcategory` | String(100) | Yes | None | Подтематика |
| `language` | String(10) | Yes | None | Язык контента |
| `is_verified` | Boolean | No | False | Верифицирован модератором |
| `is_active` | Boolean | No | True | Активен в каталоге |
| `is_opt_in` | Boolean | No | False | Добровольная регистрация |
| `bot_is_admin` | Boolean | No | False | Бот — администратор |
| `bot_added_at` | DateTime | Yes | None | Когда бот добавлен |
| `last_parsed_at` | DateTime | Yes | None | Последний парсинг |
| `llm_classification_topic` | String(100) | Yes | None | LLM топик |
| `llm_classification_confidence` | Float | Yes | None | Уверенность классификации |
| `llm_classified_at` | DateTime | Yes | None | — |
| `price_per_post` | Numeric(10,2) | Yes | None | Цена установленная владельцем (устаревшее) |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

**Relationships:**
- `owner` → User
- `settings` → ChannelSettings (one-to-one)
- `placement_requests` → list[PlacementRequest]
- `snapshots` → list[ChatSnapshot]
- `mediakit` → ChannelMediakit (one-to-one)
- `channel_rating` → ChannelRating (one-to-one)

---

## 3. Campaign (`src/db/models/campaign.py`)

Рекламная кампания рекламодателя.

### Enum CampaignStatus

```python
class CampaignStatus(str, Enum):
    DRAFT      = "draft"       # Черновик, не запущена
    QUEUED     = "queued"      # В очереди на обработку
    RUNNING    = "running"     # Активна, идёт рассылка
    SCHEDULED  = "scheduled"   # Запланирована на конкретное время
    DONE       = "done"        # Завершена успешно
    ERROR      = "error"       # Ошибка исполнения
    PAUSED     = "paused"      # Поставлена на паузу
    CANCELLED  = "cancelled"   # Отменена пользователем
    MODERATION = "moderation"  # На модерации
```

### Enum CampaignType (добавлен в Этапе 1)

```python
class CampaignType(str, Enum):
    BROADCAST = "broadcast"  # Старый тип: массовая рассылка
    PLACEMENT = "placement"  # Новый тип: размещение через арбитраж
```

### Поля Campaign

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `advertiser_id` | Integer FK→users.id | No | — | CASCADE |
| `title` | String(255) | No | — | Название кампании |
| `text` | Text | No | — | Текст объявления |
| `topic_header_image_url` | String(512) | Yes | None | Изображение заголовка |
| `status` | CampaignStatus | No | DRAFT | — |
| `type` | CampaignType | No | BROADCAST | Тип кампании ✅ Этап 1 |
| `placement_request_id` | Integer FK→placement_requests.id | Yes | None | SET NULL ✅ Этап 1 |
| `budget` | Numeric(12,2) | Yes | None | Бюджет кампании |
| `spent` | Numeric(12,2) | No | 0.00 | Потрачено |
| `ctr` | Float | Yes | None | CTR (%) |
| `views_total` | Integer | No | 0 | Сумма просмотров |
| `clicks_total` | Integer | No | 0 | Сумма кликов |
| `channels_count` | Integer | No | 0 | Количество каналов |
| `target_category` | String(100) | Yes | None | Целевая тематика |
| `target_subcategory` | String(100) | Yes | None | — |
| `scheduled_at` | DateTime | Yes | None | Запланированное время |
| `started_at` | DateTime | Yes | None | Фактическое начало |
| `finished_at` | DateTime | Yes | None | Фактическое завершение |
| `meta_json` | JSON | Yes | None | Доп. метаданные (AI варианты и др.) |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

---

## 4. PlacementRequest (`src/db/models/placement_request.py`) ✅ Этап 1

Заявка на размещение рекламы. Центральная сущность нового флоу.

### Enum PlacementStatus

```python
class PlacementStatus(str, Enum):
    PENDING_OWNER   = "pending_owner"    # Ожидает решения владельца (24ч)
    COUNTER_OFFER   = "counter_offer"    # Владелец сделал контр-предложение
    PENDING_PAYMENT = "pending_payment"  # Принято, ждём оплаты (24ч)
    ESCROW          = "escrow"           # Средства заблокированы
    PUBLISHED       = "published"        # Успешно опубликовано
    FAILED          = "failed"           # Ошибка публикации
    REFUNDED        = "refunded"         # Средства возвращены
    CANCELLED       = "cancelled"        # Отменено
```

### Жизненный цикл

```
pending_owner ──► counter_offer ──► pending_owner (следующий раунд, макс 3)
     │                                     │
     │ (accept)                            │ (accept counter)
     ▼                                     ▼
pending_payment ◄────────────────────────────
     │
     │ (pay)
     ▼
  escrow ──► published
     │
     └──► failed ──► refunded
     
(любой статус) ──► cancelled
```

### Поля PlacementRequest

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `advertiser_id` | Integer FK→users.id | No | — | CASCADE |
| `campaign_id` | Integer FK→campaigns.id | No | — | CASCADE |
| `channel_id` | Integer FK→telegram_chats.id | No | — | CASCADE |
| `proposed_price` | Numeric(10,2) | No | — | Цена предложенная advertiser |
| `final_price` | Numeric(10,2) | Yes | None | Итоговая после арбитража |
| `proposed_schedule` | DateTime | Yes | None | Желаемое время публикации |
| `final_schedule` | DateTime | Yes | None | Согласованное время |
| `proposed_frequency` | Integer | Yes | None | Частота постов (пакеты) |
| `final_text` | Text | No | — | Финальный текст рекламы |
| `status` | PlacementStatus | No | PENDING_OWNER | — |
| `rejection_reason` | String(500) | Yes | None | Причина отклонения (мин 10 символов, должна содержать буквы) |
| `counter_offer_count` | Integer | No | 0 | Раундов арбитража (макс 3) |
| `last_counter_at` | DateTime | Yes | None | Время последнего контр-предложения |
| `escrow_transaction_id` | Integer FK→transactions.id | Yes | None | SET NULL |
| `expires_at` | DateTime | No | — | Дедлайн ответа (+24ч от создания/контр-предложения) |
| `published_at` | DateTime | Yes | None | Реальное время публикации |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

**Индексы:** advertiser_id, channel_id, campaign_id, status, expires_at, created_at

---

## 5. ChannelSettings (`src/db/models/channel_settings.py`) ✅ Этап 1

Настройки монетизации канала. PK = `channel_id` (строго one-to-one).

### Системные константы (class-level, неизменяемые)

```python
MIN_PRICE_PER_POST    = Decimal("100.00")  # Минимум 100 кредитов
MAX_PACKAGE_DISCOUNT  = 50                 # Скидка пакета макс 50%
MIN_SUBSCRIPTION_DAYS = 7                  # Минимум 7 дней подписки
MAX_SUBSCRIPTION_DAYS = 365               # Максимум 1 год
MAX_POSTS_PER_DAY     = 5                  # Рекламных постов в день макс 5
MAX_POSTS_PER_WEEK    = 35                 # В неделю макс 35
MIN_HOURS_BETWEEN_POSTS = 4               # Между постами минимум 4 часа
PLATFORM_COMMISSION   = Decimal("0.20")   # 20% комиссия платформы
```

### Поля ChannelSettings

| Поле | Тип | Nullable | Default | Ограничение |
|------|-----|----------|---------|-------------|
| `channel_id` | Integer PK FK→telegram_chats.id | No | — | CASCADE |
| `owner_id` | Integer FK→users.id | No | — | CASCADE |
| `price_per_post` | Numeric(10,2) | No | 500.00 | ≥ MIN_PRICE_PER_POST |
| `daily_package_enabled` | Boolean | No | True | — |
| `daily_package_max` | Integer | No | 2 | 1–5 |
| `daily_package_discount` | Integer | No | 20 | 0–50 |
| `weekly_package_enabled` | Boolean | No | True | — |
| `weekly_package_max` | Integer | No | 5 | 1–35 |
| `weekly_package_discount` | Integer | No | 30 | 0–50 |
| `subscription_enabled` | Boolean | No | True | — |
| `subscription_min_days` | Integer | No | 7 | 7–365 |
| `subscription_max_days` | Integer | No | 365 | 7–365 |
| `subscription_max_per_day` | Integer | No | 1 | 1–5 |
| `publish_start_time` | Time | No | 09:00 | — |
| `publish_end_time` | Time | No | 21:00 | — |
| `break_start_time` | Time | Yes | 14:00 | Перерыв (начало) |
| `break_end_time` | Time | Yes | 15:00 | Перерыв (конец) |
| `auto_accept_enabled` | Boolean | No | False | Авто-принятие заявок |
| `auto_accept_min_price` | Numeric(10,2) | Yes | None | Мин цена для авто-принятия |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

**Индекс:** owner_id

---

## 6. ReputationScore (`src/db/models/reputation_score.py`) ✅ Этап 1

Система доверия пользователя. PK = `user_id` (строго one-to-one). **НЕ путать с XP/levels.**

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `user_id` | Integer PK FK→users.id | No | — | CASCADE |
| `advertiser_score` | Float | No | 5.0 | Надёжность как advertiser (0.0–10.0) |
| `owner_score` | Float | No | 5.0 | Надёжность как owner (0.0–10.0) |
| `advertiser_violations` | Integer | No | 0 | Нарушений как advertiser |
| `owner_violations` | Integer | No | 0 | Нарушений как owner |
| `is_advertiser_blocked` | Boolean | No | False | Заблокирован как advertiser |
| `is_owner_blocked` | Boolean | No | False | Заблокирован как owner |
| `advertiser_blocked_until` | DateTime | Yes | None | Срок блокировки advertiser |
| `owner_blocked_until` | DateTime | Yes | None | Срок блокировки owner |
| `block_reason` | String(500) | Yes | None | Причина блокировки |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

**Ключевые правила:**
- Диапазон: 0.0 – 10.0
- Стартовое значение: 5.0
- После 7-дневного бана: сброс до 2.0
- 5+ нарушений: перманентная блокировка
- Пользователь с двумя ролями (`both`) может быть заблокирован как owner, оставаясь активным как advertiser

---

## 7. ReputationHistory (`src/db/models/reputation_history.py`) ✅ Этап 1

Полная история изменений репутации.

### Enum ReputationAction (16 значений)

```python
class ReputationAction(str, Enum):
    PUBLICATION        = "publication"        # +1.0 за успешную публикацию
    REVIEW_5STAR       = "review_5star"        # +2.0
    REVIEW_4STAR       = "review_4star"        # +1.0
    REVIEW_3STAR       = "review_3star"        # 0.0
    REVIEW_2STAR       = "review_2star"        # -1.0
    REVIEW_1STAR       = "review_1star"        # -2.0
    CANCEL_BEFORE      = "cancel_before"       # -5.0  (до подтверждения)
    CANCEL_AFTER       = "cancel_after"        # -20.0 (после подтверждения)
    CANCEL_SYSTEMATIC  = "cancel_systematic"   # -20.0 (3 отмены за 30 дней)
    REJECT_INVALID_1   = "reject_invalid_1"    # -10.0 (1й невалидный отказ)
    REJECT_INVALID_2   = "reject_invalid_2"    # -15.0 (2й)
    REJECT_INVALID_3   = "reject_invalid_3"    # -20.0 + бан 7 дней (3й)
    REJECT_FREQUENT    = "reject_frequent"     # -5.0  (>50% отказов)
    RECOVERY_30DAYS    = "recovery_30days"     # +5.0  (30 дней без нарушений)
    BAN_RESET          = "ban_reset"           # сброс до 2.0 после бана
    INITIAL_MIGRATION  = "initial_migration"   # служебная запись
```

### Поля ReputationHistory

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `user_id` | Integer FK→users.id | No | — | CASCADE |
| `placement_request_id` | Integer FK→placement_requests.id | Yes | None | SET NULL |
| `action` | ReputationAction | No | — | Тип события |
| `delta` | Float | No | — | Изменение (+/-) |
| `new_score` | Float | No | — | Score после изменения |
| `role` | String(20) | No | — | "advertiser" или "owner" |
| `comment` | String(500) | Yes | None | Контекст |
| `created_at` | DateTime | No | now() | — |

**Индексы:** user_id, placement_request_id, created_at, role

---

## 8. MailingLog (`src/db/models/mailing_log.py`)

Запись о каждой попытке публикации поста.

### Enum MailingStatus

```python
class MailingStatus(str, Enum):
    PENDING    = "pending"
    SENT       = "sent"
    FAILED     = "failed"
    SKIPPED    = "skipped"
    CANCELLED  = "cancelled"
    RETRY      = "retry"
    TIMEOUT    = "timeout"
    BOUNCED    = "bounced"
    BLOCKED    = "blocked"
```

### Поля MailingLog

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `campaign_id` | Integer FK→campaigns.id | No | — | CASCADE |
| `channel_id` | Integer FK→telegram_chats.id | No | — | CASCADE |
| `placement_request_id` | Integer FK→placement_requests.id | Yes | None | SET NULL ✅ Этап 1 |
| `status` | MailingStatus | No | PENDING | — |
| `message_id` | BigInteger | Yes | None | Telegram message_id после отправки |
| `error_message` | Text | Yes | None | Текст ошибки |
| `views_count` | Integer | No | 0 | Просмотры (если доступно) |
| `clicks_count` | Integer | No | 0 | Клики по ссылкам |
| `sent_at` | DateTime | Yes | None | Фактическое время отправки |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

---

## 9. Transaction (`src/db/models/transaction.py`)

Финансовые операции с балансом.

### Enum TransactionType

```python
class TransactionType(str, Enum):
    TOPUP           = "topup"            # Пополнение
    WITHDRAWAL      = "withdrawal"       # Вывод средств
    PAYMENT         = "payment"          # Оплата кампании
    REFUND          = "refund"           # Возврат
    ESCROW_FREEZE   = "escrow_freeze"    # Блокировка для PlacementRequest
    ESCROW_RELEASE  = "escrow_release"   # Разблокировка → владельцу
    COMMISSION      = "commission"       # Комиссия платформы
    BONUS           = "bonus"            # Бонусные кредиты
```

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `user_id` | Integer FK→users.id | No | — | CASCADE |
| `type` | TransactionType | No | — | — |
| `amount` | Numeric(12,2) | No | — | Сумма (всегда положительная) |
| `balance_before` | Numeric(12,2) | No | — | Баланс до операции |
| `balance_after` | Numeric(12,2) | No | — | Баланс после |
| `description` | String(500) | Yes | None | Описание операции |
| `reference_id` | Integer | Yes | None | ID связанного объекта |
| `reference_type` | String(50) | Yes | None | Тип связанного объекта |
| `created_at` | DateTime | No | now() | — |

---

## 10. Payout (`src/db/models/payout.py`)

Запрос на выплату для владельца канала.

### Enum PayoutStatus

```python
class PayoutStatus(str, Enum):
    PENDING    = "pending"     # Ожидает обработки
    PROCESSING = "processing"  # В обработке
    PAID       = "paid"        # Выплачено
    FAILED     = "failed"      # Ошибка выплаты
    CANCELLED  = "cancelled"   # Отменено
```

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `owner_id` | Integer FK→users.id | No | — | CASCADE |
| `placement_id` | Integer FK→placement_requests.id | Yes | None | SET NULL |
| `amount` | Numeric(12,2) | No | — | Сумма выплаты |
| `status` | PayoutStatus | No | PENDING | — |
| `payment_method` | String(50) | Yes | None | Метод выплаты |
| `payment_details` | String(500) | Yes | None | Реквизиты |
| `processed_at` | DateTime | Yes | None | Время обработки |
| `created_at` | DateTime | No | now() | — |
| `updated_at` | DateTime | No | now() | onupdate |

---

## 11. Review (`src/db/models/review.py`)

Отзыв после завершения размещения.

### Enum ReviewerRole

```python
class ReviewerRole(str, Enum):
    ADVERTISER = "advertiser"
    OWNER      = "owner"
```

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `reviewer_id` | Integer FK→users.id | No | — | Кто оставил отзыв |
| `reviewed_id` | Integer FK→users.id | No | — | О ком отзыв |
| `placement_id` | Integer FK→placement_requests.id | Yes | None | SET NULL |
| `reviewer_role` | ReviewerRole | No | — | Роль рецензента |
| `stars` | Integer | No | — | 1–5 |
| `comment` | String(1000) | Yes | None | Текст отзыва |
| `created_at` | DateTime | No | now() | — |

---

## 12. Badge / UserBadge (`src/db/models/badge.py`)

Геймификация: достижения пользователей.

| Поле (Badge) | Тип | Описание |
|-------------|-----|----------|
| `id` | Integer PK | — |
| `code` | String(50) UNIQUE | Код бейджа |
| `name` | String(100) | Название |
| `description` | String(500) | Описание |
| `icon` | String(10) | Эмодзи |
| `xp_reward` | Integer | Награда XP |
| `role` | String(20) | advertiser/owner/both |
| `trigger_type` | String(50) | Тип триггера |
| `trigger_value` | Integer | Порог |

| Поле (UserBadge) | Тип | Описание |
|----------------|-----|----------|
| `id` | Integer PK | — |
| `user_id` | Integer FK→users.id | CASCADE |
| `badge_id` | Integer FK→badges.id | CASCADE |
| `earned_at` | DateTime | Когда получен |

---

## 13. ChannelRating (`src/db/models/channel_rating.py`)

Рейтинг качества канала (отдельно от репутации владельца).

| Поле | Тип | Nullable | Default | Описание |
|------|-----|----------|---------|----------|
| `id` | Integer PK | No | autoincrement | — |
| `channel_id` | Integer FK→telegram_chats.id UNIQUE | No | — | One-to-one |
| `overall_score` | Float | No | 5.0 | Общий рейтинг (0-10) |
| `content_quality` | Float | No | 5.0 | Качество контента |
| `audience_quality` | Float | No | 5.0 | Качество аудитории |
| `reliability` | Float | No | 5.0 | Надёжность владельца |
| `review_count` | Integer | No | 0 | Количество отзывов |
| `fraud_score` | Float | No | 0.0 | Вероятность накрутки (0-1) |
| `updated_at` | DateTime | No | now() | onupdate |

**⚠️ ChannelRating ≠ ReputationScore:**
- `ChannelRating` — характеристика канала (качество контента, аудитории)
- `ReputationScore` — характеристика пользователя (надёжность контрагента)

---

## 14. B2BPackage (`src/db/models/b2b_package.py`)

Пакетные предложения для рекламодателей.

| Пакет | Цена | Каналов | Бюджет/канал | Охват | Срок |
|-------|------|---------|--------------|-------|------|
| Стартап | 1500 кр | 5 | 300 кр | ~25K | 7 дней |
| Бизнес | 5000 кр | 10 | 500 кр | ~60K | 14 дней |
| Премиум | 25000 кр | 25 | 1000 кр | ~200K | 30 дней |

---

## 15. Сводная таблица зависимостей FK

```
users (id)
  ├── campaigns.advertiser_id
  ├── telegram_chats.owner_id
  ├── placement_requests.advertiser_id
  ├── channel_settings.owner_id
  ├── reputation_scores.user_id (PK=user_id)
  ├── reputation_history.user_id
  ├── reviews.reviewer_id, reviewed_id
  ├── payouts.owner_id
  ├── transactions.user_id
  └── user_badges.user_id

telegram_chats (id)
  ├── placement_requests.channel_id
  ├── channel_settings.channel_id (PK=channel_id)
  ├── mailing_logs.channel_id
  ├── channel_rating.channel_id (UNIQUE)
  └── channel_mediakit.channel_id (UNIQUE)

campaigns (id)
  ├── placement_requests.campaign_id
  └── mailing_logs.campaign_id

placement_requests (id)
  ├── campaigns.placement_request_id (SET NULL)
  ├── mailing_logs.placement_request_id (SET NULL)
  ├── reputation_history.placement_request_id (SET NULL)
  ├── payouts.placement_id (SET NULL)
  └── reviews.placement_id (SET NULL)

transactions (id)
  └── placement_requests.escrow_transaction_id (SET NULL)
```
