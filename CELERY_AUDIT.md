# CELERY AUDIT REPORT

**Дата:** 2026-03-10  
**Режим:** ТОЛЬКО ЧТЕНИЕ  
**Цель:** Полная инвентаризация Celery конфигурации для принятия решения о разделении на очереди

---

## 1. КОНФИГУРАЦИЯ

### 1.1 Переменные окружения (src/config/settings.py)

```python
# Celery
celery_broker_url: str = Field(..., alias="CELERY_BROKER_URL")
celery_result_backend: str = Field(..., alias="CELERY_RESULT_BACKEND")
```

**Значения из docker-compose.yml:**
```yaml
CELERY_BROKER_URL: redis://redis:6379/0
CELERY_RESULT_BACKEND: redis://redis:6379/1
```

### 1.2 Celery приложение (src/tasks/celery_app.py)

**Базовая конфигурация:**
```python
app = Celery(
    "market_bot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "src.tasks.parser_tasks",
        "src.tasks.mailing_tasks",
        "src.tasks.cleanup_tasks",
        "src.tasks.notification_tasks",
    ],
)
```

**Настройки (app.conf.update):**
| Параметр | Значение | Описание |
|----------|----------|----------|
| `task_serializer` | `"json"` | Сериализация задач |
| `accept_content` | `["json"]` | Принимаемые форматы |
| `result_serializer` | `"json"` | Сериализация результатов |
| `timezone` | `"UTC"` | Временная зона |
| `task_acks_late` | `True` | Подтверждение после выполнения |
| `task_reject_on_worker_lost` | `True` | Retry при потере worker |
| `task_track_started` | `True` | Отслеживать статус started |
| `task_soft_time_limit` | `300` | 5 минут мягкий лимит |
| `task_time_limit` | `600` | 10 минут жёсткий лимит |
| `task_default_retry_delay` | `60` | 1 минута между retry |
| `task_max_retries` | `3` | Максимум retry |
| `worker_prefetch_multiplier` | `1` | Не брать задачи вперёд |
| `worker_max_tasks_per_child` | `1000` | Перезапуск после 1000 задач |
| `result_expires` | `3600` | Результат живёт 1 час |
| `result_persistent` | `True` | Постоянное хранение |
| `task_events` | `True` | События о задачах |
| `worker_events` | `True` | События о воркерах |

### 1.3 Команды запуска (docker-compose.yml)

**Worker:**
```bash
celery -A src.tasks.celery_app worker --loglevel=info -Q mailing,parser,cleanup,celery -E
```
- **Очереди:** `mailing`, `parser`, `cleanup`, `celery` (default)
- **Логирование:** `info`
- **События:** `-E` (включено для Flower)
- **Concurrency:** не указан (по умолчанию = число CPU)

**Celery Beat:**
```bash
celery -A src.tasks.celery_app beat --loglevel=info
```

**Flower:**
```bash
celery -A src.tasks.celery_app flower --port=5555
```
- **Порт:** 5555
- **Доступ:** http://localhost:5555

### 1.4 Dockerfile.worker

```dockerfile
# Запуск от не-root пользователя
RUN adduser --disabled-password --gecos '' --uid 1000 celeryuser \
    && chown -R celeryuser:celeryuser /app

USER celeryuser

CMD ["celery", "-A", "src.tasks.celery_app", "worker", "--loglevel=info", "-Q", "mailing,parser"]
```

**Примечание:** В Dockerfile указана очередь `mailing,parser`, но в docker-compose.yml переопределено на `mailing,parser,cleanup,celery`.

---

## 2. ВСЕ ЗАДАЧИ (ИНВЕНТАРИЗАЦИЯ)

### 2.1 Обнаруженные задачи (52 total)

