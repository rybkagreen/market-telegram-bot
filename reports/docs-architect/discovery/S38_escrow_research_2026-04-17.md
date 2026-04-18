# S-38 Research: Stuck Escrow Placements — Flow Analysis & Gap Audit

> **Phase:** research / read-only  
> **Audit reference:** D-03 — ESCROW-001 release from `delete_published_post`, status OPEN  
> **Key file:** `src/tasks/placement_tasks.py`  

---

## STOP AND REPORT: escrow_service.py не существует

`src/core/services/escrow_service.py` отсутствует. Вся эскроу-логика распределена по трём сервисам:

| Сервис | Метод | Роль |
|--------|-------|------|
| `BillingService` | `freeze_escrow()` | Заморозка (payment → escrow) |
| `BillingService` | `freeze_escrow_for_placement()` | То же, принимает session извне |
| `BillingService` | `release_escrow()` | Выплата owner + комиссия платформы |
| `BillingService` | `refund_escrow()` | Возврат при отмене (3 сценария) |
| `PublicationService` | `delete_published_post()` | Вызывает release_escrow (ESCROW-001) |
| `PlacementRequestService` | `_freeze_escrow_for_payment()` | Оркестратор: freeze + set_escrow |

---

## Схема state-machine `placement.status`

```
  [pending_owner]
       │ owner approves
       ▼
  [pending_payment] ←──────── [counter_offer]
       │ advertiser pays              ↑↓ negotiation
       ▼
     [escrow]  ←── CENTRAL HUB
       │
       ├─── ERID missing ──────► [ord_blocked]  ← TERMINAL, no recovery
       │
       ├─── publish_placement task ─► [published]
       │         │ Telegram error          │
       │         ▼                         │ scheduled_delete_at reached
       │      [failed]                     ▼
       │         │                  delete_published_post task
       │         ▼                         │
       │   retry_failed_pub ──► [escrow]   │ release_escrow() called
       │   (max 1 retry)                   ▼
       │                            [completed]
       │
       └─── check_escrow_sla ─────► [failed]  (SLA violation)

Terminal statuses: failed, failed_permissions, refunded, cancelled, ord_blocked, completed
```

---

## Таблица переходов

| Transition | Task / Handler | Trigger | Error Handling |
|---|---|---|---|
| `pending_payment → escrow` | `PlacementRequestService.process_payment()` | Advertiser button / API | `InsufficientFundsError` → bubble up to caller |
| `escrow → (task scheduled)` | `_schedule_publication_task()` | Immediately after `process_payment` | `schedule_placement_publication.delay()` — fire-and-forget, no retry |
| `escrow → published` | `placement:publish_placement` (Beat via `schedule_placement_publication`) | Celery ETA | bare `except Exception` → sets `failed`, notifies advertiser; **no billing refund called** |
| `escrow → ord_blocked` | `placement:publish_placement` | ERID check fails | Admin Telegram alert; **no refund, no recovery task** |
| `escrow → failed` | `placement:check_escrow_sla` | `final_schedule <= now AND message_id IS NULL` | bare `except Exception` → `stats["errors"]++`; single `session.commit()` at end |
| `published → completed` | `placement:delete_published_post` ← `placement:check_scheduled_deletions` | `scheduled_delete_at <= now` | bare `except Exception` → return `{"error": ...}`; **no retry, no re-dispatch** |
| `published → completed` | manual / admin | — | — |
| `escrow → cancelled/refunded` | `PlacementRequestService.advertiser_cancel()` | Advertiser button | `_refund_escrow_if_needed()` → `BillingService.refund_escrow()` |
| `escrow (stuck, 48h) → meta_json` | `placement:check_escrow_stuck` | `scheduled_delete_at < now-48h AND status=escrow` | **logs only, no action, no commit** |

---

## Анализ `check_escrow_sla`

### Код (placement_tasks.py:858–977)

```python
# Query
select(PlacementRequest).where(
    PlacementRequest.status == PlacementStatus.escrow,
    PlacementRequest.message_id.is_(None),         # ← never published
    PlacementRequest.final_schedule.isnot(None),
    PlacementRequest.final_schedule <= now,
)

# Action per placement
placement.status = PlacementStatus.failed
advertiser.balance_rub += final_price             # DIRECT balance manipulation
session.add(Transaction(type=TransactionType.refund, amount=final_price))
_notify_user(advertiser_id, "❌ Ошибка публикации...")
_notify_user(channel.owner_id, "⚠️ Не опубликовано...")

await session.commit()  # single commit at end of loop
```

### Анализ покрытия

