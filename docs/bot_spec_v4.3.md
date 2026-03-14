# RekHarborBot — Спецификация бота v4.3

**Дата:** 14.03.2026 | **Машиночитаемая версия:** `bot_spec_v4.3.json`

---

## Что изменилось в v4.3

| # | Изменение |
|---|-----------|
| А-01 | **Кабинет** — единый shared-модуль для всех ролей (баланс + вывод + пополнение + подписка + реферал + геймификация) |
| А-02 | **Эскроу** — `release_escrow()` вызывается ТОЛЬКО после авто-удаления поста, не при публикации |
| А-03 | **Dispute флоу** — полная спецификация (6 экранов) |
| А-04 | **Мониторинг постов** — Celery каждые 5 мин, автоматический Dispute при досрочном удалении |
| А-05 | **Аналитика** — только то что реально можно считать (reach snapshot + tracking clicks) |
| А-06 | **Broadcast** — убран из advertiser, оставлен только для admin |
| А-07 | **B2B пакеты** — удалены полностью |

---

## Архитектура модулей

```
shared/      → start, ToS, кабинет, помощь, обратная связь, уведомления
advertiser/  → создание размещения, мои кампании, аналитика
owner/       → мои каналы, настройки, заявки, аналитика, выплаты
arbitration/ → арбитраж (shared между owner и advertiser)
dispute/     → НОВЫЙ: споры (admin + обе стороны)
billing/     → пополнение, подписки
admin/       → платформа, broadcast рассылки, выплаты владельцам
```

---

## РАЗДЕЛ 1 — SHARED ЭКРАНЫ

### 1.1 `/start` и ToS

**Новый пользователь:**
```
/start → показать ToS
   ↓
[✅ Принять условия]   → создать user с referral_code → role_select
[❌ Отклонить]         → прощальное сообщение, конец
```

**Существующий пользователь:**
```
/start → если role выбрана → показать меню роли
       → если role не выбрана → role_select
```

**Экран ToS** (`terms:accept` / `terms:decline`)
- Handler: `start.py::show_tos`
- При принятии: `user.terms_accepted_at = NOW()`, генерация `referral_code`

---

### 1.2 Главное меню (`main:main_menu`)

```
📱 Главное меню

[👤 Кабинет]
[🔄 Выбрать роль]
[💬 Помощь]  [✉️ Обратная связь]
```

Callbacks: `main:cabinet`, `main:change_role`, `main:help`, `main:feedback`

---

### 1.3 Выбор роли (`main:change_role`)

```
[📣 Рекламодатель]  → role:advertiser → adv_menu
[📺 Владелец канала] → role:owner → own_menu
[🔙 Главное меню]
```

---

### 1.4 Кабинет (`main:cabinet`) ⭐ ОБЩИЙ ДЛЯ ВСЕХ РОЛЕЙ

```
👤 Кабинет

💳 Баланс (рекламодатель): {balance_rub} ₽
💰 Заработок (владелец): {earned_rub} ₽

📊 Репутация рекл.: {adv_rep}/10 | Репутация вл.: {own_rep}/10
⭐ Тариф: {plan_name}
🏆 Ур. рекл.: {adv_level} ({adv_xp} XP) | Ур. вл.: {own_level} ({own_xp} XP)
🆔 ID: {user_id}

[если role in (owner, both) AND earned_rub > 0]:
💡 Заработок за {month}: {monthly_earned} ₽
Не забудьте задекларировать доход в «Мой налог».
```

**Кнопки (условные):**

| Кнопка | Условие | Callback |
|--------|---------|---------|
| 💳 Пополнить баланс | role in (advertiser, both) | `billing:topup_start` |
| 💸 Запросить вывод | role in (owner, both) AND earned_rub >= 1000 | `payout:request_start` |
| ⭐ Изменить тариф | всегда | `billing:plans` |
| 🎁 Реферальная программа | всегда | `cabinet:referral` |
| 🏆 Геймификация | всегда | `cabinet:gamification` |
| 🔙 Главное меню | всегда | `main:main_menu` |