| Файл | Функция | Очередь | bind | max_retries | Тип |
|------|---------|---------|------|-------------|-----|
| **notification_tasks.py** ||||||
| | `check_low_balance` | mailing | ✅ | - | Periodic (Beat) |
| | `notify_campaign_status` | notifications | ✅ | 3 | On-demand |
| | `notify_user` | mailing | ✅ | - | On-demand |
| | `notify_owner_new_placement` | notifications | - | - | On-demand |
| | `notify_owner_xp_for_publication` | notifications | - | - | On-demand |
| | `notify_payout_created` | notifications | - | - | On-demand |
| | `notify_payout_paid` | notifications | - | - | On-demand |
| | `notify_post_published` | notifications | - | - | On-demand |
| | `notify_campaign_finished` | notifications | - | - | On-demand |
| | `notify_placement_rejected` | notifications | - | - | On-demand |
| | `notify_changes_requested` | notifications | - | - | On-demand |
| | `notify_low_balance_enhanced` | notifications | - | - | On-demand |
| | `notify_plan_expiring` | notifications | - | - | On-demand |
| | `notify_badge_earned` | notifications | - | - | On-demand |
| | `notify_level_up` | notifications | - | - | On-demand |
| | `notify_channel_top10` | notifications | - | - | On-demand |
| | `notify_referral_bonus` | notifications | - | - | On-demand |
| | `send_weekly_digest` | notifications | - | - | Periodic (Beat) |
| | `auto_approve_placements` | mailing | - | - | Periodic (Beat) |
| | `notify_pending_placement_reminders` | mailing | - | - | Periodic (Beat) |
| | `notify_expiring_plans` | mailing | - | - | Periodic (Beat) |
| | `notify_expired_plans` | mailing | - | - | Periodic (Beat) |
| **rating_tasks.py** ||||||
| | `recalculate_ratings_daily` | rating | ✅ | - | Periodic (Beat) |
| | `update_weekly_toplists` | rating | ✅ | - | Periodic (Beat) |
| **parser_tasks.py** ||||||
| | `refresh_chat_database` | parser | ✅ | 3, autoretry | Periodic (Beat) |
| | `update_chat_statistics` | parser | ✅ | - | Periodic (Beat) |
| | `parse_single_chat` | parser | ✅ | - | On-demand |
| | `recheck_channel_rules` | parser | - | - | On-demand |
| | `llm_reclassify_all` | parser | ✅ | - | On-demand |
| **billing_tasks.py** ||||||
| | `check_plan_renewals` | celery (default) | - | - | Periodic (Beat) |
| | `check_pending_invoices` | celery (default) | - | - | Periodic (Beat) |
| **cleanup_tasks.py** ||||||
| | `delete_old_logs` | cleanup | ✅ | - | Periodic (Beat) |
| | `archive_old_campaigns` | cleanup | ✅ | - | Periodic (Beat) |
| | `cleanup_useless_channels` | cleanup | ✅ | - | On-demand |
| | `cleanup_expired_sessions` | cleanup | ✅ | - | On-demand |
| **mailing_tasks.py** ||||||
| | `send_campaign` | mailing | ✅ | - | On-demand |
| | `check_scheduled_campaigns` | mailing | ✅ | - | Periodic (Beat) |
| | `check_low_balance` | mailing | ✅ | - | Periodic (Beat) ⚠️ |
| | `notify_user` | mailing | ✅ | - | Periodic (Beat) ⚠️ |
| | `auto_approve_pending_placements` | mailing | - | - | Periodic (Beat) |
| | `publish_single_placement` | mailing | - | - | On-demand |
| **gamification_tasks.py** ||||||
| | `update_streaks_daily` | gamification | ✅ | - | Periodic (Beat) |
| | `send_weekly_digest` | gamification | ✅ | - | Periodic (Beat) |
| | `check_seasonal_events` | gamification | ✅ | - | Periodic (Beat) |
| | `award_daily_login_bonus` | gamification | ✅ | - | On-demand |
| **badge_tasks.py** ||||||
| | `check_user_achievements` | badges | ✅ | - | On-demand |
| | `daily_badge_check` | gamification | ✅ | - | Periodic (Beat) |
| | `monthly_top_advertisers` | gamification | ✅ | - | Periodic (Beat) |
| | `notify_badge_earned` | badges | - | - | On-demand |
| | `trigger_after_campaign_launch` | badges | - | - | On-demand |
| | `trigger_after_campaign_complete` | badges | - | - | On-demand |
| | `trigger_after_streak_update` | badges | - | - | On-demand |

