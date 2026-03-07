# RekHarborBot — Дорожная карта реализации
## Версия для Qwen Code · Март 2026

---

## Контекст и отправная точка

### Что уже сделано (до Спринта 0)

| Статус | Что сделано |
|--------|-------------|
| ✅ | Mypy: 0 ошибок (было 281) |
| ✅ | Ruff: чист |
| ✅ | Баг 400 CryptoBot — исправлен |
| ✅ | Импорт CampaignStatus — исправлен |
| ✅ | README — обновлён (пороги фильтра, шаги кампании, ~400 запросов) |
| ✅ | safe_callback.py — создан |
| ⏸️ | Unit тесты: 14 падают (устарели, отдельная задача) |
| ❌ | Integration тесты: пусто |

### Ветвление (Git)

```
main          ← только стабильные релизы (после Code Review)
develop       ← интеграция всех спринтов
sprint/0      ← ветка Спринта 0
sprint/1      ← ветка Спринта 1
sprint/2      ← и т.д.
```

**Каждый спринт = отдельная ветка `sprint/N` → PR в `develop` → Code Review → Merge.**

### Рабочее окружение для всех спринтов

```powershell
cd ~/python-projects/market-telegram-bot
source .venv/Scripts/activate
```

### Обязательные проверки перед каждым коммитом

```powershell
poetry run ruff check src/          # 0 ошибок обязательно
poetry run mypy src/ --ignore-missing-imports 2>&1 | tail -3   # 0 ошибок обязательно
poetry run pytest tests/unit/ -v --ignore=tests/unit/ -k "not outdated"  # 0 новых падений
```

---

## Обзор спринтов

| Спринт | Название | Срок | Ключевой результат |
|--------|----------|------|-------------------|
| **0** | Технический фундамент | 1–2 нед | Opt-in каналы (P0), публичный дашборд |
| **1** | Владелец канала | 2–3 нед | Полный цикл регистрации и управления каналом |
| **2** | Маркетплейс | 2–3 нед | Отзывы, предпросмотр, аналитика, выплаты |
| **3** | B2B и рейтинги | 2–3 нед | B2B-пакеты, рейтинги, детектор накрутки |
| **4** | Геймификация | 1–2 нед | XP, уровни, значки, реферальная программа |

---

## СПРИНТ 0 — Технический фундамент и публичный дашборд

### Цель

Закрыть критические P0-проблемы и устранить «проблему чёрного ящика» для новых пользователей.
Без этого спринта платформа технически нелегальна (рассылка без согласия) и невидима для оценки.

### Задачи

#### 0.1 Миграция БД — поля opt-in в TelegramChat

**Файл:** `src/db/models/analytics.py` или `src/db/models/chat.py` (там где TelegramChat)

