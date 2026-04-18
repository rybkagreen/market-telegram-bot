# S-37 Notifications Audit — Bot() Instantiations & notifications_enabled Gaps

**Sprint:** S-37 | **Phase:** Research (read-only)
**Date:** 2026-04-17

---

## 1. Таблица Bot() instantiations

### notification_tasks.py

| file:line | function_name | usage context |
|-----------|---------------|---------------|
| `notification_tasks.py:107` | `_notify_low_balance` | `bot.send_message` (text only) |
| `notification_tasks.py:258` | `_notify_user_async` | `bot.send_message` (text only) |
| `notification_tasks.py:328` | `_send_owner_placement_notification` | `bot.send_message` + InlineKeyboard |
| `notification_tasks.py:449` | `_send_payout_message` | `bot.send_message` (text only) |
| `notification_tasks.py:564` | `notify_admin_new_payout_task` (inner `_notify_async`) | delegates to `notify_admin_new_payout()` handler |
| `notification_tasks.py:666` | `notify_campaign_finished` (inner `_notify`) | `bot.send_message` + InlineKeyboard |
| `notification_tasks.py:799` | `notify_low_balance_enhanced` (inner `_notify`) | `bot.send_message` + InlineKeyboard |
| `notification_tasks.py:1177` | `notify_pending_placement_reminders` (inner `_notify_reminders_async`) | passed to `_send_placement_reminder(...)` |
| `notification_tasks.py:1336` | `notify_expiring_plans` (inner `_notify_expiring_async`) | passed to `_notify_expiring_user(...)` |
| `notification_tasks.py:1407` | `notify_expired_plans` (inner `_notify_expired_async`) | passed to `_downgrade_expired_user(...)` |

**Итого в notification_tasks.py: 10 точек.**

### Другие task-модули

| file:line | function_name | usage context |
|-----------|---------------|---------------|
| `placement_tasks.py:79` | `_notify_user` (helper) | `bot.send_message` (text only) |
| `placement_tasks.py:543` | `_publish_placement_async` (ERID block path) | admin alert via `_Bot.send_message` |
| `placement_tasks.py:569` | `_publish_placement_async` (main path) | passed to `PublicationService` |
| `placement_tasks.py:746` | `_check_published_posts_health_async` | used for post health checks |
| `placement_tasks.py:1077` | `_delete_published_post_async` | passed to `PublicationService.delete_published_post` |
| `integrity_tasks.py:126` | `_notify_admin_failures` | `bot.send_message` to all admin_ids |
| `gamification_tasks.py:201` | `_send_digest_to_user` | `bot.send_message` (weekly digest) |

### ⚠️ STOP CONDITION: Bot() за пределами src/tasks/

| file:line | function_name | usage context |
|-----------|---------------|---------------|
| `src/core/services/yookassa_service.py:229` | `_process_payment_webhook` (approx) | `bot.send_message` (payment success) |

**Найден Bot() в `src/core/services/` — нарушение паттерна "только tasks создают Bot".**

---

## 2. Код `_notify_user_async` (полностью, с номерами строк)

```python
240  async def _notify_user_async(
241      telegram_id: int,
242      message: str,
243      parse_mode: str = "HTML",
244  ) -> None:
245      """
246      Асинхронная отправка уведомления.
247  
248      Args:
249          telegram_id: Telegram ID пользователя.
250          message: Текст сообщения.
251          parse_mode: Режим парсинга.
252      """
253      from aiogram import Bot
254      from aiogram.exceptions import TelegramForbiddenError
255  
256      from src.config.settings import settings
257  
258      bot = Bot(token=settings.bot_token)
259  
260      try:
261          await bot.send_message(telegram_id, message, parse_mode=parse_mode)
262      except TelegramForbiddenError:
263          # Пользователь заблокировал бота — это нормальная ситуация
264          logger.warning(f"User {telegram_id} blocked the bot")
265          raise  # Пробрасываем выше для обработки в notify_user
266      except Exception as e:
267          # Другие ошибки (chat not found, network issues)
268          error_str = str(e).lower()
269          if CHAT_NOT_FOUND in error_str or "blocked" in error_str:
270              logger.warning(f"User {telegram_id} blocked the bot or chat is inaccessible: {e}")
271          else:
272              logger.error(f"Error sending notification to {telegram_id}: {e}")
273          raise
274      finally:
275          await bot.session.close()
276  ```

**Ключевые наблюдения:**
- Принимает `telegram_id: int` — **не User-объект, не user_id из БД**. Это уже `telegram_id`.
- Внутри **нет** проверки `notifications_enabled`.
- Создаёт `Bot()` при каждом вызове и закрывает сессию в `finally`.
- Вызывающий код несёт ответственность за проверку настройки уведомлений.

---

## 3. Таблица всех задач: проверка notifications_enabled