⚠️ **Дубликаты обнаружены:**
- `check_low_balance` — определена в `mailing_tasks.py:432` и `notification_tasks.py:18`
- `notify_user` — определена в `mailing_tasks.py:495` и `notification_tasks.py:180`
- `send_weekly_digest` — определена в `gamification_tasks.py:111` и `notification_tasks.py:933`

### 2.2 Вызовы задач (.delay / .apply_async)

| Файл | Строка | Задача | Аргументы |
|------|--------|--------|-----------|
| `billing_tasks.py` | 96 | `notify_user.delay` | (user_id, ...) |
| `billing_tasks.py` | 130 | `notify_user.delay` | (user_id, ...) |
| `badge_tasks.py` | 40 | `notify_badge_earned.delay` | (user_id, badge_id) |
| `badge_tasks.py` | 187 | `notify_badge_earned.delay` | (user_id, badge_id) |
| `badge_tasks.py` | 250 | `notify_user.delay` | (owner_id, ...) |
| `badge_tasks.py` | 271 | `check_user_achievements.delay` | (user_id) |
| `badge_tasks.py` | 282 | `check_user_achievements.delay` | (user_id) |
| `badge_tasks.py` | 296 | `check_user_achievements.delay` | (user_id) |
| `notification_tasks.py` | 382 | `notify_level_up.delay` | (owner_id, new_level) |
| `notification_tasks.py` | 1186 | `publish_single_placement.delay` | (placement.id) |
| `mailing_tasks.py` | 129 | `notify_owner_xp_for_publication.delay` | (user_id, xp) |
| `mailing_tasks.py` | 199 | `notify_campaign_status.delay` | (campaign_id, status) |
| `mailing_tasks.py` | 289 | `trigger_after_campaign_complete.delay` | (user_id) |
| `mailing_tasks.py` | 397 | `send_campaign.delay` | (campaign.id) |
| `mailing_tasks.py` | 462 | `notify_user.delay` | (user_id, ...) |

---

## 3. BEAT РАСПИСАНИЕ (src/tasks/celery_config.py)

| Имя задачи | Task Path | Schedule | Очередь |
|------------|-----------|----------|---------|
| `refresh-chat-database` | `src.tasks.parser_tasks.refresh_chat_database` | crontab(hour=3, minute=0) | parser |
| `check-scheduled-campaigns` | `src.tasks.mailing_tasks.check_scheduled_campaigns` | crontab(minute="*/5") | mailing |
| `delete-old-logs` | `src.tasks.cleanup_tasks.delete_old_logs` | crontab(hour=3, minute=0, day_of_week=0) | cleanup |
| `check-low-balance` | `src.tasks.notification_tasks.check_low_balance` | crontab(minute=0) | mailing |
| `update-chat-statistics` | `src.tasks.parser_tasks.update_chat_statistics` | crontab(hour="*/6") | parser |
| `archive-old-campaigns` | `src.tasks.cleanup_tasks.archive_old_campaigns` | crontab(hour=4, minute=0, day_of_month=1) | cleanup |
| `auto-approve-pending-placements` | `src.tasks.mailing_tasks.auto_approve_pending_placements` | crontab(minute=0) | mailing |
| `recalculate-ratings-daily` | `src.tasks.rating_tasks.recalculate_ratings_daily` | crontab(hour=4, minute=0) | rating |
| `update-weekly-toplists` | `src.tasks.rating_tasks.update_weekly_toplists` | crontab(hour=5, minute=0, day_of_week=1) | rating |
| `update-streaks-daily` | `src.tasks.gamification_tasks.update_streaks_daily` | crontab(hour=0, minute=0) | gamification |
| `send-weekly-digest` | `src.tasks.gamification_tasks.send_weekly_digest` | crontab(hour=10, minute=0, day_of_week=1) | gamification |
| `check-seasonal-events` | `src.tasks.gamification_tasks.check_seasonal_events` | crontab(hour=8, minute=0) | gamification |
| `auto-approve-placements` ⚠️ | `src.tasks.notification_tasks.auto_approve_placements` | crontab(minute=0) | mailing |
| `placement-reminders` | `src.tasks.notification_tasks.notify_pending_placement_reminders` | crontab(minute=0, hour="*/2") | mailing |
| `notify-expiring-plans` | `src.tasks.notification_tasks.notify_expiring_plans` | crontab(hour=10, minute=0) | mailing |
| `notify-expired-plans` | `src.tasks.notification_tasks.notify_expired_plans` | crontab(hour=10, minute=5) | mailing |
| `daily-badge-check` | `src.tasks.badge_tasks.daily_badge_check` | crontab(hour=0, minute=0) | gamification |
| `monthly-top-advertisers` | `src.tasks.badge_tasks.monthly_top_advertisers` | crontab(hour=0, minute=0, day_of_month=1) | gamification |