Добавить поля:
```python
bot_is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
admin_added_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
owner_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
price_per_post: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
is_accepting_ads: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

Создать Alembic-миграцию: `alembic revision --autogenerate -m "add_opt_in_fields_to_telegram_chat"`

#### 0.2 Фильтр bot_is_admin в рассыльщике

**Файл:** `src/tasks/mailing_tasks.py`

В функции запуска кампании добавить фильтр:
только каналы где `bot_is_admin=True AND is_accepting_ads=True` попадают в рассылку.

#### 0.3 Хэндлер /add_channel (базовый)

**Файл:** `src/bot/handlers/channel_owner.py` (создать новый)

FSM-флоу:
1. `/add_channel` → запросить @username канала
2. Отправить инструкцию как добавить бота админом
3. Кнопка «Проверить» → вызов `getChatMember(channel_id, bot_id)` → проверить `status == "administrator"`
4. При успехе: установить `bot_is_admin=True`, `admin_added_at=now()`, `owner_user_id=user.id`
5. Запросить цену за пост и принятые тематики
6. Установить `is_accepting_ads=True`
7. Подтверждение: «Канал @username добавлен и виден в каталоге»

#### 0.4 Публичный дашборд — команда /stats

**Файл:** `src/bot/handlers/start.py` (добавить) или новый `src/bot/handlers/stats.py`

Команда `/stats` — доступна без авторизации (гостям).
Запрашивает из БД и показывает:
- Количество активных каналов (`bot_is_admin=True, is_accepting_ads=True`)
- Суммарный охват (сумма `member_count` активных каналов)
- Кампаний запущено (всего)
- Кампаний завершено успешно
- Средний рейтинг каналов
- Суммарно выплачено владельцам (пока 0, но поле уже показываем)

**Сервисный метод:** `src/core/services/analytics_service.py` — добавить `get_platform_stats() -> PlatformStats`

#### 0.5 Публичный дашборд — Mini App страница

**Файл:** `mini_app/src/pages/` — добавить страницу `PlatformStats.tsx`

Отображает те же метрики через FastAPI эндпоинт.

**FastAPI эндпоинт:** `src/api/routers/analytics.py` — добавить `GET /api/v1/stats/public` (без авторизации)

#### 0.6 Обновить приветственное сообщение

**Файл:** `src/bot/handlers/start.py`

В `/start` для новых пользователей показывать ключевые метрики платформы (из `get_platform_stats()`).

### Метрики успеха Спринта 0

| Метрика | Цель | Как проверить |
|---------|------|--------------|
| Миграция применена | ✅ | `alembic current` показывает head |
| Поля в БД | `bot_is_admin`, `admin_added_at`, `owner_user_id`, `price_per_post`, `is_accepting_ads` | `\d telegram_chats` в psql |
| /add_channel работает | Добавление тестового канала проходит все 5 шагов | Ручное тестирование |
| bot_is_admin проверяется | Кампания НЕ рассылается в каналы с `bot_is_admin=False` | Unit тест в `test_mailing_tasks.py` |
| /stats отвечает | Команда возвращает структурированные метрики | Ручное тестирование |
| FastAPI /stats/public | HTTP 200, JSON с 6 метриками | `curl /api/v1/stats/public` |
| Ruff | 0 ошибок | `ruff check src/` |
| Mypy | 0 ошибок | `mypy src/ --ignore-missing-imports` |

### Git-операции Спринта 0

```powershell
# Создать ветку
git checkout develop
git pull origin develop
git checkout -b sprint/0

# После каждой задачи — коммит
git add .
git commit -m "feat(opt-in): add bot_is_admin fields migration"
git commit -m "feat(mailing): filter channels by bot_is_admin"
git commit -m "feat(channel-owner): add /add_channel handler with admin verification"
git commit -m "feat(stats): add /stats command and public dashboard"
git commit -m "feat(mini-app): add PlatformStats page"
git commit -m "feat(start): show platform metrics in welcome message"

# Отправить ветку
git push origin sprint/0

# PR: sprint/0 → develop
```

---

## СПРИНТ 1 — Полный цикл владельца канала

### Цель

Владелец канала может полностью управлять своим каналом через бота: настраивать параметры,
видеть входящие заявки, одобрять/отклонять, отслеживать заработок.
Это даёт реальный контент для каталога рекламодателей.

### Задачи

#### 1.1 Миграция БД — модель Payout

**Файл:** `src/db/models/payout.py` (создать)

```python
class Payout(Base):
    __tablename__ = "payouts"
    id: Mapped[int]
    owner_id: Mapped[int]  # FK → users.id
    channel_id: Mapped[int]  # FK → telegram_chats.id
    amount: Mapped[Decimal]  # сумма выплаты (80% от цены поста)
    currency: Mapped[str]  # "USDT" | "TON" | "RUB"
    status: Mapped[str]  # "pending" | "processing" | "paid" | "failed"
    placement_id: Mapped[int]  # FK → campaign placements (какой пост)
    created_at: Mapped[datetime]
    paid_at: Mapped[datetime | None]
    tx_hash: Mapped[str | None]  # хэш транзакции