| task_name (Celery name) | file:line (Celery декоратор) | вызывает `_notify_user_async` | собственная проверка `notifications_enabled` |
|-------------------------|-------------------------------|-------------------------------|----------------------------------------------|
| `mailing:check_low_balance` | `notification_tasks.py:27` | Нет (вызывает `_notify_low_balance`) | ✅ Да (`notification_tasks.py:78`) |
| `notifications:notify_campaign_status` | `notification_tasks.py:132` | ✅ Да (строка 164) | ✅ Да (`notification_tasks.py:158`) |
| `mailing:notify_user` | `notification_tasks.py:194` | ✅ Да (строка 225) | ❌ Нет |
| `notifications:notify_owner_new_placement` | `notification_tasks.py:353` | Нет (вызывает `_send_owner_placement_notification`) | ✅ Да (`notification_tasks.py:376`) |
| `notifications:notify_owner_xp_for_publication` | `notification_tasks.py:399` | Нет (вызывает `notify_level_up.delay`) | ❌ Нет |
| `notifications:notify_payout_created` | `notification_tasks.py:467` | Нет (вызывает `_send_payout_message`) | ✅ Да (`notification_tasks.py:484`) |
| `notifications:notify_payout_paid` | `notification_tasks.py:504` | Нет (вызывает `_send_payout_message`) | ✅ Да (`notification_tasks.py:521`) |
| `payouts:notify_admin_new_payout` | `notification_tasks.py:539` | Нет (admin-уведомление) | ❌ Нет (admin — не пользователь) |
| `notifications:notify_post_published` | `notification_tasks.py:591` | ✅ Да (строка 611) | ❌ Нет |
| `notifications:notify_campaign_finished` | `notification_tasks.py:621` | Нет (прямой `bot.send_message`) | ❌ Нет |
| `notifications:notify_placement_rejected` | `notification_tasks.py:685` | ✅ Да (строка 719) | ❌ Нет |
| `notifications:notify_changes_requested` | `notification_tasks.py:729` | ✅ Да (строка 751) | ❌ Нет |
| `notifications:notify_low_balance_enhanced` | `notification_tasks.py:761` | Нет (прямой `bot.send_message`) | ❌ Нет |
| `notifications:notify_plan_expiring` | `notification_tasks.py:818` | ✅ Да (строка 843) | ❌ Нет |
| `notifications:notify_badge_earned` | `notification_tasks.py:858` | ✅ Да (строка 881) | ❌ Нет |
| `notifications:notify_level_up` | `notification_tasks.py:891` | ✅ Да (строка 940) | ❌ Нет |
| `notifications:notify_channel_top10` | `notification_tasks.py:950` | ✅ Да (строка 977) | ❌ Нет |
| `notifications:notify_referral_bonus` | `notification_tasks.py:987` | ✅ Да (строка 1007) | ❌ Нет |
| `notifications:auto_approve_placements` | `notification_tasks.py:1022` | Нет | N/A (не уведомление) |
| `notifications:notify_pending_placement_reminders` | `notification_tasks.py:1135` | Нет (вызывает `_send_placement_reminder`) | ✅ Да (внутри `_send_placement_reminder:1111`) |
| `notifications:notify_expiring_plans` | `notification_tasks.py:1293` | Нет (вызывает `_notify_expiring_user`) | ✅ Да (внутри `_notify_expiring_user:1225`) |
| `notifications:notify_expired_plans` | `notification_tasks.py:1367` | Нет (вызывает `_downgrade_expired_user`) | ✅ Да (внутри `_downgrade_expired_user:1280`) |

### Задачи БЕЗ проверки notifications_enabled (уведомляют пользователей, не admin):

| task_name | file:line | вызывает `_notify_user_async` | примечание |
|-----------|-----------|-------------------------------|------------|
| `mailing:notify_user` | `notification_tasks.py:194` | ✅ | Публичный entry-point — пропускает любое сообщение |
| `notifications:notify_owner_xp_for_publication` | `notification_tasks.py:399` | через цепочку | Вызывает `notify_level_up.delay` без проверки |
| `notifications:notify_post_published` | `notification_tasks.py:591` | ✅ | advertiser_id, без проверки |
| `notifications:notify_campaign_finished` | `notification_tasks.py:621` | Нет (прямой Bot) | advertiser_id, без проверки |
| `notifications:notify_placement_rejected` | `notification_tasks.py:685` | ✅ | advertiser_id, без проверки |
| `notifications:notify_changes_requested` | `notification_tasks.py:729` | ✅ | advertiser_id, без проверки |
| `notifications:notify_low_balance_enhanced` | `notification_tasks.py:761` | Нет (прямой Bot) | advertiser_id, без проверки |
| `notifications:notify_plan_expiring` | `notification_tasks.py:818` | ✅ | advertiser_id, без проверки |
| `notifications:notify_badge_earned` | `notification_tasks.py:858` | ✅ | user_id, без проверки |
| `notifications:notify_level_up` | `notification_tasks.py:891` | ✅ | user_id, без проверки |
| `notifications:notify_channel_top10` | `notification_tasks.py:950` | ✅ | owner_id, без проверки |
| `notifications:notify_referral_bonus` | `notification_tasks.py:987` | ✅ | referrer_id, без проверки |

