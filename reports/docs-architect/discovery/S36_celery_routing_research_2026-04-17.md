# S-36 Celery Task Routing Audit

**Sprint:** S-36 | **Phase:** Research (read-only)
**Date:** 2026-04-17 | **Scope:** `src/tasks/`

---

## Ключевые находки (Executive Summary)

| Критичность | Проблема |
|-------------|----------|
| 🔴 КРИТИЧНО | `celery_config.py` → BEAT_SCHEDULE и TASK_ROUTES — **мёртвый код**, не загружается в celery_app.py |
| 🔴 КРИТИЧНО | 6 SLA-задач placement (check_owner_sla, check_payment_sla, check_counter_sla, check_escrow_sla, check_escrow_stuck, check_published_posts_health) **НЕ в активном Beat расписании** — никогда не запускаются автоматически |
| 🔴 КРИТИЧНО | 13 задач (gamification:*, badges:*, integrity:*, dispute:*) уходят в **default "celery" queue** |
| 🟠 ВАЖНО | Активный task_routes содержит только 4 маршрута, `publication.*` — мёртвый маршрут |
| 🟠 ВАЖНО | 4 задачи с `notifications:` префиксом имеют `queue="mailing"` в декораторе — несогласованность |
| 🟡 НИЗКОЕ | `gamification_tasks`, `badge_tasks`, `integrity_tasks`, `tax_tasks` — не в `include=[]` (но покрыты autodiscover) |
| 🟡 НИЗКОЕ | `tax:calendar_reminder` упоминается в мёртвом BEAT_SCHEDULE, но задача не определена в tax_tasks.py |

---

## Таблица 1: все задачи