---

### 1.5 Реферальная программа (`cabinet:referral`)

```
🎁 Реферальная программа

🔗 Ваша ссылка:
t.me/RekHarborBot?start=REF_{referral_code}

👥 Приглашено: {ref_count} чел.
💰 Бонусов: {ref_bonus_total} ₽

Условия:
• За рекламодателя +50 ₽ после первого пополнения

[📋 Скопировать ссылку]  [🔙 Кабинет]
```

---

### 1.6 Геймификация (`cabinet:gamification`)

```
🏆 Геймификация

─── Рекламодатель ───
⭐ Уровень: {adv_level}
📊 XP: {adv_xp} / {adv_xp_next}

─── Владелец ───
⭐ Уровень: {own_level}
📊 XP: {own_xp} / {own_xp_next}

─── Бейджи ───
{badges_list}

─── Как получить XP ───
• Завершённое размещение: +50 XP (оба)
• Отзыв 5★: +20 XP (владелец)
• Успешный вывод: +10 XP (владелец)
• Новая кампания: +10 XP (рекламодатель)
```

---

## РАЗДЕЛ 2 — BILLING (ПОПОЛНЕНИЕ + ПОДПИСКИ)

### 2.1 Флоу пополнения баланса

```
billing:topup_start
    ↓
Показать 6 быстрых кнопок + [Ввести свою сумму]
    ↓
topup:amount:{N} или ввод числа
    ↓
topup_confirm: desired={N} ₽ / fee={N*0.035} ₽ / gross={desired+fee} ₽
    ↓
[✅ Перейти к оплате] → создать ЮKassa платёж
    ↓
Ссылка на оплату + кнопки [💳 Оплатить] [✅ Проверить] [❌ Отмена]
    ↓
Вебхук ЮKassa → process_topup_webhook(metadata.desired_balance) ⚠️ НЕ gross_amount
    ↓
✅ Баланс пополнен! Зачислено: {desired_balance} ₽
```

**Расчёт:**
```
desired = 10 000 ₽
fee     = 10 000 × 0.035 = 350 ₽
gross   = 10 350 ₽  ← пользователь платит это
credit  = 10 000 ₽  ← зачисляется это (из metadata)
```

**FSM:** `TopupStates: entering_amount → confirming → waiting_payment`

---

### 2.2 Тарифные планы (`billing:plans`)

| Тариф | Цена | Enum | Кампании | AI/мес | Форматы |
|-------|------|------|----------|--------|---------|
| Free | 0 ₽ | `free` | 1 | ❌ | post_24h |
| Starter | 490 ₽ | `starter` | 5 | 3 | + post_48h |
| Pro | 1 490 ₽ | `pro` | 20 | 20 | + post_7d |
| Agency | 4 990 ₽ | **`business`** ⚠️ | ∞ | ∞ | все 5 |

> ⚠️ `UserPlan.business.value == 'business'`. `PLAN_LIMITS` ключ: `'business'` (не `'agency'`).

---

## РАЗДЕЛ 3 — ADVERTISER ФЛОУ

### 3.1 Меню рекламодателя (`main:adv_menu`)

```
📣 Меню рекламодателя
💳 Баланс: {balance_rub} ₽ | ⭐ {plan_name}

[📊 Статистика и аналитика]
[📣 Создать кампанию]
[📋 Мои кампании]
[🔙 Главное меню]
```

> ⚠️ Кнопка `💼 B2B-пакеты` **УДАЛЕНА** в v4.3

---

### 3.2 Создание кампании (6 шагов)

#### Шаг 1: Категория (`main:create_campaign`)

**Предварительные проверки:**
- `balance_rub >= 2000` → иначе: экран "Пополнить баланс"
- `active_campaigns < plan_limit` → иначе: экран "Обновить тариф"

12 категорий (IT, Бизнес, Образование, Розница, Красота, Еда, Путешествия, Недвижимость, Авто, Спорт, Развлечения) + [❌ Отмена]