```

Миграция: `"add_payout_model"`

#### 1.2 Хэндлер управления каналом

**Файл:** `src/bot/handlers/channel_owner.py` (расширить от Спринта 0)

Команды и кнопки:
- `/my_channels` — список зарегистрированных каналов с балансом к выплате
- Кнопка «Настройки» канала: изменить цену, тематики, режим одобрения, статус
- Кнопка «Аналитика» канала: доход за периоды, количество размещений
- Кнопка «Заявки» канала: входящие заявки (ожидают одобрения)
- Кнопка «Отключить рекламу» / «Включить рекламу»

#### 1.3 Обработка входящих заявок

**Файл:** `src/bot/handlers/channel_owner.py`

Когда рекламодатель запускает кампанию с каналом у которого `is_accepting_ads=True`:
1. Владелец получает уведомление: текст объявления + сумма выплаты + дата публикации
2. Кнопки: «✅ Одобрить», «❌ Отклонить», «✏️ Запросить правки»
3. Автоодобрение через 24 ч если нет ответа (Celery задача)
4. При отклонении — средства возвращаются рекламодателю на баланс

**Файл:** `src/tasks/mailing_tasks.py` — добавить задачу `auto_approve_pending_placements()`

#### 1.4 Система выплат (базовая)

**Файл:** `src/core/services/payout_service.py` (создать)

Методы:
- `calculate_payout(placement_id) -> Decimal` — 80% от цены поста
- `create_pending_payout(placement_id)` — после факта публикации
- `get_owner_balance(owner_id) -> Decimal` — суммарно к выплате
- `process_payout(payout_id)` — заглушка (UI для ручного запроса, реальная интеграция с CryptoBot — в Спринте 2)

**Файл:** `src/tasks/billing_tasks.py` — добавить `check_pending_payouts()` — еженедельно

#### 1.5 Эскроу-механика

**Файл:** `src/core/services/billing_service.py`

Добавить методы:
- `freeze_funds(campaign_id, amount)` — при запуске кампании, статус «заморожено»
- `release_funds_for_placement(placement_id)` — после факта публикации, создаёт Payout
- `refund_frozen_funds(placement_id)` — если публикация не состоялась в 48 ч

#### 1.6 Уведомления для владельца

**Файл:** `src/tasks/notification_tasks.py` — добавить:
- `notify_owner_new_placement(placement_id)` — новая заявка
- `notify_owner_payout_created(payout_id)` — выплата начислена
- `remind_owner_pending_placement(placement_id)` — за 4 ч до истечения срока

### Метрики успеха Спринта 1

| Метрика | Цель | Как проверить |
|---------|------|--------------|
| Модель Payout | Создана и мигрирована | `\d payouts` в psql |
| /my_channels | Показывает список каналов | Ручное тестирование |
| Смена настроек канала | Все 5 параметров меняются и сохраняются | Ручное тестирование |
| Входящая заявка | Владелец получает уведомление при создании кампании | E2E тест с тестовым каналом |
| Автоодобрение | Celery задача создана и есть в Beat-расписании | `grep "auto_approve" src/tasks/` |
| Эскроу | `freeze_funds` блокирует баланс; `release_funds` создаёт Payout | Unit тест |
| Payout создаётся | После публикации — Payout в статусе `pending` | Unit тест |
| Ruff + Mypy | 0 ошибок | CI команды |

### Git-операции Спринта 1

```powershell
git checkout develop
git pull origin develop
git checkout -b sprint/1

git commit -m "feat(payout): add Payout model and migration"
git commit -m "feat(channel-owner): add /my_channels and channel settings"
git commit -m "feat(channel-owner): add placement approval flow"
git commit -m "feat(billing): add escrow freeze/release/refund"
git commit -m "feat(payout): add payout_service with calculation logic"
git commit -m "feat(notifications): add owner notification tasks"