| Критерий | Оценка |
|---|---|
| Покрывает escrow без message_id (задача потеряна) | ✅ |
| Покрывает escrow с `final_schedule=None` | ❌ (не попадает в query) |
| Покрывает `ord_blocked` | ❌ (другой статус) |
| Обновляет `platform_account.escrow_reserved` | ❌ (использует прямой += вместо BillingService) |
| Идемпотентность | ⚠️ только Redis-дедуп (TTL=3600 из DEDUP_TTL default) |
| Транзакционная безопасность | ⚠️ нет `with_for_update()` — race condition с воркерами |
| Retry при ошибке конкретного placement | ❌ — инкремент stats["errors"], продолжение цикла |
| Состояние сессии после частичного failure | ⚠️ `flush()` был вызван, `rollback()` нет |

**Ключевой дефект:** прямое `advertiser.balance_rub += final_price` вместо `BillingService.refund_escrow()` не уменьшает `platform_account.escrow_reserved`. Со временем баланс платформы становится некорректным.

---

## Анализ `check_escrow_stuck`

### Код (placement_tasks.py:1183–1251)

```python
# Query — ищет ESCROW с прошедшим scheduled_delete_at (> 48h назад)
PlacementRequest.status == PlacementStatus.escrow,
PlacementRequest.scheduled_delete_at.isnot(None),
PlacementRequest.scheduled_delete_at < threshold,  # threshold = now - 48h

# Action — ТОЛЬКО логирование
logger.critical("STUCK ESCROW: ...")
placement.meta_json["escrow_stuck_detected"] = datetime.now(UTC).isoformat()
# НЕТ session.commit() !
```

**Этот сценарий охватывает:** размещение, у которого `message_id` был сохранён (первый commit в `publish_placement`) и `scheduled_delete_at` выставлен, но второй commit (status=published) не выполнился. Пост реально живёт в Telegram, escrow заморожено, owner не получит деньги никогда.

**Критические пропуски:**
1. `session.commit()` **отсутствует** — мутация `meta_json` не сохраняется в БД
2. Не вызывает `delete_published_post.delay(placement.id)` — пост остаётся в эфире
3. Не вызывает `release_escrow` / `refund_escrow` — деньги заморожены
4. Не отправляет уведомление администраторам (только `logger.critical`)

---

## Список сценариев застревания

### Сценарий 1: `publish_placement` задача потеряна в Redis
**Условие:** Celery рестарт / `visibility_timeout` истёк до обработки  
**Состояние:** `status=escrow`, `message_id=None`, `final_schedule` в прошлом  
**Что падает:** задача пропала из очереди, никто не перезапускает  
**Что должно произойти:** рефанд + failed  
**Сейчас:** `check_escrow_sla` ✅ ловит (каждые 5 мин)  
**Проблема:** только если `final_schedule != NULL` — если schedule не выставлен, не ловится

### Сценарий 2: `publish_placement` упала с `TelegramBadRequest`
**Условие:** Telegram API ошибка при отправке  
**Состояние:** `status=failed` (строки 606-614 placement_tasks.py)  
**Что падает:** в уведомлении обещается "Возврат 50%", но `billing_service.refund_escrow()` **НЕ вызывается**  
**Что должно произойти:** `retry_failed_publication` должен быть диспатчен, но это делается не автоматически  
**Сейчас:** деньги остаются замороженными, `retry_failed_publication` никогда не запускается автоматически  
**Тяжесть:** HIGH — escrow не освобождается при publication failure

### Сценарий 3: Разрыв между двумя коммитами в `publish_placement`
**Условие:** первый commit (message_id + scheduled_delete_at) прошёл, второй (status=published) нет  
**Состояние:** `status=escrow`, `message_id` установлен, `scheduled_delete_at` установлен  
**Что падает:** voркер упал / DB timeout между строками 291 и 576 в publication_service.py  
**Что должно произойти:** либо повторить попытку (пост уже есть — `message_id` check в `_publish_placement_async` строка 491 защищает от дублирования), либо перейти сразу к delete  
**Сейчас:** `check_escrow_stuck` детектирует (>48h), но **ничего не делает** и даже не коммитит детекцию  
**Тяжесть:** CRITICAL — пост в Telegram живёт, owner не получит оплату

### Сценарий 4: `delete_published_post` упала (ESCROW-001)
**Условие:** DB ошибка или исключение в `pub_service.delete_published_post()`  
**Состояние:** `status=published`, `scheduled_delete_at` в прошлом, escrow НЕ освобождён  
**Что падает:** строки 1088-1091 — bare except, возвращает `{"error": ...}`, task считается успешной  
**Что должно произойти:** автоматический retry  
**Сейчас:** `check_scheduled_deletions` (каждые 5 мин) должен перезапустить, но Redis dedup (TTL=3600 по умолчанию) блокирует на 1 час  
**Тяжесть:** CRITICAL — owner не получает выплату, пост остаётся в Telegram

### Сценарий 5: `ord_blocked` — деньги заморожены навсегда
**Условие:** ERID не получен (OrdRegistration.status not in success states)  
**Состояние:** `status=ord_blocked` (строки 530-531)  
**Что падает:** нет recovery-задачи, нет таймаута, нет рефанда  
**Что должно произойти:** либо повторная попытка получить ERID, либо рефанд с уведомлением  
**Сейчас:** `check_escrow_sla` смотрит только `status=escrow` — `ord_blocked` игнорируется  
**Тяжесть:** HIGH — деньги advertiser'а заморожены без ограничения времени