> ⚠️ Кнопка `💼 Сразу к B2B` **УДАЛЕНА** в v4.3

---

#### Шаг 2: Подкатегория (`camp:cat:{cat}`)
Подкатегории по выбранной теме + [⏩ Пропустить] + [🔙 Назад]

---

#### Шаг 3: Выбор канала (`camp:subcat:{sub}`)
Каналы показываются по одному, с пагинацией.

**Для каждого канала:**
```
📺 {channel_name} (@{username})
👥 {member_count} подп. | 📈 ER: {er}% | 👁 {avg_views}
⭐ {rating} | 💰 Цена: {price_per_post} ₽

─── Доступные форматы ───
{formats_and_prices}

[✅ Выбрать канал]  [❌ Пропустить]
[▶️ Далее (N выбрано)]  ← только если N > 0
```

> ⚠️ Каналы где `channel.owner_id == user.id` — **скрыть** (self-dealing protection)

---

#### Шаг 4: Формат (`camp:channels:done`)

Кнопка формата **скрывается** если:
- Хотя бы один выбранный канал не поддерживает формат (`allow_format_* = False`)
- Тариф пользователя не включает формат

**Цена кнопки:** `SUM(channel.price_per_post × multiplier)` по всем каналам

| Кнопка | Условие |
|--------|---------|
| 📄 Пост 24ч — {цена} ₽ | всегда |
| 📄 Пост 48ч — {цена} ₽ | все каналы allow + plan in (starter, pro, business) |
| 📄 Пост 7 дней — {цена} ₽ | все каналы allow + plan in (pro, business) |
| 📌 Закреп 24ч — {цена} ₽ | все каналы allow + plan = business |
| 📌 Закреп 48ч — {цена} ₽ | все каналы allow + plan = business |

---

#### Шаг 5: Текст (`camp:format:{fmt}`)

```
[🤖 AI-генерация]   ← только если plan != free AND ai_uses_left > 0
[✏️ Вручную]
[🔙 Назад]
```

**AI:** описание → 3 варианта → выбрать / ещё раз / вручную

**Ручной ввод:** мин. 10 / макс. 1000 символов

---

#### Шаг 6: Подтверждение (`camp:submit`)

```
📋 Каналов: N
📄 Формат: {format_name}
💰 К оплате: {total_price} ₽

⚠️ Владелец должен ответить в течение 24 часов.

[✅ Отправить заявку]  [🔙 Изменить текст]  [❌ Отменить]
```

---

### 3.3 Арбитраж (со стороны рекламодателя)

```
Заявка отправлена → ожидание ответа owner (24ч)
    ↓
Owner принял → уведомление → экран оплаты
Owner отклонил → уведомление → +100% возврат
Owner контр-предложение → уведомление →
    [✅ Принять]  [✏️ Контр]  [❌ Отклонить]
    (макс 3 раунда, каждый 24ч)
Таймаут 24ч → авто-отмена, +100% возврат
```

---

### 3.4 Оплата эскроу (`camp:pay:{id}`)

```
💳 Оплата заявки #{id}

💰 Сумма эскроу: {final_price} ₽
🔒 Деньги заморожены до авто-удаления поста

─── Распределение ───
• Владельцу (ПОСЛЕ удаления): {owner_amount} ₽ (85%)
• Платформа: {platform_amount} ₽ (15%)

⚠️ Отмена после оплаты: возврат 50%

[💳 Оплатить с баланса ({balance_rub} ₽)]  ← если хватает
[💳 Пополнить баланс]                       ← если не хватает
[❌ Отменить]
```

---

### 3.5 После публикации — уведомления

**При публикации (деньги ещё в эскроу):**
```
📢 Реклама опубликована!
📺 @{channel} в {published_at}
🗑 Авто-удаление: {delete_at}
⏳ Средства в эскроу до авто-удаления.

[⚠️ Пожаловаться]  ← доступно 48ч
```

**После авто-удаления (деньги списаны):**
```
✅ Кампания завершена!
💰 Списано: {final_price} ₽
👁 Охват: ≈{reach} | 🖱 Кликов: {clicks}

[⭐ Отзыв]  [📊 Статистика]  [📣 Создать ещё]
```