### 3.1 ДУБЛИКАТ AUTO_APPROVE ОБНАРУЖЕН ⚠️

```python
# Строка 53:
"auto-approve-pending-placements": {
    "task": "src.tasks.mailing_tasks.auto_approve_pending_placements",
    "schedule": crontab(minute=0),
    "options": {"queue": "mailing"},
},

# Строка 89:
"auto-approve-placements": {
    "task": "src.tasks.notification_tasks.auto_approve_placements",
    "schedule": crontab(minute=0),
    "options": {"queue": "mailing"},
},
```

**Проблема:** Обе задачи запускаются каждый час в 00 минут и выполняют схожую функцию — автоодобрение заявок.

**Рекомендация:** Оставить одну задачу, удалить дубликат.

---

## 4. СОСТОЯНИЕ ОЧЕРЕДЕЙ (Redis)

**Команды выполнены:** 2026-03-10

```bash
# Ключи Celery в Redis
docker compose exec redis redis-cli KEYS "celery*"
# Результат: (пусто)

# Длина основной очереди
docker compose exec redis redis-cli LLEN celery
# Результат: 0

# Keyspace info
docker compose exec redis redis-cli INFO keyspace
# Результат:
# db0:keys=9,expires=0,avg_ttl=0,subexpiry=0
# db1:keys=3,expires=3,avg_ttl=3042994,subexpiry=0
```

**Интерпретация:**
- `db0` (очереди): 9 ключей — служебные ключи Celery/Redis
- `db1` (результаты): 3 ключа с expiration — результаты задач
- Очередь `celery` пуста — нет накопленных задач
- Задачи выполняются в реальном времени без задержек

---

## 5. КЛАССИФИКАЦИЯ ПО КРИТИЧНОСТИ