git push origin sprint/1
# PR: sprint/1 → develop
```

---

## СПРИНТ 2 — Маркетплейс: аналитика, отзывы, предпросмотр

### Цель

Рекламодатель получает полный цикл с измеримым результатом: система отзывов строит доверие,
предпросмотр снижает конфликты, CTR-трекинг даёт реальную аналитику.
Это закрывает конкурентный gap с Telega.io по измеримости.

### Задачи

#### 2.1 Миграция БД — модель Review

**Файл:** `src/db/models/review.py` (создать)

```python
class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int]
    reviewer_id: Mapped[int]   # FK → users.id (кто пишет отзыв)
    reviewee_id: Mapped[int]   # FK → users.id (о ком отзыв)
    channel_id: Mapped[int | None]  # если отзыв о канале
    placement_id: Mapped[int]  # обязательная связь с размещением
    reviewer_role: Mapped[str]  # "advertiser" | "owner"
    # Оценки для рекламодателя→каналу
    score_compliance: Mapped[int | None]   # соответствие договорённостям 1-5
    score_audience: Mapped[int | None]     # качество аудитории 1-5
    score_speed: Mapped[int | None]        # скорость взаимодействия 1-5
    # Оценки для владельца→рекламодателю
    score_material: Mapped[int | None]     # качество материала 1-5
    score_requirements: Mapped[int | None] # адекватность требований 1-5
    score_payment: Mapped[int | None]      # скорость оплаты 1-5
    comment: Mapped[str | None]
    is_hidden: Mapped[bool]   # автоскрытие по антифроду
    created_at: Mapped[datetime]
```

Миграция: `"add_review_model"`

#### 2.2 Сервис и хэндлер отзывов

**Файл:** `src/core/services/review_service.py` (создать)

Методы:
- `request_review_from_advertiser(placement_id)` — после завершения кампании
- `request_review_from_owner(placement_id)` — после выплаты
- `submit_review(reviewer_id, placement_id, scores, comment)` — сохранить отзыв
- `get_channel_rating(channel_id) -> float` — средняя по `score_compliance`
- `check_duplicate_fraud(comment) -> bool` — антифрод

**Файл:** `src/bot/handlers/campaigns.py` — добавить FSM для запроса отзыва после завершения

**Файл:** `src/tasks/notification_tasks.py` — добавить `request_post_campaign_reviews(campaign_id)`

#### 2.3 Предпросмотр поста

**Файл:** `src/bot/handlers/campaigns.py` — в мастере кампании добавить шаг предпросмотра

Логика: после шага «Рекламный материал» — показать сообщение точно в том формате
как оно будет выглядеть в канале (текст с HTML-форматированием + медиа если есть).
Кнопки: «✅ Выглядит хорошо» / «✏️ Изменить текст».

Это чисто UI-шаг без изменений в БД.

#### 2.4 CTR-трекинг

**Файл:** `src/db/models/` — добавить поле в размещение или отдельную модель:
```python
tracking_url: Mapped[str | None]  # исходная ссылка рекламодателя
short_link: Mapped[str | None]    # короткая ссылка платформы для трекинга
clicks_count: Mapped[int]         # счётчик кликов
```

**Файл:** `src/api/routers/` — добавить `GET /r/{short_code}` — редирект + инкремент счётчика

**Файл:** `src/core/services/` — `link_tracking_service.py` — генерация коротких ссылок

#### 2.5 Улучшение аналитики кампании — CPM, CTR, ROI

**Файл:** `src/core/services/analytics_service.py` — добавить методы:
- `calculate_cpm(campaign_id) -> Decimal` — cost per 1000 views
- `calculate_ctr(campaign_id) -> float` — клики / просмотры (если есть tracking_url)
- `calculate_roi(campaign_id) -> dict` — сводный ROI-отчёт
- `generate_campaign_pdf_report(campaign_id) -> bytes` — PDF через reportlab

**Файл:** `src/bot/handlers/campaign_analytics.py` — добавить вывод CPM/CTR/ROI

#### 2.6 Умный выбор времени публикации

**Файл:** `src/core/services/` — `timing_service.py` (создать)

Метод `suggest_optimal_time(channel_id) -> datetime`:
- Через Telethon читает последние 50 постов канала
- Анализирует часы публикации и часы с наибольшим числом просмотров
- Возвращает рекомендуемое время публикации

**Файл:** `src/bot/handlers/campaigns.py` — на шаге «Расписание» добавить кнопку «Оптимальное время»

### Метрики успеха Спринта 2

| Метрика | Цель | Как проверить |
|---------|------|--------------|
| Модель Review | Создана, мигрирована | `\d reviews` |
| Запрос отзыва | Отправляется обеим сторонам после завершения | Ручной тест завершения кампании |
| Отзыв сохраняется | submit_review создаёт запись | Unit тест |
| Предпросмотр | Шаг отображается в мастере кампании | Ручной тест создания кампании |
| CTR-редирект | `GET /r/abc` → редирект + clicks_count++ | `curl -I /r/test_code` |
| CPM рассчитывается | Метод возвращает Decimal > 0 при наличии данных | Unit тест |
| PDF-отчёт | generate_campaign_pdf_report возвращает bytes | Unit тест |
| Оптимальное время | Метод suggest_optimal_time возвращает datetime | Unit тест (с mock Telethon) |
| Ruff + Mypy | 0 ошибок | CI команды |

### Git-операции Спринта 2

```powershell
git checkout develop && git pull origin develop
git checkout -b sprint/2

