# Отчёт о реализации Спринта 0 и Спринта 1

## Спринт 0 — Технический фундамент и публичный дашборд

### Статус: ✅ ЗАВЕРШЁН

| № | Задача | Файлы | Статус | Коммит |
|---|--------|-------|--------|--------|
| 0.1 | Миграция — поля opt-in в TelegramChat | `src/db/models/analytics.py`, `src/db/models/user.py`, `src/db/migrations/versions/20260306_120000_add_opt_in_fields_to_telegram_chat.py` | ✅ | 286ea05 |
| 0.2 | Фильтр bot_is_admin в рассыльщике | `src/db/repositories/chat_analytics.py`, `src/utils/telegram/sender.py` | ✅ | aaf974f |
| 0.3 | Хэндлер /add_channel | `src/bot/handlers/channel_owner.py`, `src/bot/states/channel_owner.py` | ✅ | 6043428 |
| 0.4 | Команда /stats | `src/bot/handlers/stats.py`, `src/core/services/analytics_service.py` | ✅ | c870e79 |
| 0.5 | FastAPI эндпоинт + Mini App страница | `src/api/routers/analytics.py`, `mini_app/src/pages/PlatformStats.tsx`, `mini_app/src/App.tsx` | ✅ | 99ae431 |
| 0.6 | Приветственное сообщение с метриками | `src/bot/handlers/start.py` | ✅ | db0d97b |

### Новые поля в TelegramChat:
- `bot_is_admin` (Boolean) — бот добавлен администратором
- `admin_added_at` (DateTime) — когда добавлен
- `owner_user_id` (BigInteger, FK) — владелец канала
- `price_per_post` (Numeric) — цена за пост
- `is_accepting_ads` (Boolean) — принимает рекламу

### Проверки:
- ✅ Ruff: 0 ошибок
- ✅ Mypy: 0 ошибок
- ✅ Ветка `sprint/0` слита в `develop`

---

## Спринт 1 — Полный цикл владельца канала

### Статус: ✅ ЗАВЕРШЁН

| № | Задача | Файлы | Статус | Коммит |
|---|--------|-------|--------|--------|
| 1.1 | Модель Payout + миграция | `src/db/models/payout.py`, `src/db/migrations/versions/20260307_100000_add_payout_model.py` | ✅ | 5b2dc61 |
| 1.2 | /my_channels и настройки канала | `src/bot/handlers/channel_owner.py`, `src/bot/states/channel_owner.py`, `src/db/repositories/chat_analytics.py` | ✅ | 46731b7 |
| 1.3 | Обработка входящих заявок | `src/db/models/mailing_log.py`, `src/bot/handlers/channel_owner.py`, `src/tasks/mailing_tasks.py`, `src/tasks/notification_tasks.py`, `src/tasks/celery_config.py` | ✅ | bf4dd4b |
| 1.4 | Сервис выплат (базовый) | `src/core/services/payout_service.py` | ✅ | 747a462 |
| 1.5 | Эскроу-механика | `src/core/services/billing_service.py` | ✅ | 680222d |
| 1.6 | Уведомления владельца | `src/tasks/notification_tasks.py` | ✅ | bf26476 |

### Новые модели:
- **Payout** — выплата владельцу (80% от цены поста)
  - `owner_id`, `channel_id`, `placement_id`
  - `amount`, `platform_fee`, `currency`, `status`
  - `wallet_address`, `tx_hash`, `paid_at`

### Новые статусы MailingStatus:
- `PENDING_APPROVAL` — ожидает одобрения владельца
- `REJECTED` — отклонено владельцем
- `QUEUED` — в очереди после одобрения

### Новые сервисы:
- **PayoutService**:
  - `calculate_payout()` — 80% владельцу, 20% платформе
  - `get_owner_balance()` — баланс к выплате
  - `create_pending_payout()` — создание выплаты
  - `process_payout()`, `mark_payout_paid()`, `cancel_payout()`

- **BillingService** (эскроу):
  - `freeze_funds()` — заморозка средств для кампании
  - `release_funds_for_placement()` — списание после публикации
  - `refund_frozen_funds()` — возврат при отмене