| # | module | task_name | queue_param (decorator) | effective_queue | in_include | in_task_routes | in_beat |
|---|--------|-----------|------------------------|-----------------|------------|----------------|---------|
| 1 | parser_tasks | `parser:refresh_chat_database` | — | parser (route) | ✅ | ✅ mailing.* | ❌ |
| 2 | parser_tasks | `parser:refresh_chat_database_business` | — | parser (route) | ✅ | ✅ | ✅ active |
| 3 | parser_tasks | `parser:refresh_chat_database_marketing` | — | parser (route) | ✅ | ✅ | ✅ active |
| 4 | parser_tasks | `parser:refresh_chat_database_it` | — | parser (route) | ✅ | ✅ | ✅ active |
| 5 | parser_tasks | `parser:refresh_chat_database_lifestyle` | — | parser (route) | ✅ | ✅ | ✅ active |
| 6 | parser_tasks | `parser:refresh_chat_database_health` | — | parser (route) | ✅ | ✅ | ✅ active |
| 7 | parser_tasks | `parser:refresh_chat_database_education` | — | parser (route) | ✅ | ✅ | ✅ active |
| 8 | parser_tasks | `parser:refresh_chat_database_news` | — | parser (route) | ✅ | ✅ | ✅ active |
| 9 | parser_tasks | `parser:collect_all_chats_stats` | parser | parser | ✅ | ✅ | ✅ active |
| 10 | parser_tasks | `parser:parse_single_chat` | parser | parser | ✅ | ✅ | ❌ |
| 11 | parser_tasks | `parser:recheck_channel_rules` | parser | parser | ✅ | ✅ | ❌ |
| 12 | parser_tasks | `parser:llm_reclassify_all` | — | parser (route) | ✅ | ✅ | ❌ |
| 13 | parser_tasks | `parser:autoclassify_channels` | parser | parser | ✅ | ✅ | ❌ |
| 14 | cleanup_tasks | `cleanup:delete_old_logs` | — | cleanup (route) | ✅ | ✅ | ✅ active |
| 15 | cleanup_tasks | `cleanup:archive_old_campaigns` | — | cleanup (route) | ✅ | ✅ | ❌ |
| 16 | cleanup_tasks | `cleanup:cleanup_useless_channels` | — | cleanup (route) | ✅ | ✅ | ❌ |
| 17 | cleanup_tasks | `cleanup:cleanup_expired_sessions` | — | cleanup (route) | ✅ | ✅ | ❌ |
| 18 | notification_tasks | `mailing:check_low_balance` | — | mailing (route) | ✅ | ✅ | ❌ |
| 19 | notification_tasks | `mailing:notify_user` | — | mailing (route) | ✅ | ✅ | ❌ |
| 20 | notification_tasks | `notifications:notify_campaign_status` | notifications | notifications | ✅ | ❌ | ❌ |
| 21 | notification_tasks | `notifications:notify_owner_new_placement` | notifications | notifications | ✅ | ❌ | ❌ |
| 22 | notification_tasks | `notifications:notify_owner_xp_for_publication` | notifications | notifications | ✅ | ❌ | ❌ |
| 23 | notification_tasks | `notifications:notify_payout_created` | notifications | notifications | ✅ | ❌ | ❌ |
| 24 | notification_tasks | `notifications:notify_payout_paid` | notifications | notifications | ✅ | ❌ | ❌ |
| 25 | notification_tasks | `payouts:notify_admin_new_payout` | background | background | ✅ | ❌ | ❌ |
| 26 | notification_tasks | `notifications:notify_post_published` | notifications | notifications | ✅ | ❌ | ❌ |
| 27 | notification_tasks | `notifications:notify_campaign_finished` | notifications | notifications | ✅ | ❌ | ❌ |
| 28 | notification_tasks | `notifications:notify_placement_rejected` | notifications | notifications | ✅ | ❌ | ❌ |
| 29 | notification_tasks | `notifications:notify_changes_requested` | notifications | notifications | ✅ | ❌ | ❌ |
| 30 | notification_tasks | `notifications:notify_low_balance_enhanced` | notifications | notifications | ✅ | ❌ | ❌ |
| 31 | notification_tasks | `notifications:notify_plan_expiring` | notifications | notifications | ✅ | ❌ | ❌ |
| 32 | notification_tasks | `notifications:notify_badge_earned` | notifications | notifications | ✅ | ❌ | ❌ |
| 33 | notification_tasks | `notifications:notify_level_up` | notifications | notifications | ✅ | ❌ | ❌ |
| 34 | notification_tasks | `notifications:notify_channel_top10` | notifications | notifications | ✅ | ❌ | ❌ |
| 35 | notification_tasks | `notifications:notify_referral_bonus` | notifications | notifications | ✅ | ❌ | ❌ |
| 36 | notification_tasks | `notifications:auto_approve_placements` | **mailing** ⚠️ | mailing | ✅ | ❌ | ❌ |
| 37 | notification_tasks | `notifications:notify_pending_placement_reminders` | **mailing** ⚠️ | mailing | ✅ | ❌ | ❌ |
| 38 | notification_tasks | `notifications:notify_expiring_plans` | **mailing** ⚠️ | mailing | ✅ | ❌ | ❌ |
| 39 | notification_tasks | `notifications:notify_expired_plans` | **mailing** ⚠️ | mailing | ✅ | ❌ | ❌ |
| 40 | billing_tasks | `billing:check_plan_renewals` | billing | billing | ✅ | ❌ | ✅ active |
| 41 | billing_tasks | `billing:check_pending_invoices` | billing | billing | ✅ | ❌ | ❌ (DEPRECATED) |
| 42 | placement_tasks | `placement:check_owner_response_sla` | worker_critical | worker_critical | ✅ | ❌ | ⚠️ dead-config only |
| 43 | placement_tasks | `placement:check_payment_sla` | worker_critical | worker_critical | ✅ | ❌ | ⚠️ dead-config only |
| 44 | placement_tasks | `placement:check_counter_offer_sla` | worker_critical | worker_critical | ✅ | ❌ | ⚠️ dead-config only |
| 45 | placement_tasks | `placement:publish_placement` | worker_critical | worker_critical | ✅ | ❌ | ❌ |
| 46 | placement_tasks | `placement:retry_failed_publication` | worker_critical | worker_critical | ✅ | ❌ | ❌ |
| 47 | placement_tasks | `placement:check_published_posts_health` | worker_critical | worker_critical | ✅ | ❌ | ⚠️ dead-config only |
| 48 | placement_tasks | `placement:check_escrow_sla` | worker_critical | worker_critical | ✅ | ❌ | ⚠️ dead-config only |
| 49 | placement_tasks | `placement:schedule_placement_publication` | worker_critical | worker_critical | ✅ | ❌ | ❌ |
| 50 | placement_tasks | `placement:delete_published_post` | worker_critical | worker_critical | ✅ | ❌ | ❌ |
| 51 | placement_tasks | `placement:check_scheduled_deletions` | worker_critical | worker_critical | ✅ | ❌ | ✅ active |
| 52 | placement_tasks | `placement:check_escrow_stuck` | worker_critical | worker_critical | ✅ | ❌ | ⚠️ dead-config only |
| 53 | ord_tasks | `ord:register_creative` | background | background | ✅ | ❌ | ❌ |
| 54 | ord_tasks | `ord:report_publication` | background | background | ✅ | ❌ | ❌ |
| 55 | ord_tasks | `ord:poll_erid_status` | background | background | ✅ | ❌ | ❌ |
| 56 | document_ocr_tasks | `document_ocr:process_document` | worker_critical | worker_critical | ✅ | ❌ | ❌ |
| 57 | dispute_tasks | `dispute:resolve_financial` | — | **celery (default)** 🔴 | ✅ | ❌ | ❌ |
| 58 | gamification_tasks | `gamification:update_streaks_daily` | — | **celery (default)** 🔴 | ❌ | ❌ | ⚠️ dead-config only |
| 59 | gamification_tasks | `gamification:send_weekly_digest` | — | **celery (default)** 🔴 | ❌ | ❌ | ⚠️ dead-config only |
| 60 | gamification_tasks | `gamification:check_seasonal_events` | — | **celery (default)** 🔴 | ❌ | ❌ | ⚠️ dead-config only |
| 61 | gamification_tasks | `gamification:award_daily_login_bonus` | — | **celery (default)** 🔴 | ❌ | ❌ | ❌ |
| 62 | badge_tasks | `badges:check_user_achievements` | — | **celery (default)** 🔴 | ❌ | ❌ | ❌ |
| 63 | badge_tasks | `badges:daily_badge_check` | — | **celery (default)** 🔴 | ❌ | ❌ | ⚠️ dead-config only |
| 64 | badge_tasks | `badges:monthly_top_advertisers` | — | **celery (default)** 🔴 | ❌ | ❌ | ⚠️ dead-config only |
| 65 | badge_tasks | `badges:notify_badge_earned` | — | **celery (default)** 🔴 | ❌ | ❌ | ❌ |
| 66 | badge_tasks | `badges:trigger_after_campaign_launch` | — | **celery (default)** 🔴 | ❌ | ❌ | ❌ |
| 67 | badge_tasks | `badges:trigger_after_campaign_complete` | — | **celery (default)** 🔴 | ❌ | ❌ | ❌ |
| 68 | badge_tasks | `badges:trigger_after_streak_update` | — | **celery (default)** 🔴 | ❌ | ❌ | ❌ |
| 69 | integrity_tasks | `integrity:check_data_integrity` | — | **celery (default)** 🔴 | ❌ | ❌ | ⚠️ dead-config only |
| — | tax_tasks | *(нет задач — только helper-функции)* | — | — | ❌ | ❌ | — |