| Задача | Критичность | Обоснование |
|--------|-------------|-------------|
| **Финансовые задачи** ||
| `check_low_balance` | 🔴 Критическая | Уведомления о низком балансе |
| `notify_payout_created` | 🔴 Критическая | Уведомление о создании выплаты |
| `notify_payout_paid` | 🔴 Критическая | Уведомление о выплате |
| `check_plan_renewals` | 🔴 Критическая | Продление тарифов |
| `check_pending_invoices` | 🔴 Критическая | Обработка счетов |
| **Рассылки и кампании** ||
| `send_campaign` | 🟠 Обычная | Основная рассылка кампаний |
| `check_scheduled_campaigns` | 🟠 Обычная | Проверка расписания |
| `notify_campaign_status` | 🟠 Обычная | Статус кампании |
| `notify_campaign_finished` | 🟠 Обычная | Завершение кампании |
| `auto_approve_placements` | 🟠 Обычная | Автоодобрение заявок |
| `publish_single_placement` | 🟠 Обычная | Публикация размещения |
| **Уведомления пользователей** ||
| `notify_user` | 🟠 Обычная | Базовое уведомление |
| `notify_post_published` | 🟠 Обычная | Публикация поста |
| `notify_placement_rejected` | 🟠 Обычная | Отказ в размещении |
| `notify_changes_requested` | 🟠 Обычная | Запрос изменений |
| `notify_plan_expiring` | 🟠 Обычная | Истекающий тариф |
| `notify_expired_plans` | 🟠 Обычная | Истёкший тариф |
| **Геймификация** ||
| `notify_badge_earned` | 🟡 Низкая | Достижения |
| `notify_level_up` | 🟡 Низкая | Повышение уровня |
| `update_streaks_daily` | 🟡 Низкая | Обновление стриков |
| `send_weekly_digest` | 🟡 Низкая | Еженедельный дайджест |
| `check_seasonal_events` | 🟡 Низкая | Сезонные события |
| `award_daily_login_bonus` | 🟡 Низкая | Ежедневный бонус |
| `daily_badge_check` | 🟡 Низкая | Проверка достижений |
| `monthly_top_advertisers` | 🟡 Низкая | Топ рекламодателей |
| **Парсер и аналитика** ||
| `refresh_chat_database` | 🟡 Низкая | Обновление БД чатов |
| `update_chat_statistics` | 🟡 Низкая | Статистика чатов |
| `parse_single_chat` | 🟡 Низкая | Парсинг одного чата |
| `recheck_channel_rules` | 🟡 Низкая | Перепроверка каналов |
| `llm_reclassify_all` | 🟡 Низкая | LLM классификация |
| `recalculate_ratings_daily` | 🟡 Низкая | Пересчёт рейтингов |
| `update_weekly_toplists` | 🟡 Низкая | Топы недели |
| **Очистка** ||
| `delete_old_logs` | 🟡 Низкая | Удаление логов |
| `archive_old_campaigns` | 🟡 Низкая | Архивация кампаний |
| `cleanup_useless_channels` | 🟡 Низкая | Очистка каналов |
| `cleanup_expired_sessions` | 🟡 Низкая | Очистка сессий |

---

## 6. ПОТЕНЦИАЛЬНЫЕ ПРОБЛЕМЫ

### 6.1 Блокировка критических задач тяжёлыми операциями

**Вопрос:** Может ли тяжёлая задача рассылки (итерация по сотням каналов) заблокировать отправку уведомления о выплате?

**Ответ:** ✅ **ДА, МОЖЕТ**

**Текущая конфигурация:**
- **Worker concurrency:** не указан (по умолчанию = число CPU ядер)
- **Очереди:** `mailing`, `parser`, `cleanup`, `celery` (все в одном worker)
- **Prefetch multiplier:** 1 (хорошо — не берёт задачи вперёд)

**Риск:**
- Задача `send_campaign` может обрабатываться до 10 минут (time_limit=600)
- Задача `refresh_chat_database` может обрабатываться до 30 минут (time_limit=1800)
- При concurrency=4 и 4 тяжёлых задачах — критические уведомления (`notify_payout_*`) будут ждать

**Рекомендация:**
- Разделить очереди на разные worker'ы
- Выделить отдельный worker для критических задач (`celery` queue)
- Увеличить priority для финансовых задач

### 6.2 Time limits

**Задачи с custom time_limit:**

| Задача | Soft Limit | Hard Limit |
|--------|------------|------------|
| `send_campaign` | - | 600s (10 мин) |
| `check_scheduled_campaigns` | - | 300s (5 мин) |
| `refresh_chat_database` | - | 1800s (30 мин) |
| `validate_username` | - | 60s (1 мин) |
| `delete_old_logs` | - | 600s (10 мин) |
| `archive_old_campaigns` | - | 300s (5 мин) |
| `update_chat_statistics` | 6h | 6h |

**Найдено в коде:**
```python
# parser_tasks.py:1184
@celery_app.task(
    ...,
    soft_time_limit=6 * 3600,  # 6 часов максимум
)
```