### Новые Celery задачи:
- `mailing:auto_approve_pending_placements` — автоодобрение через 24 часа
- `notifications:notify_owner_new_placement` — уведомление о заявке
- `notifications:notify_payout_created` — уведомление о создании выплаты
- `notifications:notify_payout_paid` — уведомление о выплате

### Проверки:
- ✅ Ruff: 0 ошибок
- ✅ Mypy: 0 ошибок
- ✅ Ветка `sprint/1` запушена в `origin/sprint/1`

---

## Зависимости для Спринта 2

### Реализовано:
- ✅ Модель `Payout` с `placement_id` (FK на `mailing_logs.id`)
- ✅ Статусы `PENDING_APPROVAL`/`REJECTED`/`QUEUED` для системы отзывов
- ✅ Эскроу-механика для защиты средств рекламодателя
- ✅ Уведомления владельца о заявках и выплатах

### Готово для Спринта 2:
- ✅ Модель Review может ссылаться на `placement_id`
- ✅ Система эскроу готова для интеграции с CryptoBot (Спринт 2)
- ✅ Базовая структура для CTR-трекинга и аналитики

---

## Файловая структура

```
src/
├── api/routers/
│   └── analytics.py              # Спринт 0: /stats/public endpoint
├── bot/handlers/
│   ├── channel_owner.py          # Спринт 0 + 1: /add_channel, /my_channels, approval
│   └── stats.py                  # Спринт 0: /stats command
├── bot/states/
│   └── channel_owner.py          # Спринт 0 + 1: FSM states
├── core/services/
│   ├── analytics_service.py      # Спринт 0: get_platform_stats()
│   ├── billing_service.py        # Спринт 1: escrow mechanism
│   └── payout_service.py         # Спринт 1: payout logic
├── db/models/
│   ├── analytics.py              # Спринт 0: opt-in fields
│   ├── mailing_log.py            # Спринт 1: new statuses
│   ├── payout.py                 # Спринт 1: Payout model
│   └── user.py                   # Спринт 0 + 1: relationships
├── db/repositories/
│   └── chat_analytics.py         # Спринт 0 + 1: get_by_owner_id(), get_chats_for_mailing()
├── db/migrations/versions/
│   ├── 20260306_120000_add_opt_in_fields_to_telegram_chat.py  # Спринт 0
│   ├── 20260307_100000_add_payout_model.py                    # Спринт 1
│   └── 20260307_120000_add_mailing_status_enum_values.py      # Спринт 1
├── tasks/
│   ├── celery_config.py          # Спринт 1: auto-approve task
│   ├── mailing_tasks.py          # Спринт 1: auto_approve_pending_placements
│   └── notification_tasks.py     # Спринт 1: payout notifications
└── utils/telegram/
    └── sender.py                 # Спринт 0: get_chats_for_campaign()

mini_app/src/pages/
└── PlatformStats.tsx             # Спринт 0: public dashboard
```

---

## Коммиты

### Спринт 0 (6 коммитов):
```
db0d97b feat(start): show platform metrics in welcome message
99ae431 feat(mini-app): add public PlatformStats page and /api/analytics/stats/public endpoint
c870e79 feat(stats): add /stats command and get_platform_stats() service method
6043428 feat(channel-owner): add /add_channel handler with bot admin verification
aaf974f feat(mailing): filter channels by bot_is_admin and is_accepting_ads
286ea05 feat(opt-in): add bot_is_admin fields to TelegramChat model and migration
```

### Спринт 1 (6 коммитов):
```
bf26476 feat(notifications): add payout notifications for channel owners
680222d feat(billing): add escrow mechanism for campaign funds
747a462 feat(payout): add PayoutService with basic payout logic
bf4dd4b feat(channel-owner): add placement approval flow and auto-approve task
46731b7 feat(channel-owner): add /my_channels and channel settings management
5b2dc61 feat(payout): add Payout model and migration
```

---

## Итого

- **Спринт 0**: 6/6 задач ✅
- **Спринт 1**: 6/6 задач ✅
- **Ruff**: 0 ошибок ✅
- **Mypy**: 0 ошибок ✅
- **Ветки**: `sprint/0` → `develop`, `sprint/1` → `origin/sprint/1` ✅

**Готово к Спринту 2** — Маркетплейс (отзывы, предпросмотр, CTR-трекинг, аналитика).