**Итого:** 69 задач в 10 модулях. `tax_tasks.py` не содержит ни одного `@celery_app.task`.

---

## Таблица 2: очереди

| queue | tasks_count | prefixes/задачи |
|-------|-------------|-----------------|
| `parser` | 13 | `parser:*` |
| `worker_critical` | 11 | `placement:*`, `document_ocr:*` |
| `notifications` | 15 | `notifications:notify_*` (15 задач без авто/периодических) |
| `mailing` | 6 | `mailing:check_low_balance`, `mailing:notify_user`, `notifications:auto_approve_placements`, `notifications:notify_pending_placement_reminders`, `notifications:notify_expiring_plans`, `notifications:notify_expired_plans` |
| `cleanup` | 4 | `cleanup:*` |
| `billing` | 2 | `billing:*` |
| `background` | 4 | `ord:*` (3), `payouts:notify_admin_new_payout` (1) |
| **`celery` (default)** 🔴 | **13** | `dispute:resolve_financial`, `gamification:*` (4), `badges:*` (7), `integrity:check_data_integrity` |

**Зарегистрированные именованные очереди:** parser, worker_critical, notifications, mailing, cleanup, billing, background  
**Незарегистрированные очереди (нет entry в конфиге воркеров):** `celery` (default), `notifications` (нет в QUEUE_CONFIG), `billing` (нет в QUEUE_CONFIG)