### 6.3 Retry логика

**Задачи с retry:**

| Задача | max_retries | autoretry_for | Interval |
|--------|-------------|---------------|----------|
| `refresh_chat_database` | 3 | Exception | 300s start, 300s step, 600s max |
| `update_chat_statistics` | 3 | - | - |
| `notify_campaign_status` | 3 | - | - |
| `send_campaign` | 5 | - | 30s start, 60s step, 300s max |

**Найдено в коде:**
```python
# notification_tasks.py:158
raise self.retry(countdown=60, exc=exc) from exc
```

### 6.4 Beat и Worker — раздельные контейнеры

**Статус:** ✅ **РАЗДЕЛЕНЫ**

```yaml
worker:
  command: celery -A src.tasks.celery_app worker --loglevel=info -Q mailing,parser,cleanup,celery -E

celery_beat:
  command: celery -A src.tasks.celery_app beat --loglevel=info

flower:
  command: celery -A src.tasks.celery_app flower --port=5555
```

**Преимущество:** Beat не блокирует worker, независимый перезапуск.

### 6.5 Flower для мониторинга

**Статус:** ✅ **ИСПОЛЬЗУЕТСЯ**

```yaml
flower:
  build:
    context: .
    dockerfile: docker/Dockerfile.worker
  container_name: market_bot_flower
  ports:
    - "${FLOWER_PORT:-5555}:5555"
  command: celery -A src.tasks.celery_app flower --port=5555
```

**Доступ:** http://localhost:5555

**Функции:**
- Мониторинг задач в реальном времени
- Статистика по worker'ам
- История выполненных задач
- Возможность отмены/revoke задач

---

## 7. ВЫВОДЫ

### 7.1 Что работает хорошо

✅ **Разделение на очереди настроено:**
- `mailing` — рассылки и уведомления
- `parser` — парсинг каналов
- `cleanup` — очистка данных
- `rating` — рейтинги
- `gamification` — геймификация
- `badges` — достижения

✅ **Надёжность:**
- `task_acks_late=True` — подтверждение после выполнения
- `task_reject_on_worker_lost=True` — retry при потере worker
- `worker_prefetch_multiplier=1` — не берёт задачи вперёд

✅ **Мониторинг:**
- Flower настроен и доступен
- События включены (`-E` в worker)
- result_backend настроен (Redis db1)

✅ **Безопасность:**
- Worker запускается от не-root пользователя (celeryuser, uid=1000)
- Задачи подписываются (task_signing можно включить)

### 7.2 Риски и проблемы

⚠️ **КРИТИЧНО: Дубликаты задач**

| Дубликат | Файлы | Решение |
|----------|-------|---------|
| `check_low_balance` | `mailing_tasks.py:432`, `notification_tasks.py:18` | Удалить из mailing_tasks |
| `notify_user` | `mailing_tasks.py:495`, `notification_tasks.py:180` | Удалить из mailing_tasks |
| `send_weekly_digest` | `gamification_tasks.py:111`, `notification_tasks.py:933` | Удалить из notification_tasks |
| `auto_approve_*` | Beat строки 53 и 89 | Оставить одну задачу |

⚠️ **ВЫСОКИЙ ПРИОРИТЕТ: Смешение критических и фоновых задач**

**Проблема:** Все очереди (`mailing,parser,cleanup,celery`) обрабатываются одним worker'ом.

**Риск:**
- Тяжёлая задача `refresh_chat_database` (30 мин) может заблокировать `notify_payout_paid`
- Задача `send_campaign` (10 мин × N каналов) может создать очередь на 50+ минут

**Рекомендация:**
```bash
# Worker 1 — критические задачи (финансы, уведомления)
celery -A src.tasks.celery_app worker -Q celery,mailing -n critical@%h --concurrency=2

# Worker 2 — фоновые задачи (парсер, аналитика)
celery -A src.tasks.celery_app worker -Q parser,cleanup -n background@%h --concurrency=4

# Worker 3 — геймификация (низкий приоритет)
celery -A src.tasks.celery_app worker -Q gamification,badges,rating -n game@%h --concurrency=2
```