git commit -m "feat(review): add Review model and migration"
git commit -m "feat(review): add review_service and post-campaign request"
git commit -m "feat(campaign): add post preview step in campaign wizard"
git commit -m "feat(analytics): add CTR tracking with short links"
git commit -m "feat(analytics): add CPM/CTR/ROI calculations and PDF report"
git commit -m "feat(timing): add optimal publication time suggestion"

git push origin sprint/2
# PR: sprint/2 → develop
```

---

## СПРИНТ 3 — B2B-маркетплейс и рейтинговая система

### Цель

Закрыть сегмент агентств и крупных рекламодателей, усилить доверие к каталогу через
верифицированные рейтинги и защиту от накрутки.

### Задачи

#### 3.1 Миграция БД — B2BPackage и ChannelRating

**Файл:** `src/db/models/b2b_package.py` (создать)

```python
class B2BPackage(Base):
    __tablename__ = "b2b_packages"
    id: Mapped[int]
    name: Mapped[str]
    niche: Mapped[str]  # "it" | "business" | "realestate" | "crypto" | "marketing" | "finance"
    description: Mapped[str]
    channels_count: Mapped[int]
    guaranteed_reach: Mapped[int]   # гарантированный суммарный охват
    min_er: Mapped[float]           # минимальный ER по пакету
    price: Mapped[Decimal]
    discount_pct: Mapped[int]       # скидка % от суммы разовых размещений
    is_active: Mapped[bool]
    channel_ids: Mapped[list]       # JSONB список ID каналов в пакете
```

**Файл:** `src/db/models/channel_rating.py` (создать)

```python
class ChannelRating(Base):
    __tablename__ = "channel_ratings"
    id: Mapped[int]
    channel_id: Mapped[int]   # FK → telegram_chats.id
    date: Mapped[date]
    subscribers: Mapped[int]
    avg_views: Mapped[int]
    er: Mapped[float]
    reach_score: Mapped[float]   # 0-100, вес 30%
    er_score: Mapped[float]      # 0-100, вес 25%
    growth_score: Mapped[float]  # 0-100, вес 15%
    frequency_score: Mapped[float]  # 0-100, вес 10%
    reliability_score: Mapped[float]  # 0-100, вес 15%
    age_score: Mapped[float]     # 0-100, вес 5%
    total_score: Mapped[float]   # итоговый балл 0-100
    rank_in_topic: Mapped[int | None]
    fraud_flag: Mapped[bool]     # флаг подозрительной активности