---

## Таблица 3: расхождения в `mailing:*` и `notifications:*`

| task_name | prefix | queue_in_decorator | queue_from_routes | effective_queue | Проблема |
|-----------|--------|-------------------|-------------------|-----------------|----------|
| `mailing:check_low_balance` | mailing: | — | mailing (matched) | mailing | ✅ OK |
| `mailing:notify_user` | mailing: | — | mailing (matched) | mailing | ✅ OK |
| `notifications:notify_campaign_status` | notifications: | notifications | — (no route match) | notifications | ✅ OK (decorator) |
| `notifications:auto_approve_placements` | notifications: | **mailing** | — (no route match) | **mailing** | ⚠️ префикс ≠ очередь |
| `notifications:notify_pending_placement_reminders` | notifications: | **mailing** | — (no route match) | **mailing** | ⚠️ префикс ≠ очередь |
| `notifications:notify_expiring_plans` | notifications: | **mailing** | — (no route match) | **mailing** | ⚠️ префикс ≠ очередь |
| `notifications:notify_expired_plans` | notifications: | **mailing** | — (no route match) | **mailing** | ⚠️ префикс ≠ очередь |
| `payouts:notify_admin_new_payout` | payouts: | background | — | background | ⚠️ в notification_tasks.py, prefix=payouts: |

**Вывод:** Логический сплит — периодические/системные уведомления → `mailing`, событийные уведомления → `notifications`. Сплит функциональный, но не согласован с именованием.

---

## Таблица 4: задачи на default queue (не должно быть)

Все 13 задач попадают в `celery` queue потому что:
1. Нет `queue=` в декораторе
2. Нет совпадающего маршрута в активном `task_routes` (только 4 маршрута: mailing.*, parser.*, cleanup.*, publication.*)

| task_name | file | bind | Рекомендуемая очередь |
|-----------|------|------|-----------------------|
| `dispute:resolve_financial` | dispute_tasks.py:19 | ✅ | worker_critical |
| `gamification:update_streaks_daily` | gamification_tasks.py:67 | ✅ | gamification (или background) |
| `gamification:send_weekly_digest` | gamification_tasks.py:119 | ✅ | gamification |
| `gamification:check_seasonal_events` | gamification_tasks.py:261 | ✅ | gamification |
| `gamification:award_daily_login_bonus` | gamification_tasks.py:318 | ✅ | gamification |
| `badges:check_user_achievements` | badge_tasks.py:17 | ✅ | gamification |
| `badges:daily_badge_check` | badge_tasks.py:62 | ✅ | gamification |
| `badges:monthly_top_advertisers` | badge_tasks.py:122 | ✅ | gamification |
| `badges:notify_badge_earned` | badge_tasks.py:213 | ❌ | gamification |
| `badges:trigger_after_campaign_launch` | badge_tasks.py:267 | ❌ | gamification |
| `badges:trigger_after_campaign_complete` | badge_tasks.py:277 | ❌ | gamification |
| `badges:trigger_after_streak_update` | badge_tasks.py:288 | ❌ | gamification |
| `integrity:check_data_integrity` | integrity_tasks.py:59 | ❌ | cleanup (или background) |

---

## Таблица 5: активное Beat расписание

**Источник истины:** `src/tasks/celery_app.py`, функция `get_beat_schedule()` + отдельная запись после вызова.