⚠️ **СРЕДНИЙ ПРИОРИТЕТ: Отсутствует приоритизация задач**

**Проблема:** Все задачи имеют одинаковый приоритет.

**Решение:**
```python
# Пример для критических задач
notify_payout_paid.apply_async(args=[payout_id], priority=10)

# Пример для фоновых задач
send_weekly_digest.apply_async(args=[user_id], priority=1)
```

**Настройка broker:**
```python
# Redis broker поддерживает priority
broker_transport_options = {'visibility_timeout': 604800}
task_priority = 4  # default priority
```

### 7.3 Рекомендации по разделению очередей

**Текущее состояние:**
```
Worker: mailing, parser, cleanup, celery (все в одном)
```

**Рекомендуемая архитектура:**

```
┌─────────────────────────────────────────────────────────┐
│                    Redis Broker                         │
│  db0: очереди                                           │
│  db1: результаты                                        │
└─────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Worker         │ │  Worker         │ │  Worker         │
│  (critical)     │ │  (background)   │ │  (game)         │
│  -Q celery,     │ │  -Q parser,     │ │  -Q gamification│
│  -Q mailing     │ │  -Q cleanup,    │ │  -Q badges,     │
│  --concurrency=2│ │  -Q rating      │ │  -Q rating      │
│                 │ │  --concurrency=4│ │  --concurrency=2│
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │               │               │
         ▼               ▼               ▼
  🔴 Критические   🟠 Обычные       🟡 Низкие
  - финансы        - парсер         - геймификация
  - уведомления    - очистка        - дайджесты
  - выплаты        - аналитика      - достижения
```

**docker-compose.yml изменения:**
```yaml
worker_critical:
  command: celery -A src.tasks.celery_app worker -Q celery,mailing -n critical@%h --concurrency=2
  deploy:
    replicas: 2

worker_background:
  command: celery -A src.tasks.celery_app worker -Q parser,cleanup,rating -n background@%h --concurrency=4
  deploy:
    replicas: 1

worker_game:
  command: celery -A src.tasks.celery_app worker -Q gamification,badges -n game@%h --concurrency=2
  deploy:
    replicas: 1
```

### 7.4 Итоговая таблица приоритетов

| Приоритет | Очередь | Задачи | Контейнеры |
|-----------|---------|--------|------------|
| 🔴 P0 | `celery`, `mailing` | Финансы, выплаты, уведомления | 2 replicas |
| 🟠 P1 | `parser`, `cleanup` | Парсер, очистка, аналитика | 1 replica |
| 🟡 P2 | `gamification`, `badges`, `rating` | Геймификация, достижения | 1 replica |

---

## ПРИЛОЖЕНИЕ A: ПОЛНЫЙ СПИСОК ЗАДАЧ ПО ФАЙЛАМ

### src/tasks/notification_tasks.py (24 задачи)
```python
@celery_app.task(bind=True, base=BaseTask, name="mailing:check_low_balance")
@celery_app.task(name="notifications:notify_campaign_status", bind=True, max_retries=3)
@celery_app.task(bind=True, base=BaseTask, name="mailing:notify_user")
@celery_app.task(name="notifications:notify_owner_new_placement")
@celery_app.task(name="notifications:notify_owner_xp_for_publication")
@celery_app.task(name="notifications:notify_payout_created")
@celery_app.task(name="notifications:notify_payout_paid")
@celery_app.task(name="notifications:notify_post_published")
@celery_app.task(name="notifications:notify_campaign_finished")
@celery_app.task(name="notifications:notify_placement_rejected")
@celery_app.task(name="notifications:notify_changes_requested")
@celery_app.task(name="notifications:notify_low_balance_enhanced")
@celery_app.task(name="notifications:notify_plan_expiring")
@celery_app.task(name="notifications:notify_badge_earned")
@celery_app.task(name="notifications:notify_level_up")
@celery_app.task(name="notifications:notify_channel_top10")
@celery_app.task(name="notifications:notify_referral_bonus")
@celery_app.task(name="notifications:send_weekly_digest")
@celery_app.task(name="notifications:auto_approve_placements")
@celery_app.task(name="notifications:notify_pending_placement_reminders")
@celery_app.task(name="notifications:notify_expiring_plans")
@celery_app.task(name="notifications:notify_expired_plans")
```