```

Миграции: `"add_b2b_package_model"`, `"add_channel_rating_model"`

#### 3.2 Рейтинговый сервис

**Файл:** `src/core/services/rating_service.py` (создать)

Методы:
- `calculate_channel_score(channel_id, date) -> ChannelRating` — формула из PRD §7.1
- `recalculate_all_ratings()` — пересчёт всех каналов (вызывается Celery ежедневно)
- `get_top_channels(topic, limit=10) -> list` — топ по тематике
- `get_reliability_stars(channel_id) -> float` — от 1 до 5 (из §7.2 PRD)

**Файл:** `src/tasks/rating_tasks.py` (создать)

Задачи:
- `recalculate_ratings_daily()` — ежедневно в 04:00 UTC
- `update_weekly_toplists()` — еженедельно в понедельник

**Файл:** `src/tasks/celery_config.py` — добавить в beat_schedule

#### 3.3 Детектор накрутки

**Файл:** `src/core/services/rating_service.py` — добавить метод:

`detect_fraud(channel_id) -> FraudReport`:
- Если прирост подписчиков > 50% за 7 дней — флаг
- Если ER < 0.5% при > 10k подписчиков — флаг
- Если отток > 30% через 14 дней после роста — флаг
- При флаге: обновить `fraud_flag=True`, переместить в конец каталога, уведомить админа

**Файл:** `src/tasks/rating_tasks.py` — добавить `run_fraud_detection()` — ежедневно

#### 3.4 Хэндлер B2B-маркетплейса

**Файл:** `src/bot/handlers/b2b.py` (создать)

Команда `/b2b`:
1. Показать список ниш (6 кнопок) с кратким описанием ЦА
2. При выборе ниши — показать доступные пакеты с ценами и охватом
3. Детальная карточка пакета: состав, гарантии, скидка vs разовые размещения
4. Кнопка «Купить пакет» → переход в мастер кампании с предзаполненным выбором каналов

**Файл:** `src/core/services/b2b_package_service.py` (создать)

Методы:
- `get_packages_by_niche(niche) -> list[B2BPackage]`
- `validate_package_channels(package_id) -> bool` — все ли каналы активны
- `get_package_actual_reach(package_id) -> int` — реальный охват на сейчас

#### 3.5 Медиакит канала

**Файл:** `src/core/services/b2b_package_service.py` — добавить:

`generate_mediakit_pdf(channel_id) -> bytes`:
- Через reportlab генерирует PDF
- Содержит: статистику канала, тематику, историю роста, прайс, примеры постов
- Кнопка в детальной карточке канала: «📄 Медиакит»

#### 3.6 Расширение каталога — новые фильтры

**Файл:** `src/bot/handlers/channels_db.py` — добавить фильтры:
- Минимальный ER (1% / 3% / 5% / 10%+)
- Рейтинг надёжности (≥ 3★ / ≥ 4★ / 5★)
- Только растущие (прирост > 0 за 7 дней)
- Исключить каналы с `fraud_flag=True`

### Метрики успеха Спринта 3

| Метрика | Цель | Как проверить |
|---------|------|--------------|
| Модели B2BPackage, ChannelRating | Созданы и мигрированы | `alembic current` |
| Расчёт рейтинга | calculate_channel_score возвращает total_score 0-100 | Unit тест с mock данными |
| Celery задачи рейтингов | Есть в beat_schedule | `grep "rating" src/tasks/celery_config.py` |
| Детектор накрутки | При аномалии fraud_flag=True | Unit тест с аномальными данными |
| /b2b команда | Показывает 6 ниш и пакеты | Ручной тест |
| Медиакит | generate_mediakit_pdf возвращает PDF > 0 байт | Unit тест |
| Новые фильтры в каталоге | ER-фильтр работает | Ручной тест |
| Ruff + Mypy | 0 ошибок | CI команды |

### Git-операции Спринта 3

```powershell
git checkout develop && git pull origin develop
git checkout -b sprint/3

git commit -m "feat(b2b): add B2BPackage and ChannelRating models with migrations"
git commit -m "feat(rating): add rating_service with scoring formula"
git commit -m "feat(rating): add fraud detector"
git commit -m "feat(rating): add rating_tasks Celery jobs"
git commit -m "feat(b2b): add /b2b handler with niche browser"
git commit -m "feat(b2b): add mediakit PDF generation"
git commit -m "feat(catalog): add ER, reliability and growth filters"