### Сценарий 6: `final_schedule IS NULL` при нормальном переходе в escrow
**Условие:** `schedule_placement_publication` вызван с `scheduled_iso=None` → ETA через 5 мин (не пишется в БД)  
**Состояние:** `status=escrow`, `message_id=None`, `final_schedule=NULL`  
**Что падает:** задача потеряна, но `check_escrow_sla` не ловит (WHERE `final_schedule IS NOT NULL`)  
**Сейчас:** placement зависает навсегда  
**Тяжесть:** MEDIUM

---

## Отсутствие retry / DLQ — детали

**Ни одна задача в `placement_tasks.py` не использует:**
- `autoretry_for` 
- `retry_backoff`
- `self.retry()`

Глобальный `task_max_retries=3` в `celery_app.py:74` — это **дефолт**, он не применяется автоматически. Для применения нужен явный вызов `self.retry()` или `autoretry_for=`.

**DLQ:** ноль упоминаний `dead_letter` / `dlq` / `DLQ` в `src/`.

**Ord tasks** (сравнение): используют явный `raise self.retry(exc=e, countdown=300, max_retries=3)` и polling с `max_retries=12`. Это правильный паттерн, не применённый к placement tasks.

---

## Рекомендация: архитектура recovery

### Вариант A: DLQ поверх Celery (отклоняется)
Redis-брокер не поддерживает native DLQ (это фича AMQP/RabbitMQ). Кастомная реализация потребует отдельной очереди + consumer — избыточно для данной задачи.

### Вариант B: Таблица `stuck_placements` (излишне)
Добавила бы Alembic-миграцию, новую схему, новый repo. Дублирует то, что уже есть в `placement.meta_json["escrow_stuck_detected"]` и `TransactionType.refund`. Не оправдано.

### Вариант C: Расширить существующие мониторинговые задачи ✅ (рекомендуется)

**Минимальный набор исправлений (в порядке приоритета):**

1. **`delete_published_post` task — добавить autoretry:**
   ```python
   @celery_app.task(
       bind=True, base=BaseTask,
       name="placement:delete_published_post",
       queue=QUEUE_WORKER_CRITICAL,
       autoretry_for=(Exception,),
       max_retries=5,
       retry_backoff=True,
       retry_backoff_max=600,
   )
   ```
   Убрать bare `except` — дать исключению всплыть для Celery retry.

2. **`check_escrow_stuck` — добавить `session.commit()` и action:**
   - Добавить `await session.commit()` после цикла
   - Для placement с `message_id IS NOT NULL`: вызвать `delete_published_post.delay(placement.id)`
   - Для placement с `message_id IS NULL`: вызвать логику refund (или передать в check_escrow_sla)
   - Добавить Telegram-уведомление администраторам

3. **`check_escrow_sla` — использовать BillingService:**
   - Заменить прямой `advertiser.balance_rub += final_price` на `billing_service.refund_escrow(session, ..., scenario="after_escrow_before_confirmation")`
   - Добавить `with_for_update()` в запрос
   - Расширить query: убрать условие `final_schedule IS NOT NULL` или добавить fallback на `created_at + 2h`

4. **`publish_placement` failure path — вызвать refund:**
   - При publication failure в строке 609 вызвать `billing_service.refund_escrow()` и убрать `REFUND_AFTER_ESCROW_PCT` из уведомления (или выполнить фактический возврат)
   - Автоматически диспатчить `retry_failed_publication.apply_async(args=[placement_id], countdown=3600)`

5. **`ord_blocked` — добавить SLA:**
   - Новая задача (или расширение `check_escrow_sla`): если `ord_blocked` старше N часов → рефанд advertiser'у + уведомление admin

---

## Итоговая матрица риска

| Сценарий | Вероятность | Тяжесть | Recovery сейчас | Приоритет fix |
|---|---|---|---|---|
| publish_placement task lost | Низкая | Высокая | ✅ check_escrow_sla | P2 |
| publish_placement fails, escrow не возвращается | Средняя | КРИТИЧЕСКАЯ | ❌ нет | **P0** |
| Разрыв между коммитами | Низкая | КРИТИЧЕСКАЯ | ❌ check_escrow_stuck пустой | **P0** |
| delete_published_post fails | Средняя | КРИТИЧЕСКАЯ | ⚠️ деdup блокирует на 1ч | **P0** |
| ord_blocked без рефанда | Средняя | Высокая | ❌ нет | P1 |
| final_schedule NULL | Низкая | Средняя | ❌ нет | P2 |

---

🔍 Verified against: `d195386` | 📅 Updated: 2026-04-17T00:00:00Z