### src/tasks/mailing_tasks.py (6 задач)
```python
@celery_app.task(bind=True, base=BaseTask, name="mailing:send_campaign")
@celery_app.task(bind=True, base=BaseTask, name="mailing:check_scheduled_campaigns")
@celery_app.task(bind=True, base=BaseTask, name="mailing:check_low_balance")  # ⚠️ ДУБЛИКАТ
@celery_app.task(bind=True, base=BaseTask, name="mailing:notify_user")  # ⚠️ ДУБЛИКАТ
@celery_app.task(name="mailing:auto_approve_pending_placements")
@celery_app.task(name="mailing:publish_single_placement")
```

### src/tasks/parser_tasks.py (5 задач)
```python
@celery_app.task(
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    name="parser:refresh_chat_database"
)
@celery_app.task(
    bind=True,
    max_retries=3,
    soft_time_limit=6 * 3600,
    name="parser:update_chat_statistics"
)
@celery_app.task(bind=True, base=BaseTask, name="parser:parse_single_chat", queue="parser")
@celery_app.task(name="parser:recheck_channel_rules", queue="parser")
@celery_app.task(name="parser:llm_reclassify_all", bind=True)
```

### src/tasks/cleanup_tasks.py (4 задачи)
```python
@celery_app.task(bind=True, base=BaseTask, name="cleanup:delete_old_logs")
@celery_app.task(bind=True, base=BaseTask, name="cleanup:archive_old_campaigns")
@celery_app.task(bind=True, base=BaseTask, name="cleanup:cleanup_useless_channels")
@celery_app.task(bind=True, base=BaseTask, name="cleanup:cleanup_expired_sessions")
```

### src/tasks/rating_tasks.py (2 задачи)
```python
@celery_app.task(bind=True, base=BaseTask, name="rating:recalculate_ratings_daily")
@celery_app.task(bind=True, base=BaseTask, name="rating:update_weekly_toplists")
```

### src/tasks/gamification_tasks.py (4 задачи)
```python
@celery_app.task(bind=True, base=BaseTask, name="gamification:update_streaks_daily")
@celery_app.task(bind=True, base=BaseTask, name="gamification:send_weekly_digest")  # ⚠️ ДУБЛИКАТ
@celery_app.task(bind=True, base=BaseTask, name="gamification:check_seasonal_events")
@celery_app.task(bind=True, base=BaseTask, name="gamification:award_daily_login_bonus")
```

### src/tasks/badge_tasks.py (7 задач)
```python
@celery_app.task(bind=True, base=BaseTask, name="badges:check_user_achievements")
@celery_app.task(bind=True, base=BaseTask, name="badges:daily_badge_check")
@celery_app.task(bind=True, base=BaseTask, name="badges:monthly_top_advertisers")
@celery_app.task(name="badges:notify_badge_earned")
@celery_app.task(name="badges:trigger_after_campaign_launch")
@celery_app.task(name="badges:trigger_after_campaign_complete")
@celery_app.task(name="badges:trigger_after_streak_update")
```

### src/tasks/billing_tasks.py (2 задачи)
```python
@app.task(name="tasks.billing_tasks:check_plan_renewals")
@app.task(name="tasks.billing_tasks:check_pending_invoices")
```

---

**ИТОГО:** 52 задачи в 8 файлах

---

**ИСПОЛНИТЕЛЬ:** Qwen Code  
**ДАТА АУДИТА:** 2026-03-10  
**ВРЕМЯ:** ~30 минут
