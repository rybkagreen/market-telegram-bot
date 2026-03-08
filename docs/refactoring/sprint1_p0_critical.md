# QWEN CODE — СПРИНТ 1: КРИТИЧЕСКИЕ БЛОКЕРЫ (P0)

## ⚠️ ПРАВИЛА ВЫПОЛНЕНИЯ — ЧИТАЙ ПЕРЕД СТАРТОМ

1. **Не пропускай задачи** — выполняй строго в порядке нумерации
2. **Не придумывай логику** — читай существующий код перед правкой
3. **После каждой задачи** — пиши `✅ ЗАДАЧА N ВЫПОЛНЕНА` и показывай diff
4. **Не трогай** файлы вне указанных в задаче — это чужой спринт
5. **Если что-то непонятно** — останови работу и задай вопрос, не угадывай
6. **Тесты** — после каждой задачи запускай `python -m pytest` если есть тесты на модуль

---

## ЗАДАЧА 1 — Реализовать `process_payout()` в `payout_service.py`

### Файл: `src/core/services/payout_service.py`

### Контекст
Сейчас метод `process_payout()` является заглушкой — меняет статус, но не делает реальный перевод. Выплаты владельцам каналов (80% от цены поста) не работают. Это **блокирует монетизацию** всей платформы.

### Что читать перед правкой
```
1. src/core/services/payout_service.py — весь файл
2. src/core/services/cryptobot_service.py — методы transfer() или send_transfer()
3. src/db/models/payout.py — поля PayoutStatus, PayoutCurrency
4. src/db/models/user.py — поля telegram_id, cryptobot_id или аналог
5. src/api/constants/payments.py — константы валют и минимальных сумм
```

### Что реализовать
```python
async def process_payout(self, payout_id: int) -> dict:
    """
    Реальная выплата через CryptoBot API.
    
    Шаги:
    1. Получить Payout из БД по payout_id
    2. Проверить статус: только PENDING → обрабатывать
    3. Проверить минимальную сумму (из constants/payments.py)
    4. Получить telegram_id владельца из User
    5. Вызвать cryptobot_service.send_transfer(
           telegram_id=owner.telegram_id,
           amount=payout.amount,
           currency=payout.currency,
           comment=f"Выплата за размещения в @{channel.username}"
       )
    6. При успехе: статус → COMPLETED, записать transfer_id
    7. При ошибке: статус → FAILED, записать error_message
    8. Вернуть {"success": bool, "transfer_id": str | None, "error": str | None}
    """
```

### Критерии готовности
- [ ] Метод делает реальный API-вызов к CryptoBot
- [ ] Обрабатывает ошибку `InsufficientFunds` от CryptoBot
- [ ] Обрабатывает ошибку `UserNotFound` (нет аккаунта в CryptoBot)
- [ ] Статус Payout корректно меняется в БД
- [ ] Логирует результат через `logger`
- [ ] Нет `try/except Exception: pass` — ошибки должны логироваться

---

## ЗАДАЧА 2 — Исправить `placement_id=0` в `mailing_tasks.py`

### Файл: `src/tasks/mailing_tasks.py`

### Контекст
После успешной рассылки системе нужно начислять XP владельцу канала. Для этого нужен `placement_id` (id записи `MailingLog`). Сейчас передаётся `0`, из-за чего XP не начисляется.

### Что читать перед правкой
```
1. src/tasks/mailing_tasks.py — найти строку с placement_id=0 (около строки 109)
2. src/core/services/mailing_service.py — метод run_campaign(), понять что он возвращает
3. src/db/models/mailing_log.py — поля MailingLog (id, campaign_id, chat_id)
4. src/core/services/xp_service.py — метод add_owner_xp()
```

### Что реализовать
```python
# БЫЛО (примерно):
await xp_service.add_owner_xp(
    user_id=chat.owner_user_id,
    amount=XP_REWARDS["placement_completed"],
    reason="campaign_placement",
    placement_id=0  # ← ЗАГЛУШКА
)

# ДОЛЖНО СТАТЬ:
# После вызова mailing_service.run_campaign(campaign_id):
# 1. Из результата получить список успешных placements (MailingLog.id)
# 2. Для каждого placement передавать реальный placement_id

result = await mailing_service.run_campaign(campaign_id)
for placement in result.successful_placements:
    await xp_service.add_owner_xp(
        user_id=placement.owner_user_id,
        amount=XP_REWARDS["placement_completed"],
        reason="campaign_placement",
        placement_id=placement.id  # ← РЕАЛЬНЫЙ ID
    )
```