| beat_entry | task_name | task_exists | queue | schedule |
|------------|-----------|-------------|-------|----------|
| parser-slot-1-business | `parser:refresh_chat_database_business` | ✅ | parser | 00:15 UTC |
| parser-slot-2-marketing | `parser:refresh_chat_database_marketing` | ✅ | parser | 00:45 UTC |
| parser-slot-3-it | `parser:refresh_chat_database_it` | ✅ | parser | 01:15 UTC |
| parser-slot-4-lifestyle | `parser:refresh_chat_database_lifestyle` | ✅ | parser | 01:45 UTC |
| parser-slot-5-health | `parser:refresh_chat_database_health` | ✅ | parser | 02:15 UTC |
| parser-slot-6-education | `parser:refresh_chat_database_education` | ✅ | parser | 02:45 UTC |
| parser-slot-7-news | `parser:refresh_chat_database_news` | ✅ | parser | 03:15 UTC |
| collect-all-chats-stats-daily | `parser:collect_all_chats_stats` | ✅ | parser | 03:30 UTC |
| delete-old-logs | `cleanup:delete_old_logs` | ✅ | cleanup | воскресенье 03:00 UTC |
| check-plan-renewals | `billing:check_plan_renewals` | ✅ | billing | ежедневно 03:00 UTC |
| placement-check-scheduled-deletions | `placement:check_scheduled_deletions` | ✅ | worker_critical | каждые 5 мин |

**Итого активных Beat записей: 11. Все задачи существуют. ✅**

### STOP CONDITION — мёртвое расписание celery_config.py

`celery_config.py` содержит `BEAT_SCHEDULE` с ~22 записями, которые **НЕ загружаются** в приложение (не импортируются в `celery_app.py`). Среди них:

| beat_entry | task_name | Статус |
|------------|-----------|--------|
| check-scheduled-campaigns | `src.tasks.mailing_tasks.check_scheduled_campaigns` | 🔴 МОДУЛЬ УДАЛЁН (v4.3) |
| recalculate-ratings-daily | `src.tasks.rating_tasks.recalculate_ratings_daily` | 🔴 ФАЙЛ НЕ СУЩЕСТВУЕТ |
| update-weekly-toplists | `src.tasks.rating_tasks.update_weekly_toplists` | 🔴 ФАЙЛ НЕ СУЩЕСТВУЕТ |
| tax-calendar-reminder | `tax:calendar_reminder` | 🔴 ЗАДАЧА НЕ ОПРЕДЕЛЕНА В tax_tasks.py |
| placement-check-owner-sla | `placement:check_owner_response_sla` | ⚠️ задача существует, но Beat запись мёртвая |
| placement-check-payment-sla | `placement:check_payment_sla` | ⚠️ аналогично |
| placement-check-counter-sla | `placement:check_counter_offer_sla` | ⚠️ аналогично |
| placement-check-escrow-sla | `placement:check_escrow_sla` | ⚠️ аналогично |
| placement-check-escrow-stuck | `placement:check_escrow_stuck` | ⚠️ аналогично |
| check-published-posts-health | `placement:check_published_posts_health` | ⚠️ аналогично |
| data-integrity-check | `integrity:check_data_integrity` | ⚠️ задача существует, но Beat запись мёртвая |

**⚠️ STOP CONDITION:** `tax:calendar_reminder` — задача упоминается в Beat расписании, но не существует. Файл `tax_tasks.py` (130 строк) содержит только helper-функции без декораторов `@celery_app.task`.

Однако это расписание мёртвое — не загружается в рантайм. Runtime не аффектирован.

---

## Критический анализ: два конфига, один конфликт

```
celery_app.py                           celery_config.py
─────────────────────────────           ─────────────────────────────
get_beat_schedule() → dict              BEAT_SCHEDULE = {...}   ← НЕ ИМПОРТИРУЕТСЯ
  11 записей (active)                     ~22 записей (МЁРТВО)

app.conf.task_routes = {                TASK_ROUTES = {...}     ← НЕ ИМПОРТИРУЕТСЯ
  "mailing.*" → mailing,                  14 маршрутов (МЁРТВО)
  "parser.*" → parser,
  "cleanup.*" → cleanup,
  "publication.*" → critical,  ← DEAD
}
```