git push origin sprint/3
# PR: sprint/3 → develop
```

---

## СПРИНТ 4 — Геймификация и удержание

### Цель

Создать психологические стимулы к долгосрочному использованию платформы:
уровни снижают отток, реферальная программа даёт органический рост,
дайджесты возвращают неактивных пользователей.

### Задачи

#### 4.1 Миграция БД — Badge, UserBadge, обновление User

**Файл:** `src/db/models/badge.py` (создать)

```python
class Badge(Base):
    __tablename__ = "badges"
    id: Mapped[int]
    code: Mapped[str]        # уникальный код: "first_campaign", "hundred_posts"
    name: Mapped[str]
    description: Mapped[str]
    icon_emoji: Mapped[str]
    xp_reward: Mapped[int]
    category: Mapped[str]   # "advertiser" | "owner" | "both"
    condition_type: Mapped[str]  # "campaigns_count" | "spend_amount" | "placements_count" etc.
    condition_value: Mapped[int]  # числовой порог для выдачи

class UserBadge(Base):
    __tablename__ = "user_badges"
    id: Mapped[int]
    user_id: Mapped[int]   # FK → users.id
    badge_id: Mapped[int]  # FK → badges.id
    earned_at: Mapped[datetime]
```

**Файл:** `src/db/models/user.py` — добавить поля:

```python
level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
xp_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
total_spent: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
total_earned: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
```

Миграции: `"add_badge_models"`, `"add_gamification_fields_to_user"`

#### 4.2 XP-сервис и уровни

**Файл:** `src/core/services/xp_service.py` (создать)

Методы:
- `add_xp(user_id, amount, reason) -> LevelUpEvent | None` — начислить XP, вернуть LevelUp если поднялся
- `get_level_for_xp(xp) -> int` — 1..10 по таблице из PRD §9.1
- `get_level_privileges(level) -> LevelPrivileges` — скидки и привилегии
- `get_progress_to_next_level(user_id) -> dict` — процент прогресса + сколько до следующего

Триггеры начисления XP (добавить вызовы в существующий код):
- Кампания запущена: +50 XP
- Кампания завершена: +100 XP
- Первая кампания: +200 XP (через Badge)
- Размещение выполнено (владелец): +30 XP
- Отзыв оставлен: +20 XP

#### 4.3 Сервис значков

**Файл:** `src/core/services/badge_service.py` (создать)

Методы:
- `check_and_award_badges(user_id)` — проверить все условия и выдать новые значки
- `award_badge(user_id, badge_code)` — выдать конкретный значок + XP
- `get_user_badges(user_id) -> list[Badge]`

**Файл:** `src/tasks/gamification_tasks.py` (создать)

Задачи:
- `update_streaks_daily()` — ежедневно проверять стрики
- `check_seasonal_events()` — ежедневно, наград сезонных ивентов
- `send_weekly_digest()` — каждый понедельник

#### 4.4 Обновление кабинета — прогресс-бар и значки

**Файл:** `src/bot/handlers/cabinet.py` — расширить:
- Показывать уровень, XP, прогресс-бар до следующего уровня
- Показывать заработанные значки (до 6 последних)
- Кнопка «Все значки» → полный список с условиями незаработанных

Пример UI:
```
👤 Иван Иванов
📊 Уровень 3 — Опытный 🔥
⚡ 2 340 / 3 500 XP ████████░░ 67%
🎯 Скидка 3% на размещения