### Критерии готовности
- [ ] `placement_id` получается из реального `MailingLog.id`
- [ ] XP начисляется только при успешном статусе размещения
- [ ] Если `owner_user_id` равен `None` — пропускать без ошибки
- [ ] Логировать: сколько владельцев получили XP за кампанию

---

## ЗАДАЧА 3 — Реализовать подсчёт доступной суммы к выводу

### Файлы:
- `src/db/repositories/` — создать или дополнить репозиторий
- `src/bot/handlers/cabinet.py` — строка ~200
- `src/bot/handlers/start.py` — строка ~445

### Контекст
В кабинете и главном меню отображается `available_payout=0` вместо реальной суммы. Нужно считать сумму из таблицы `payouts` по условиям.

### Что читать перед правкой
```
1. src/db/models/payout.py — поля Payout: amount, status, currency, owner_id
2. src/db/repositories/base.py — базовый репозиторий
3. src/bot/handlers/cabinet.py — найти TODO и понять контекст вывода
4. src/bot/handlers/start.py — найти available_payout=0
```

### Что реализовать

**Шаг 3.1** — Добавить метод в репозиторий (создать `src/db/repositories/payout_repo.py` если не существует):
```python
async def get_available_amount(self, owner_id: int) -> Decimal:
    """
    Сумма всех выплат в статусе PENDING для owner_id.
    Возвращает Decimal, 0 если нет.
    """

async def get_total_earned(self, owner_id: int) -> Decimal:
    """
    Сумма всех выплат в статусе COMPLETED для owner_id.
    """
```

**Шаг 3.2** — В `cabinet.py` заменить `available_payout=0`:
```python
# БЫЛО:
available_payout = 0  # TODO: получить из payout_repo

# ДОЛЖНО СТАТЬ:
available_payout = await payout_repo.get_available_amount(user.id)
```

**Шаг 3.3** — Аналогично в `start.py`.

### Критерии готовности
- [ ] Метод `get_available_amount` использует SQL SUM с фильтром по статусу
- [ ] Возвращает `Decimal`, не `float`
- [ ] В кабинете отображается реальная сумма
- [ ] В главном меню отображается реальная сумма

---

## ЗАДАЧА 4 — Включить Level 3 (LLM) content filter

### Файл: `src/utils/content_filter/filter.py`

### Контекст
L3 фильтр (LLM-проверка) закомментирован. Сейчас при score > 0.5 контент не проходит L3 — это позволяет плохому контенту проскакивать. Нужно включить L3, но **с таймаутом** чтобы не блокировать производительность.

### Что читать перед правкой
```
1. src/utils/content_filter/filter.py — весь файл, найти закомментированный L3
2. src/core/services/qwen_ai_service.py — метод для проверки контента
3. src/api/constants/content_filter.py — пороги LEVEL2_THRESHOLD, LEVEL3_THRESHOLD
4. src/config/settings.py — есть ли CONTENT_FILTER_L3_ENABLED или подобное
```

### Что реализовать
```python
# Раскомментировать и доработать:
async def _llm_check(self, text: str) -> FilterResult:
    """
    LLM-проверка через QwenAIService.
    Таймаут: 3 секунды. При таймауте — пропустить (fail open).
    """
    try:
        result = await asyncio.wait_for(
            self.qwen_service.check_content(text),
            timeout=3.0
        )
        return result
    except asyncio.TimeoutError:
        logger.warning("Content filter L3 timeout, failing open")
        return FilterResult(score=0.0, passed=True, level=3)
    except Exception as e:
        logger.error(f"Content filter L3 error: {e}")
        return FilterResult(score=0.0, passed=True, level=3)
```

**Добавить в `settings.py`:**
```python
CONTENT_FILTER_L3_ENABLED: bool = True  # Управление из .env
CONTENT_FILTER_L3_TIMEOUT: float = 3.0
```