`celery_config.py` импортируется ТОЛЬКО для констант имён очередей (`QUEUE_WORKER_CRITICAL` и пр.) из `placement_tasks.py:31`. Все бизнес-значения (BEAT_SCHEDULE, TASK_ROUTES, QUEUE_CONFIG, TASK_TIME_LIMITS) — мёртвый код.

---

## Рекомендация 1: минимальный diff для `celery_app.py`

### 1a. Расширить `task_routes` (заменить 4 маршрута на полный список)

```python
# celery_app.py → create_celery_app() → app.conf.update()
task_routes={
    # Существующие (исправить)
    "mailing.*": {"queue": "mailing"},
    "parser.*": {"queue": "parser"},
    "cleanup.*": {"queue": "cleanup"},
    # Убрать dead route: "publication.*"

    # НОВЫЕ маршруты
    "notifications.*": {"queue": "notifications"},
    "placement.*": {"queue": "worker_critical"},
    "billing.*": {"queue": "billing"},
    "ord.*": {"queue": "background"},
    "badges.*": {"queue": "gamification"},
    "gamification.*": {"queue": "gamification"},
    "integrity.*": {"queue": "cleanup"},
    "dispute.*": {"queue": "worker_critical"},
    "tax.*": {"queue": "billing"},
    "document_ocr.*": {"queue": "worker_critical"},
    "payouts.*": {"queue": "background"},
},
```

### 1b. Добавить 6 SLA записей в `get_beat_schedule()`

```python
# добавить в возвращаемый dict get_beat_schedule():
"placement-check-owner-sla": {
    "task": "placement:check_owner_response_sla",
    "schedule": crontab(minute="*/5"),
    "options": {"queue": "worker_critical", "expires": 60},
},
"placement-check-payment-sla": {
    "task": "placement:check_payment_sla",
    "schedule": crontab(minute="*/5"),
    "options": {"queue": "worker_critical", "expires": 60},
},
"placement-check-counter-sla": {
    "task": "placement:check_counter_offer_sla",
    "schedule": crontab(minute="*/5"),
    "options": {"queue": "worker_critical", "expires": 60},
},
"placement-check-escrow-sla": {
    "task": "placement:check_escrow_sla",
    "schedule": crontab(minute="*/5"),
    "options": {"queue": "worker_critical", "expires": 60},
},
"placement-check-escrow-stuck": {
    "task": "placement:check_escrow_stuck",
    "schedule": crontab(minute="*/30"),
    "options": {"queue": "worker_critical", "expires": 120},
},
"check-published-posts-health": {
    "task": "placement:check_published_posts_health",
    "schedule": crontab(hour="*/6", minute=30),
    "options": {"queue": "worker_critical", "expires": 300},
},
"data-integrity-check": {
    "task": "integrity:check_data_integrity",
    "schedule": crontab(hour="*/6", minute=0),
    "options": {"queue": "cleanup"},
},
```

### 1c. Добавить недостающие модули в `include=[]`

```python
include=[
    # ... existing ...
    "src.tasks.gamification_tasks",
    "src.tasks.badge_tasks",
    "src.tasks.integrity_tasks",
    "src.tasks.tax_tasks",
],
```

*(autodiscover покрывает их, но явный include делает граф зависимостей читаемым)*

---

## Рекомендация 2: декораторы требуют `queue=`

Следующие задачи уходят в default queue и должны получить явный `queue=` в декораторе (как резервный уровень после task_routes):