---

### 3.6 Аналитика рекламодателя (`main:analytics`)

> ⚠️ RT-001: callback `main:analytics` — строго для рекламодателя

```
📊 Статистика рекламодателя

📣 Размещений: {total}
✅ Завершено: {completed}
💰 Потрачено: {total_spent} ₽
👁 Охват (оценка): ≈{total_reach}
🖱 Кликов: {total_clicks}
📈 CTR: {avg_ctr}%

─── По статусам ───
🔵 Активные: {active}  🟢 Завершённые: {completed}  🔴 Отменённые: {cancelled}

─── Топ каналов ───
{top_channels_list}

[✨ AI-анализ]  ← Pro/Agency
[📥 Экспорт CSV]  ← Pro/Agency
```

**Данные:** reach = `PlacementRequest.published_reach` (snapshot при публикации), clicks = `campaigns.clicks_count`

---

## РАЗДЕЛ 4 — OWNER ФЛОУ

### 4.1 Меню владельца (`main:own_menu`)

```
📺 Меню владельца
💰 Заработок: {earned_rub} ₽  🔴 N новых заявок

[📊 Статистика]           → main:owner_analytics  ← RT-001!
[📺 Мои каналы]           → main:my_channels
[📋 Заявки 🔴 N]          → main:my_requests
[💸 Выплаты]              → main:payouts
[🔙 Главное меню]
```

---

### 4.2 Регистрация канала (`own:add_channel`)

**FSM:** `AddChannelStates: entering_username → confirming`

```
Ввод @username
    ↓
Проверка: бот — admin канала?
    ↓ нет → "Сделайте бота администратором"
    ↓ да
Показать: название, подписчики, права бота
    ↓
Права: can_post ✅ | can_delete {✅/⚠️} | can_pin {✅/⚠️}
Предупреждение:
  ⚠️ Без can_delete → форматы с авто-удалением недоступны
  ⚠️ Без can_pin → закрепы недоступны

[➕ Добавить]  [❌ Отмена]
```

---

### 4.3 Настройки канала (`own:settings:{id}`)

| Раздел | Callback | Описание |
|--------|---------|---------|
| 💰 Цена | `own:settings:price:{id}` | мин. 1000 ₽, FSM ввод числа |
| 📄 Форматы | `own:settings:formats:{id}` | toggle allow_format_* (post_24h нельзя выключить) |
| ⏰ Расписание | `own:settings:schedule:{id}` | start/end, перерыв, макс. постов/день (сист. макс 5) |
| 🤖 Автоподтверждение | `own:settings:autoaccept:{id}` | автопринятие заявок |

**Экран форматов:**
```
{✅/❌} Пост 24ч (×1.0) — {цена}₽  ← нельзя выключить
{✅/❌} Пост 48ч (×1.4) — {цена}₽
{✅/❌} Пост 7д  (×2.0) — {цена}₽
{✅/❌} Закреп 24ч (×3.0) — {цена}₽  ← только если can_pin
{✅/❌} Закреп 48ч (×4.0) — {цена}₽  ← только если can_pin
```

---

### 4.4 Входящие заявки (`main:my_requests`)

Детали заявки (`own:request:{id}`):
```
📋 Заявка #{id}
👤 @{advertiser}
📄 Формат: {format_name}
💰 Предложение: {proposed_price} ₽ (ваша цена: {your_price} ₽)
⏰ Запрошенное время: {proposed_time}

─── Текст ───
{ad_text_preview}

⏱ Ответить до: {expires_at}

[✅ Принять]  [✏️ Контр-предложение]  [❌ Отклонить]
```

**Отклонение — ОБЯЗАТЕЛЬНЫЙ комментарий:**
- Мин. 10 символов, не gibberish
- Штрафы: 1й −10 реп, 2й −15, 3й −20 + бан 7д
- Частые отказы > 50% → −5