### Критерии готовности
- [ ] L3 вызывается когда score L2 > `LEVEL2_THRESHOLD`
- [ ] Таймаут 3 сек — при истечении пропускает (не блокирует)
- [ ] Управляется переменной `CONTENT_FILTER_L3_ENABLED` из `.env`
- [ ] Логирует: level, score, решение для каждой проверки
- [ ] Нет синхронных вызовов в async контексте

---

## ЗАДАЧА 5 — Реализовать PDF-отчёты для кампаний

### Файлы:
- `src/core/services/analytics_service.py` — метод `generate_campaign_pdf_report()`
- `src/utils/pdf_report.py` — утилита генерации
- `src/bot/handlers/notifications.py` — строка ~155

### Контекст
Метод `generate_campaign_pdf_report()` задокументирован в сервисе, но не реализован. В `notifications.py` стоит TODO. Нужна базовая генерация PDF с ключевыми метриками кампании.

### Что читать перед правкой
```
1. src/core/services/analytics_service.py — найти generate_campaign_pdf_report()
2. src/utils/pdf_report.py — есть ли уже заготовка
3. src/db/models/campaign.py — доступные поля кампании
4. src/db/models/mailing_log.py — поля для статистики
5. src/bot/handlers/notifications.py — где вызывается и что ожидается
```

### Что реализовать

**PDF должен содержать:**
```
[Логотип/заголовок]
Отчёт по кампании: {campaign.name или campaign.id}
Дата: {created_at} — {completed_at}

--- РЕЗУЛЬТАТЫ ---
Охват:        {total_sent} каналов
Просмотры:    {total_views}
Клики:        {total_clicks}
CTR:          {ctr}%
Затрачено:    {total_cost} кредитов

--- ТОП-3 КАНАЛА ---
1. @{username} — {views} просмотров
2. ...
3. ...

--- AI-ИНСАЙТ ---
{ai_summary если есть, иначе пусто}
```

**Библиотека:** использовать `reportlab` или `fpdf2` (проверить что установлено в requirements.txt, не добавлять новые зависимости без необходимости)

**Сигнатура:**
```python
async def generate_campaign_pdf_report(self, campaign_id: int) -> bytes:
    """
    Возвращает PDF как bytes.
    Поднимает ValueError если кампания не найдена.
    """
```

**В `notifications.py`:**
```python
# БЫЛО: # TODO: реализовать analytics_service.generate_campaign_report
# ДОЛЖНО СТАТЬ:
pdf_bytes = await analytics_service.generate_campaign_pdf_report(campaign_id)
await bot.send_document(
    chat_id=user.telegram_id,
    document=BufferedInputFile(pdf_bytes, filename=f"report_{campaign_id}.pdf"),
    caption="📊 Ваш отчёт по кампании готов"
)
```

### Критерии готовности
- [ ] PDF генерируется без исключений для завершённой кампании
- [ ] Все числовые поля имеют fallback (`0` если нет данных)
- [ ] Возвращает `bytes`
- [ ] Файл весит < 500KB для типичной кампании
- [ ] В `notifications.py` убран TODO, добавлен реальный вызов

---

## ФИНАЛЬНАЯ ПРОВЕРКА СПРИНТА 1

После выполнения всех задач:

```bash
# 1. Проверить импорты
python -c "from src.core.services.payout_service import PayoutService; print('OK')"
python -c "from src.utils.content_filter.filter import ContentFilter; print('OK')"
python -c "from src.core.services.analytics_service import AnalyticsService; print('OK')"

# 2. Запустить линтер
ruff check src/core/services/payout_service.py
ruff check src/tasks/mailing_tasks.py
ruff check src/utils/content_filter/filter.py

# 3. Проверить что нет новых TODO в изменённых файлах
grep -n "TODO\|FIXME\|placeholder\|заглушка" \
  src/core/services/payout_service.py \
  src/tasks/mailing_tasks.py \
  src/utils/content_filter/filter.py
```

**Спринт считается завершённым** когда все 5 задач выполнены и нет новых TODO в изменённых файлах.