**Итого: 12 задач не проверяют notifications_enabled** — полностью подтверждает аудит Phase 9.

### Дополнительные нарушения в других модулях:

| task/function | file:line | проверка notifications_enabled |
|---------------|-----------|--------------------------------|
| `_notify_user` (placement_tasks helper) | `placement_tasks.py:67` | ❌ Нет |
| `_send_digest_to_user` (gamification) | `gamification_tasks.py:187` | ✅ Да (строка 167 — `if not user.notifications_enabled`) |
| `_notify_admin_failures` (integrity) | `integrity_tasks.py:112` | N/A (admin alert) |
| `yookassa_service` payment success | `yookassa_service.py:229` | ❌ Нет |

---

## 4. Анализ сигнатуры `_notify_user_async`

```python
async def _notify_user_async(telegram_id: int, message: str, parse_mode: str = "HTML") -> None
```

**Принимает `telegram_id: int`** — это уже финальный Telegram Chat ID, не внутренний `user.id` из БД.

Следствия для рефакторинга:
- Проверить `notifications_enabled` внутри `_notify_user_async` **невозможно** без добавления DB-запроса (нужен `telegram_id → User`).
- Альтернативы:
  1. **Вариант A**: добавить опциональный параметр `check_notifications: bool = False` и DB lookup внутри хелпера.
  2. **Вариант B**: заменить сигнатуру: принимать `user_id: int` (внутренний ID), делать lookup внутри — единый вход.
  3. **Вариант C**: добавить гард на стороне вызывающего кода — в каждой задаче перед вызовом (текущий подход, непоследовательный).

Параллельный хелпер `_notify_user` в `placement_tasks.py` принимает `user_id: int` (внутренний ID), делает DB lookup, но тоже не проверяет `notifications_enabled`.

---

## 5. Модель User: поле notifications_enabled

**Файл:** `src/db/models/user.py:92`

```python
notifications_enabled: Mapped[bool] = mapped_column(
    Boolean, default=True, server_default="true"
)
```

- Тип: `bool`
- Default: `True` (python-side)
- Server default: `"true"` (DB-side)
- Без nullable — всегда присутствует

---

## 6. Рекомендованный план рефакторинга (без кода)

### TD-14: Singleton Bot / Bot-pool вместо per-call instantiation

**Проблема:** 17+ мест создают `Bot(token=...)` при каждом вызове. Каждый вызов открывает новую HTTP-сессию (aiohttp ClientSession) и затем закрывает её в `finally`. Это:
- Накладные расходы на TLS handshake при каждом уведомлении
- Риск утечки сессий если `finally` не срабатывает (исключение до `bot = Bot(...)`)
- Сложность поддержки — логика создания/закрытия размазана по 17 местам

**Рекомендация:**
1. Создать модуль `src/tasks/_bot_factory.py` с функцией `get_bot() -> Bot` — возвращает один и тот же экземпляр (lazy singleton).
2. Бот создаётся один раз при первом вызове, сессия живёт всё время жизни воркера.
3. Celery worker lifecycle hook (`worker_process_init` / `worker_process_shutdown`) — закрывать сессию при завершении.
4. Все 17 точек меняются с `bot = Bot(token=...)` + `await bot.session.close()` на просто `bot = get_bot()`.

### TD-13 / N-11: notifications_enabled пропускается в 12 задачах

**Проблема:** 12 Celery-задач отправляют уведомления без проверки `user.notifications_enabled`. Проверка непоследовательна — есть в 6-7 местах, отсутствует в 12.

**Рекомендация:**
1. Переписать `_notify_user_async` принимать `telegram_id: int` + добавить параметр `skip_pref_check: bool = False` и DB lookup. ИЛИ — создать новый хелпер `_notify_user_checked(telegram_id: int, ...) -> bool` с встроенной проверкой.
2. Все 12 задач, вызывающих `_notify_user_async` напрямую, должны либо перейти на новый хелпер, либо добавить проверку перед вызовом.
3. Задачи, где данные уже содержат `user_id` (не `telegram_id`), могут использовать путь: `UserRepo.get_by_id → check notifications_enabled → get telegram_id → send`.
4. Задача `notify_admin_new_payout` и `_notify_admin_failures` — исключения, для них проверка не нужна (получатель — admin, не пользователь).
5. `yookassa_service.py:229` — аномалия: сервисный слой создаёт Bot() напрямую. Следует делегировать в задачу Celery или NotificationService.

### Порядок изменений (приоритет)

1. **Высокий**: singleton Bot в tasks (TD-14) — снижает нагрузку на TLS и упрощает код.
2. **Высокий**: `mailing:notify_user` без проверки — публичный entry-point, вызывается внешним кодом, наиболее опасная точка.
3. **Средний**: 10 gamification/advertiser задач без проверки (notify_badge_earned, notify_level_up, etc.).
4. **Низкий**: `yookassa_service.py` — вынести уведомление в Celery-задачу.

---

🔍 Verified against: `d195386` | 📅 Updated: 2026-04-17T00:00:00Z