**Контр-предложение (макс 3 раунда):**
1. Новая цена
2. Новое время
3. Комментарий (необязательно)

---

### 4.5 Выплаты (`main:payouts` → `payout:request_start`)

**FSM:** `PayoutStates: entering_amount → confirming → entering_requisites`

```
Запрашиваемая сумма: {gross} ₽
Комиссия 1.5%: −{fee} ₽
──────────────
Будет переведено: {net} ₽

Введите реквизиты (карта или СБП)
    ↓
✅ Заявка создана! К получению: {net} ₽
Срок: до 24 часов (09:00–22:00 МСК)
```

**Проверки при выводе:**
1. `earned_rub >= 1000` (MIN_PAYOUT)
2. Нет активной заявки
3. Velocity check: `(payouts_30d + gross) / topups_30d <= 0.80`

---

### 4.6 Аналитика владельца (`main:owner_analytics`)

> ⚠️ RT-001: callback `main:owner_analytics` — строго для владельца

```
📊 Статистика владельца

📺 Каналов: {N}
✅ Публикаций: {total}
💰 Заработано: {total_earned} ₽
💰 Ср. чек: {avg_check} ₽
⭐ Средний рейтинг: {avg_rating}

─── Периоды ───
📅 Сегодня: {today} ₽  Неделя: {week} ₽  Месяц: {month} ₽

─── По каналам ───
@{ch}: {N} публ. · {earned} ₽ · {rating}⭐
```

---

## РАЗДЕЛ 5 — DISPUTE ФЛОУ ⭐ НОВЫЙ

### 5.1 Как открывается спор

| Триггер | Кто открывает | Fault |
|---------|---------------|-------|
| Celery: пост удалён < 80% времени | Автоматически | owner_suspected |
| Бот выброшен из канала после публикации | Автоматически | owner_suspected |
| Рекламодатель нажал [⚠️ Пожаловаться] (48ч после публикации) | Рекламодатель | не определён |
| Техническая ошибка публикации | Автоматически | technical |

### 5.2 Уведомления при открытии

**Рекламодателю:**
```
⚠️ Открыт спор по заявке #{id}
📺 @{channel}  💰 {escrow_amount} ₽
🔍 Причина: {reason}

Администратор рассмотрит в течение 24 часов.
Средства заморожены.

[📋 Детали]  [💬 Поддержка]
```

**Владельцу (при досрочном удалении):**
```
⚠️ Открыт спор по размещению в @{channel}
Оплачено: {paid_duration}
Фактически: {actual_duration}

Объясните ситуацию в течение 24 часов.
Иначе — 100% возврат рекламодателю.

[📝 Объяснить]  [📋 Детали]
```

### 5.3 Интерфейс разрешения (admin)

```
🚨 Спор #{id}

📺 @{channel}  💰 {escrow} ₽
Опубл: {published_at} → Удалено: {deleted_at}
Прожило: {actual}/{paid} ({pct}%)

─── Позиция владельца ───
"{owner_explanation}"

─── Позиция рекламодателя ───
"{advertiser_comment}"

[✅ Вина владельца → 100% рекламодателю]
[⚖️ Частичный возврат]
[❌ Жалоба необоснована → выплатить владельцу]
[🔧 Техническая ошибка → 100% возврат]
```

### 5.4 Распределение по решению

| Решение | Рекламодатель | Владелец | Платформа | Репутация |
|---------|---------------|---------|-----------|-----------|
| owner_fault | +100% | 0% | 0% | owner −30 |
| advertiser_fault | 0% | +85% | +15% | adv −10 |
| technical | +100% | 0% | 0% | без штрафов |
| partial | custom% | custom% | остаток | admin решает |

---

## РАЗДЕЛ 6 — СХЕМА ЭСКРОУ (ИСПРАВЛЕННАЯ)

### ⚠️ Ключевое изменение v4.3