| file | task_name | добавить |
|------|-----------|----------|
| dispute_tasks.py:19 | `dispute:resolve_financial` | `queue="worker_critical"` |
| gamification_tasks.py:67 | `gamification:update_streaks_daily` | `queue="gamification"` |
| gamification_tasks.py:119 | `gamification:send_weekly_digest` | `queue="gamification"` |
| gamification_tasks.py:261 | `gamification:check_seasonal_events` | `queue="gamification"` |
| gamification_tasks.py:318 | `gamification:award_daily_login_bonus` | `queue="gamification"` |
| badge_tasks.py:16 | `badges:check_user_achievements` | `queue="gamification"` |
| badge_tasks.py:62 | `badges:daily_badge_check` | `queue="gamification"` |
| badge_tasks.py:122 | `badges:monthly_top_advertisers` | `queue="gamification"` |
| badge_tasks.py:213 | `badges:notify_badge_earned` | `queue="gamification"` |
| badge_tasks.py:267 | `badges:trigger_after_campaign_launch` | `queue="gamification"` |
| badge_tasks.py:277 | `badges:trigger_after_campaign_complete` | `queue="gamification"` |
| badge_tasks.py:288 | `badges:trigger_after_streak_update` | `queue="gamification"` |
| integrity_tasks.py:59 | `integrity:check_data_integrity` | `queue="cleanup"` |

---

## Дополнительные находки

### D-1: `celery_config.py` — мёртвый конфигурационный файл

`BEAT_SCHEDULE`, `TASK_ROUTES`, `QUEUE_CONFIG`, `TASK_TIME_LIMITS`, `TASK_RETRY_POLICY` в `celery_config.py` — мёртвый код. Единственное активное использование: `from src.tasks.celery_config import QUEUE_WORKER_CRITICAL` в `placement_tasks.py:31`.

Решение: либо удалить файл и переместить константы в `celery_app.py`, либо явно импортировать и применить в `celery_app.py`.

### D-2: `tax_tasks.py` не содержит ни одной Celery-задачи

Файл из 130 строк — только helper-функции `_get_upcoming_tax_deadlines()` и `_notify_admins()`. Задача `tax:calendar_reminder` упомянута в `celery_config.py:BEAT_SCHEDULE` (мёртво) и в комментарии `celery_app.py:98` ("consolidated from publication_tasks"). Требуется:
- Либо добавить `@celery_app.task(name="tax:calendar_reminder", queue="billing")` в `tax_tasks.py`
- Либо исключить из конфигурации

### D-3: `billing_tasks.py:105` — неправильный вызов `notify_user.delay()`

```python
# billing_tasks.py:105
notify_user.delay(
    telegram_id=user.telegram_id,
    message=message,
    notification_type=NotificationType.PLAN_RENEWED.value,  # ← этого аргумента НЕТ в сигнатуре
    parse_mode="HTML",
)
```

Функция `notify_user` (notification_tasks.py:194) принимает только `telegram_id`, `message`, `parse_mode`. Аргумент `notification_type` будет проигнорирован Python (передаётся как **kwargs в Celery, но функция его не принимает). Не runtime-ошибка, но сигнализирует о несогласованности.

### D-4: `billing_tasks.py:147` — аналогичная проблема

```python
notify_user.delay(
    telegram_id=user.telegram_id,
    message=message,
    notification_type=NotificationType.PLAN_EXPIRED.value,  # ← неиспользуемый kwarg
    parse_mode="HTML",
)
```

---

## Сводка расхождений

| Категория | Расхождение | Задач |
|-----------|------------|-------|
| Default queue (нет маршрута + нет queue=) | gamification:*, badges:*, integrity:*, dispute:* | 13 |
| Не в активном Beat (мёртвый конфиг) | placement SLA (6) + integrity (1) + gamification (3) + badges (2) | 12 |
| Мёртвый маршрут `publication.*` | нет задач с prefix publication: | 0 |
| Несогласованный prefix vs queue | notifications:auto_approve_placements и 3 других → "mailing" | 4 |
| Не в `include=[]` (только autodiscover) | gamification, badges, integrity, tax | 4 модуля |
| Задача в Beat, но не существует | `tax:calendar_reminder` | 1 (мёртвый Beat) |
| Модуль в `celery_config.BEAT_SCHEDULE`, файл удалён | rating_tasks.py, mailing_tasks.py | 2 файла |

---

🔍 Verified against: d195386 | 📅 Updated: 2026-04-17T00:00:00Z