🏆 Значки (3):
🚀 Первый запуск  💎 100 размещений  ⚡ Быстрый ответ
```

#### 4.5 Реферальная программа (логика)

Поле `referred_by_id` в User уже есть. Реализовать логику:

**Файл:** `src/core/services/billing_service.py` — добавить:
- `apply_referral_bonus_advertiser(referred_user_id)` — +500 кр после первой кампании
- `apply_referral_bonus_channel(referred_user_id)` — +300 кр после первого размещения

**Файл:** `src/bot/handlers/cabinet.py` — добавить раздел «Реферальная программа»:
- Реферальная ссылка пользователя
- Количество приведённых пользователей
- Суммарно заработано через рефералов

**Файл:** `src/bot/handlers/start.py` — обрабатывать `?start=ref_CODE` параметр

#### 4.6 Еженедельный дайджест

**Файл:** `src/tasks/gamification_tasks.py` — `send_weekly_digest()`:

Для рекламодателей: суммарный охват за неделю, лучшая кампания, прогресс уровня
Для владельцев: заработок за неделю, количество размещений, изменение рейтинга

### Метрики успеха Спринта 4

| Метрика | Цель | Как проверить |
|---------|------|--------------|
| Модели Badge, UserBadge | Созданы и мигрированы | `alembic current` |
| Поля level, xp_points в User | Добавлены | `\d users` |
| add_xp работает | XP начисляются, при уровне-вверх возвращает LevelUpEvent | Unit тест |
| Прогресс-бар в кабинете | Отображается корректно | Ручной тест |
| Значок выдаётся | check_and_award_badges выдаёт при выполнении условия | Unit тест |
| Реферальная ссылка | Создаётся, переход засчитывается | Ручной тест |
| Реферальный бонус | Начисляется после первой кампании реферала | Unit тест |
| Дайджест | Задача выполняется без ошибок | Celery log |
| Ruff + Mypy | 0 ошибок | CI команды |

### Git-операции Спринта 4

```powershell
git checkout develop && git pull origin develop
git checkout -b sprint/4

git commit -m "feat(gamification): add Badge, UserBadge models and migration"
git commit -m "feat(gamification): add xp and level fields to User model"
git commit -m "feat(gamification): add xp_service with level system"
git commit -m "feat(gamification): add badge_service with condition checking"
git commit -m "feat(cabinet): add level progress bar and badges display"
git commit -m "feat(referral): implement referral bonus logic"
git commit -m "feat(gamification): add weekly digest and streak tasks"

git push origin sprint/4
# PR: sprint/4 → develop
```

---

## Финальный чеклист перед PR в develop (все спринты)

```powershell
# 1. Линтинг
poetry run ruff check src/ tests/
echo "Ruff exit code: $?"

# 2. Типизация
poetry run mypy src/ --ignore-missing-imports 2>&1 | tail -5

# 3. Тесты (только стабильные)
poetry run pytest tests/unit/ -v -k "not outdated" --tb=short

# 4. Миграции применены
poetry run alembic current
poetry run alembic check  # нет непримененных миграций

# 5. Нет незакоммиченных изменений
git status  # должно быть "nothing to commit"

# 6. Ветка актуальна
git log --oneline -5
```

### Шаблон описания PR

```markdown
## Спринт N — [Название]

### Что сделано
- [ ] Задача 1
- [ ] Задача 2

### Метрики успеха
| Метрика | Результат |
|---------|-----------|
| Ruff | ✅ 0 ошибок |
| Mypy | ✅ 0 ошибок |
| Unit тесты | ✅ N passed, 0 failed |
| Миграции | ✅ Applied |

### Новые файлы
- `src/...` — описание

### Изменённые файлы
- `src/...` — что изменилось

### Что требует внимания при review
```

---

## Зависимости между спринтами

```
Спринт 0 (bot_is_admin, /add_channel, /stats)
    │
    ├── Спринт 1 (Payout, эскроу, управление заявками)
    │       │
    │       └── Спринт 2 (Review, предпросмотр, CTR, CPM/ROI)
    │               │
    │               └── Спринт 3 (B2B, рейтинги, детектор накрутки)
    │                       │
    │                       └── Спринт 4 (XP, Badge, реферальная, дайджест)
    │
    └── Каждый спринт мержится в develop до начала следующего
```

**Нельзя начинать Спринт 1 без завершённого Спринта 0:**
Спринт 1 зависит от `owner_user_id` и `bot_is_admin` из миграции Спринта 0.

**Нельзя начинать Спринт 2 без завершённого Спринта 1:**
Спринт 2 создаёт Review которые привязаны к placements из эскроу Спринта 1.