```
БЫЛО (неправильно):
  publish_placement() → release_escrow() → owner +85%

СТАЛО (правильно):
  publish_placement()
      ↓ статус: published
  Celery check_posts_alive (каждые 5 мин)
      ↓ пост жив → ждём scheduled_delete_at
  delete_published_post()
      ↓ статус: completed
  release_escrow() → owner.earned_rub += owner_amount
      ↓
  Уведомление владельцу: "Начислено: {owner_amount} ₽"
```

### Обнаружение досрочного удаления

```python
# Проверка существования поста
await bot.forward_message(
    chat_id=bot.id,
    from_chat_id=channel_id,
    message_id=message_id
)
# TelegramBadRequest "message not found" → пост удалён

# Порог для Dispute
if actual_duration < paid_duration * 0.80:
    open_dispute(reason='post_removed_early')
else:
    release_escrow()  # пожил достаточно
```

---

## РАЗДЕЛ 7 — CELERY ЗАДАЧИ

| Задача | Очередь | Расписание | Описание |
|--------|---------|------------|---------|
| `publish_placement` | critical | по запросу | Публикация поста (+ закрепление если pin) |
| `delete_published_post` | critical | по запросу | Удаление + release_escrow |
| `check_posts_alive` | default | каждые 5 мин | Мониторинг всех published постов |
| `check_sla_timers` | default | каждые 30 мин | SLA таймеры (pending 24ч → авто-отмена) |

---

## РАЗДЕЛ 8 — КОНСТАНТЫ

```python
PLATFORM_COMMISSION   = Decimal("0.15")
OWNER_SHARE           = Decimal("0.85")
YOOKASSA_FEE_RATE     = Decimal("0.035")
PAYOUT_FEE_RATE       = Decimal("0.015")
VELOCITY_MAX_RATIO    = Decimal("0.80")
VELOCITY_WINDOW_DAYS  = 30
MIN_TOPUP             = Decimal("500")
MAX_TOPUP             = Decimal("300000")
MIN_CAMPAIGN_BUDGET   = Decimal("2000")
MIN_PRICE_PER_POST    = Decimal("1000")
MIN_PAYOUT            = Decimal("1000")
MIN_POST_LIFE_RATIO   = Decimal("0.80")   # ← НОВАЯ
QUICK_TOPUP_AMOUNTS   = [500, 1000, 2000, 5000, 10000, 20000]
```

---

## РАЗДЕЛ 9 — КРИТИЧЕСКИЕ БАГИ (исправлены)

| ID | Проблема | Решение |
|----|---------|---------|
| RT-001 | `main:analytics` и `main:owner_analytics` — один handler | Разделить handlers: advertiser → `analytics.py::show_advertiser_analytics`, owner → `analytics.py::show_owner_analytics` |
| ESCROW-001 | `release_escrow()` при публикации → владелец мог удалить пост | `release_escrow()` только в `delete_published_post()` |
| PLAN-001 | `PLAN_LIMITS['agency']` → KeyError | Ключ `'business'` (HOTFIX применён) |
| REFERRAL-001 | Нет `referral_code` при создании пользователя → IntegrityError | Генерация в `terms_accept` handler |
| CAMPAIGN-001 | `campaigns.type` не существует в БД | Миграция 017 добавляет колонку |

---

## РАЗДЕЛ 10 — ЧТО УДАЛЕНО В v4.3

| Элемент | Где был | Статус |
|---------|---------|--------|
| B2B пакеты | `adv_menu`, `camp_step1`, handler `b2b.py` | ❌ Удалить |
| Callback `main:b2b` | `adv_menu` кнопка | ❌ Удалить |
| Broadcast для advertiser | `CampaignType.BROADCAST` в advertiser флоу | ❌ Удалить из advertiser |
| CryptoBot / crypto_payments | handlers, models, table | ❌ Удалить |
| Telegram Stars | любые ссылки на stars | ❌ Удалить |
| OpenRouter | config, `OPENROUTER_API_KEY` | ❌ Удалить |
| `NPD_TAX_RATE` | constants | ❌ Удалить |
| Тарифные цены 299/990/2999 | где встречаются | ❌ Заменить |

---

*RekHarborBot Bot Spec v4.3 | 14.03.2026*
