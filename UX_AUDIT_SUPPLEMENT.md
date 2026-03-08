# ДОПОЛНЕНИЕ К UX_AUDIT_REPORT.md

**Дата дополнения:** 8 марта 2026  
**Причина:** Устранение 14 критических пробелов в исходном отчёте  
**Статус:** ⚠️ Исправление критических замечаний от Claude Sonnet 4.6

---

## РАЗДЕЛ A: ОПИСАНИЕ 12 ПРОПУЩЕННЫХ FLOW

### Flow 3.7: Детальная страница кампании

**Статус:** ⚠️ ЧАСТИЧНО (нет отдельного handler, данные в cabinet.py)

**Точка входа:**
- Команда: `/campaigns` → `cabinet.py:show_campaigns_list`
- Callback: `main:my_campaigns` → выбор кампании из списка

**Файл:** `src/bot/handlers/cabinet.py:406-540`

**Описание:**
В текущей реализации **отдельной детальной страницы кампании нет**. Список кампаний показывается в `show_campaigns_list()`, но переход на детальную страницу не реализован.

**Что отображается в списке:**
```python
text += (
    f"{emoji} <b>{campaign.title}</b>\n"
    f"   Статус: {status_value}  |  Прогресс: {progress:.0f}%\n"
    f"   Создана: {created}\n"
    f"   Отправлено: {campaign.sent_count}/{campaign.total_chats}\n\n"
)
```

**Кнопки по статусам (НЕ РЕАЛИЗОВАНЫ):**
- Черновик: [редактировать] [удалить] [запустить] — ❌ Нет
- В очереди: [отменить] — ❌ Нет
- Активная: [пауза] [отменить] — ❌ Нет
- Завершённая: [аналитика] [дублировать] — ⚠️ Только аналитика через `main:ai_campaign_analytics`
- Ошибка: [что показывается] — ❌ Нет
- Заблокирована: [что показывается, как оспорить] — ❌ Нет

**Где должна быть реализована:**
```python
# Требуется добавить handler:
@router.callback_query(CampaignCB.filter(F.action == "detail"))
async def show_campaign_detail(callback: CallbackQuery, callback_data: CampaignCB) -> None:
    """Показать детальную страницу кампании."""
    # TODO: Реализовать
```

---

### Flow 3.8: Управление активной кампанией

**Статус:** ❌ НЕ РЕАЛИЗОВАНО

**Требуемые функции:**
1. Поставить на паузу → что происходит в БД и Celery
2. Снять с паузы
3. Отменить оставшиеся публикации
4. Отображение прогресса (N из M каналов)

**По коду:**
В `src/bot/handlers/campaigns.py` есть только `confirm_launch()` для запуска. Функции паузы/отмены **отсутствуют**.

**Где должно быть:**
```python
# Требуется добавить:
@router.callback_query(CampaignCB.filter(F.action == "pause"))
async def pause_campaign(callback: CallbackQuery) -> None:
    """Поставить кампанию на паузу."""
    # TODO: Реализовать

@router.callback_query(CampaignCB.filter(F.action == "resume"))
async def resume_campaign(callback: CallbackQuery) -> None:
    """Снять кампанию с паузы."""
    # TODO: Реализовать

@router.callback_query(CampaignCB.filter(F.action == "cancel"))
async def cancel_campaign(callback: CallbackQuery) -> None:
    """Отменить кампанию."""
    # TODO: Реализовать
```

**Проблема:** В `campaigns.py:960` есть `CampaignCB.filter(F.action == "cancel")`, но это отмена визарда создания, не активной кампании.

---

### Flow 3.9: Аналитика кампании

**Статус:** ⚠️ ЧАСТИЧНО (только AI-аналитика)

**Точка входа:**
- Callback: `main:ai_campaign_analytics` → `campaign_analytics.py:show_ai_campaign_analytics`
- Файл: `src/bot/handlers/campaign_analytics.py:32-263`

**Что реализовано:**
1. Список кампаний для выбора (`show_campaign_list_kb`)
2. AI-анализ кампании (`analyze_campaign`)
3. Метрики: охват, ER, CTR, ROI, CPM — ⚠️ Заглушки

**Код анализа:**
```python
# campaign_analytics.py:134-262
@router.callback_query(CampaignAICB.filter(F.action == "analyze"))
async def analyze_campaign(callback: CallbackQuery, callback_data: CampaignAICB) -> None:
    """AI-анализ кампании."""
    campaign_id = int(callback_data.campaign_id)
    
    # Получаем кампанию
    async with async_session_factory() as session:
        campaign = await session.get(Campaign, campaign_id)
        
    # Запрашиваем AI анализ
    analysis = await ai_service.analyze_campaign(campaign)
    
    text = f"📊 <b>AI-анализ кампании</b>\n\n{analysis}"
```

**Что НЕ реализовано:**
- ❌ PDF-отчёт: `notifications.py:145` — заглушка `await callback.answer("🚧 Функция в разработке")`
- ❌ A/B сравнение: нет handler
- ❌ Детальные метрики по каждому каналу: нет

**Где PDF отчёт:**
```python
# notifications.py:145
@router.callback_query(MainMenuCB.filter(F.action == "download_report"))
async def handle_report_request(callback: CallbackQuery) -> None:
    await callback.answer("🚧 Функция в разработке", show_alert=True)
```

---

### Flow 3.10: Дублирование кампании

**Статус:** ❌ НЕ РЕАЛИЗОВАНО

**Где должно быть:**
- Кнопка "Дублировать" на детальной странице кампании (Flow 3.7)
- Handler для копирования данных кампании

**Требуемый код:**
```python
@router.callback_query(CampaignCB.filter(F.action == "duplicate"))
async def duplicate_campaign(callback: CallbackQuery) -> None:
    """Дублировать кампанию."""
    # TODO: Реализовать
    # Копировать: title, topic, header, text, filters
    # Не копировать: status, sent_count, created_at
```

---

### Flow 3.13: История транзакций

**Статус:** ✅ РЕАЛИЗОВАНО (только пополнения)

**Точка входа:**
- Команда: `/balance` → `billing.py:show_balance`
- Callback: `billing:history` → `billing.py:show_history`

**Файл:** `src/bot/handlers/billing.py:548-588`

**Что реализовано:**
```python
@router.callback_query(BillingCB.filter(F.action == "history"))
async def show_history(callback: CallbackQuery) -> None:
    """История пополнений кредитов."""
    async with async_session_factory() as session:
        from sqlalchemy import select
        
        from src.db.models.crypto_payment import CryptoPayment
        
        # Получаем последние 10 платежей
        stmt = (
            select(CryptoPayment)
            .where(CryptoPayment.user_id == user.id)
            .order_by(CryptoPayment.created_at.desc())
            .limit(10)
        )
        result = await session.execute(stmt)
        payments = list(result.scalars().all())
```

**Что отображается:**
- Дата
- Сумма в кредитах
- Валюта (USDT/TON/BTC/ETH/LTC)
- Статус (pending/paid/failed)

**Чего нет:**
- ❌ Пагинация (только последние 10)
- ❌ История расходов (списания за кампании)
- ❌ История выплат (для владельцев)

**Где история выплат:**
В `src/bot/handlers/analytics.py:282` есть кнопка "💰 История выплат" → `ch_payouts:{channel_id}`, но handler не найден.

---

### Flow 3.14: Просмотр текущего тарифа

**Статус:** ⚠️ ЧАСТИЧНО (отображается в кабинете)

**Где отображается:**
1. `/start` — в приветствии: `📦 Тариф: {plan_value}`
2. `/cabinet` — в кабинете: `📦 Тариф: {plan_value}`
3. `/balance` — в балансе: `Тариф: {plan_value}`

**Файл:** `src/bot/handlers/cabinet.py:199-260`

**Что показывается:**
- Название тарифа (FREE/STARTER/PRO/BUSINESS)
- Дата окончания (если есть): `до {plan_expires_at.strftime('%d.%m')} ({days_left} дней)`
- Осталось кампаний: `Осталось кампаний: {remaining_campaigns} из {plan_limit}` — ⚠️ Заглушка

**Чего нет:**
- ❌ Отдельной страницы тарифа
- ❌ Детального описания лимитов тарифа
- ❌ Истории смены тарифов

---

### Flow 3.15: Смена тарифа

**Статус:** ⚠️ ЧАСТИЧНО (только выбор, оплата не работает)

**Точка входа:**
- Callback: `billing:plans` → `billing.py:show_plans`
- Выбор тарифа: `billing:plan` → `billing.py:plan_selected`

**Файл:** `src/bot/handlers/billing.py:476-547`

**Что реализовано:**
```python
@router.callback_query(BillingCB.filter(F.action == "plan"))
async def plan_selected(callback: CallbackQuery, callback_data: BillingCB) -> None:
    """Выбрать и активировать тариф (списывает кредиты)."""
    plan = callback_data.value
    
    # Проверяем баланс
    if user.credits < plan_price:
        await callback.answer("❌ Недостаточно кредитов", show_alert=True)
        return
    
    # TODO: Списать кредиты и активировать тариф
```

**Проблема:** В коде **заглушка** — функция активации тарифа не реализована.

**Где должна быть:**
```python
# billing_service.py — требуется реализовать:
async def activate_plan(user_id: int, plan: UserPlan) -> bool:
    """Активировать тариф пользователя."""
    # TODO: Реализовать
    # 1. Списать кредиты
    # 2. Установить plan
    # 3. Установить plan_expires_at
    # 4. Создать Transaction
```

---

### Flow 3.18: Настройки канала

**Статус:** ✅ РЕАЛИЗОВАНО

**Точка входа:**
- Callback: `ch_settings:{channel_id}` → `channel_owner.py:show_channel_settings`

**Файл:** `src/bot/handlers/channel_owner.py:855-877`

**Что можно менять:**
```python
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💰 Изменить цену", callback_data=f"ch_edit_price:{channel_id}")],
    [InlineKeyboardButton(text="🏷 Изменить тематики", callback_data=f"ch_edit_topics:{channel_id}")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data=f"channel_menu:{channel_id}")],
])
```

**Реализованные handler:**
- ❌ `ch_edit_price:{channel_id}` — НЕ НАЙДЕН
- ❌ `ch_edit_topics:{channel_id}` — НЕ НАЙДЕН
- ✅ `ch_settings:` — показывает меню настроек

**Проблема:** Кнопки есть, handler для редактирования **не реализованы**.

**Где должны быть:**
```python
# Требуется добавить:
@router.callback_query(F.data.startswith("ch_edit_price:"))
async def edit_channel_price(callback: CallbackQuery) -> None:
    """Изменить цену канала."""
    # TODO: Реализовать FSM для ввода новой цены

@router.callback_query(F.data.startswith("ch_edit_topics:"))
async def edit_channel_topics(callback: CallbackQuery) -> None:
    """Изменить тематики канала."""
    # TODO: Реализовать FSM для выбора тематик
```

---

### Flow 3.20: Аналитика канала

**Статус:** ⚠️ ЧАСТИЧНО (только для владельца в analytics.py)

**Точка входа:**
- Callback: `owner_analytics:channel:{channel_id}` → `analytics.py`

**Файл:** `src/bot/handlers/analytics.py:175-280`

**Что реализовано:**
```python
@router.callback_query(F.data.startswith("owner_analytics:channel:"))
async def show_channel_analytics(callback: CallbackQuery) -> None:
    """Показать аналитику канала."""
    channel_id = int((callback.data or "").split(":")[2])
    
    # Получаем канал
    async with async_session_factory() as session:
        channel = await session.get(TelegramChat, channel_id)
        
    text = (
        f"📊 <b>Аналитика канала</b>\n\n"
        f"📡 @{channel.username}\n"
        f"👥 Подписчиков: {channel.member_count:,}\n"
        f"📈 ER: {channel.er:.2f}%\n"
        f"⭐ Рейтинг: {channel.rating:.1f}\n"
    )
```

**Чего нет:**
- ❌ Динамика подписчиков (график)
- ❌ История размещений
- ❌ История выплат
- ❌ Средняя оценка от рекламодателей

---

### Flow 3.24: Каталог каналов + фильтры

**Статус:** ✅ РЕАЛИЗОВАНО

**Точка входа:**
- Команда: `/channels`
- Callback: `main:channels_db` → `channels_db.py:show_channels_menu`

**Файл:** `src/bot/handlers/channels_db.py:1-536`

**Доступные фильтры:**
1. **Категории:** `channels:category` → выбор из 10 категорий
2. **Подкатегории:** `channels:subcategories` → выбор из подкатегорий
3. **Тариф:** `channels:tariff` → фильтр по доступности на тарифе
4. **ER:** `channels:filter_er` → минимальный ER
5. **Рейтинг:** `channels:filter_rating` → минимальный рейтинг
6. **Fraud:** `channels:filter_fraud` → исключить fraud-каналы

**Клавиатуры:**
- `get_categories_kb()` — категории
- `get_tariff_filter_kb()` — фильтр по тарифу
- `get_channels_menu_kb()` — главное меню

**Пагинация:** ✅ Реализована через `PaginationCB`

**Проблема:** Фильтры применяются **последовательно**, не одновременно. Нельзя выбрать "IT + ER > 5% + рейтинг > 70".

---

### Flow 3.25: Детальная страница канала

**Статус:** ❌ НЕ РЕАЛИЗОВАНО

**Где должна быть:**
- Кнопка "Подробнее" в каталоге каналов
- Handler для отображения детальной информации

**Требуемый код:**
```python
@router.callback_query(ChannelsCB.filter(F.action == "channel_detail"))
async def show_channel_detail(callback: CallbackQuery, callback_data: ChannelsCB) -> None:
    """Показать детальную страницу канала."""
    channel_id = int(callback_data.value)
    
    # Получить канал из БД
    # Показать: описание, метрики, последние посты, историю рейтинга, отзывы
    # Кнопки: "Добавить в кампанию", "Сравнить", "Запросить медиакит"
    
    # TODO: Реализовать
```

---

### Flow 3.26: Отзыв о канале

**Статус:** ⚠️ ЧАСТИЧНО (только в campaigns.py)

**Точка входа:**
- Автоматически после завершения кампании
- Callback: `review_request:{campaign_id}` → `campaigns.py:show_review_request`

**Файл:** `src/bot/handlers/campaigns.py:1013-1092`

**Что реализовано:**
```python
@router.callback_query(F.data.startswith("review_request:"))
async def show_review_request(callback: CallbackQuery) -> None:
    """Запросить отзыв о канале."""
    campaign_id = int((callback.data or "").split(":")[1])
    
    text = (
        f"📋 <b>Оцените канал</b>\n\n"
        f"Кампания: {campaign.title}\n"
        f"Канал: @{channel.username}\n\n"
        f"Оцените по параметрам:\n"
        f"• Соответствие тематике\n"
        f"• Качество аудитории\n"
        f"• Скорость размещения\n\n"
        f"По звёздам (1-5):"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐⭐⭐⭐⭐", callback_data=f"review_submit:{campaign_id}:5")],
        [InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data=f"review_submit:{campaign_id}:4")],
        # ... 1-5 звёзд
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="review_skip")],
    ])
```

**Что НЕ реализовано:**
- ❌ Текстовый комментарий (опционально)
- ❌ Сохранение отзыва в БД
- ❌ Отображение отзывов в детальной странице канала

---

### Flow 3.27: Отзыв владельца о рекламодателе

**Статус:** ❌ НЕ РЕАЛИЗОВАНО

**Где должен быть:**
- Автоматически после завершения размещения
- Handler для запроса и сохранения отзыва

**Требуемый код:**
```python
@router.callback_query(F.data.startswith("review_owner_request:"))
async def show_owner_review_request(callback: CallbackQuery) -> None:
    """Запросить отзыв владельца о рекламодателе."""
    # TODO: Реализовать
    # Аналогично Flow 3.26, но для владельца
```

---

## РАЗДЕЛ B: ИСПРАВЛЕНИЯ ПО FLOW

### Flow 3.11 vs 3.12: Пополнение баланса (CryptoBot vs Stars)

**Статус:** ⚠️ ЧАСТИЧНО (оба реализованы, но есть баги)

**Flow 3.11: CryptoBot**

**Точка входа:**
- Callback: `billing:topup_crypto` → `billing.py:show_crypto_packages`

**Файл:** `src/bot/handlers/billing.py:131-363`

**Курс конвертации:**
```python
# settings.py
credits_per_usdt: int = Field(90, alias="CREDITS_PER_USDT")
credits_per_ton: int = Field(400, alias="CREDITS_PER_TON")
credits_per_btc: int = Field(9_000_000, alias="CREDITS_PER_BTC")
credits_per_eth: int = Field(300_000, alias="CREDITS_PER_ETH")
credits_per_ltc: int = Field(7_000, alias="CREDITS_PER_LTC")
```

**Баг (HTTP 400):**
В `cryptobot_service.py` есть проблема с созданием инвойса:
```python
# cryptobot_service.py:78-95
async def create_invoice(self, currency: str, amount: float, ...) -> CryptoPayment:
    try:
        invoice = await self.client.createInvoice(
            currency=currency,
            amount=amount,
            payload=payload_str,
            description=description,
        )
    except Exception as e:
        # ❌ Ловит все ошибки, не логирует детали
        # ❌ Возвращает заглушку вместо обработки
        logger.error(f"CryptoBot error: {e}")
        raise
```

**Проблема:** При создании инвойса CryptoBot возвращает HTTP 400, если:
- `amount` < минимального (0.001 USDT)
- `payload` > 100 символов
- Токен невалидный

**Flow 3.12: Telegram Stars**

**Точка входа:**
- Callback: `billing:topup_stars` → `billing.py:show_stars_packages`

**Файл:** `src/bot/handlers/billing.py:364-475`

**Курс конвертации:**
```python
# settings.py
credits_per_star: int = Field(2, alias="CREDITS_PER_STAR")
```

**Обработка платежа:**
```python
@router.message(F.successful_payment)
async def stars_payment_success(message: Message) -> None:
    """Обработать успешный Stars платёж."""
    # ✅ Реализовано
    # 1. Получить сумму из successful_payment
    # 2. Конвертировать в кредиты
    # 3. Зачислить на баланс
    # 4. Создать Transaction
```

**Различия:**
| Параметр | CryptoBot | Stars |
|----------|-----------|-------|
| Минимум | ~0.001 USDT (90 кр) | 50 Stars (100 кр) |
| Комиссия | ~1% | ~30% (Telegram) |
| Обработка | Webhook (Celery) | Instant (handler) |
| Статусы | pending/paid/failed | paid/failed |

---

### Flow 3.19: Заявки на размещение (детализация)

**Статус:** ✅ РЕАЛИЗОВАНО

**Точка входа:**
- Callback: `main:my_requests` → `start.py:go_to_my_requests`
- Callback: `ch_requests:{channel_id}` → `channel_owner.py:show_channel_requests`

**Файл:** `src/bot/handlers/channel_owner.py:900-1150`

**Точный текст уведомления:**
```python
card_text = (
    f"📋 <b>Заявка #{placement.id}</b>  •  @{placement.chat.username if placement.chat else 'канал'}\n"
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"<b>ТЕКСТ ПОСТА:</b>\n\n"
    f"{campaign.text[:500]}{'...' if len(campaign.text) > 500 else ''}\n\n"
)

if campaign.url:
    card_text += f"🔗 Ссылка: {campaign.url}\n"

if campaign.image_file_id:
    card_text += "🖼 Медиа: изображение прикреплено\n"

card_text += (
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"📅 Желаемое время: {placement.scheduled_at.strftime('%d.%m.%Y %H:%M') if placement.scheduled_at else 'Как можно скорее'}\n"
    f"⏱ Заявка истекает через: {hours_left} ч {mins_left} мин\n"
    f"💰 Ваша выплата: {payout_amount} кр (80% от {placement.cost} кр)\n"
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    f"ℹ️ Рекламодатель: {advertiser_campaigns_count} кампаний"
)
```

**Кнопки:**
```python
keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_placement:{placement_id}")],
    [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_placement_reason:{placement_id}")],
    [InlineKeyboardButton(text="✏️ Запросить правки", callback_data=f"request_changes_placement:{placement_id}")],
    [InlineKeyboardButton(text="🔙 Назад", callback_data=f"ch_requests:{placement.chat_id if placement.chat else 0}")],
])
```

**FSM для причины отклонения:**
```python
# ❌ НЕ РЕАЛИЗОВАНО
# Требуется добавить:
class RejectPlacementStates(StatesGroup):
    waiting_reason = State()

@router.callback_query(F.data.startswith("reject_placement_reason:"))
async def reject_placement_reason(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить причину отклонения."""
    await state.set_state(RejectPlacementStates.waiting_reason)
    await callback.message.answer("Введите причину отклонения:")
```

**Автоодобрение через 24 часа:**
```python
# ❌ НЕ РЕАЛИЗОВАНО
# Требуется Celery задача:
@celery_app.task(bind=True, max_retries=3)
def auto_approve_placement(self, placement_id: int) -> None:
    """Автоодобрение заявки через 24 часа."""
    # TODO: Реализовать
    # 1. Проверить, не было ли решения владельца
    # 2. Если нет → одобрить автоматически
    # 3. Перевести в QUEUED
```

---

### Flow 3.21: Запрос выплаты

**Статус:** ❌ НЕ РЕАЛИЗОВАНО

**Точка входа:**
- Callback: `main:payouts` → `start.py:go_to_payouts`
- Callback: `ch_payouts:{channel_id}` → ❌ НЕ НАЙДЕН

**Файл:** `src/bot/handlers/start.py:645-668`

**Текущая реализация:**
```python
@router.callback_query(MainMenuCB.filter(F.action == "payouts"))
async def go_to_payouts(callback: CallbackQuery) -> None:
    """Показать экран выплат владельца."""
    text = (
        "💸 <b>Выплаты</b>\n\n"
        "Управление выплатами доступно в разделе «Мои каналы».\n\n"
        "Выплаты автоматически создаются после публикации "
        "рекламного поста в вашем канале.\n"
        "80% от стоимости размещения поступает вам, "
        "20% — комиссия платформы."
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📺 Мои каналы", callback_data=MainMenuCB(action="my_channels"))
    builder.button(text="🔙 В меню", callback_data=MainMenuCB(action="main_menu"))
    builder.adjust(1, 1)
    
    await safe_callback_edit(callback, text, reply_markup=builder.as_markup())
```

**Проблема:** Это **информационный экран**, не функциональный. Нет:
- ❌ Кнопки "Запросить выплату"
- ❌ Выбора метода (USDT/TON)
- ❌ Ввода адреса кошелька
- ❌ Истории выплат

**Где должна быть реализация:**
```python
# Требуется добавить:
@router.callback_query(F.data.startswith("ch_payouts:"))
async def show_channel_payouts(callback: CallbackQuery) -> None:
    """Показать выплаты канала."""
    # TODO: Реализовать
    # 1. Получить доступную сумму (payout_repo.get_available_payout_amount)
    # 2. Показать кнопки: "Запросить выплату", "История"
    
@router.callback_query(F.data.startswith("request_payout:"))
async def request_payout(callback: CallbackQuery, state: FSMContext) -> None:
    """Запросить выплату."""
    # TODO: Реализовать FSM
    # 1. Выбор метода: USDT / TON
    # 2. Ввод адреса кошелька
    # 3. Подтверждение
    # 4. Создание Payout
```

**Payout модель:**
```python
# src/db/models/payout.py
class Payout(Base):
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("user.id"))
    amount = Column(Numeric(12, 2))
    method = Column(String(10))  # "USDT", "TON"
    wallet_address = Column(String(255))
    status = Column(String(20))  # "pending", "paid", "rejected"
    created_at = Column(DateTime)
    paid_at = Column(DateTime)
```

---

## РАЗДЕЛ C: ИСПРАВЛЕНИЯ ПО УВЕДОМЛЕНИЯМ

### Пропущенные типы уведомлений

|Тип|Статус|Где должно быть|
|---|------|---------------|
|Напоминание об ожидающей заявке (за 4 часа)|❌ НЕ РЕАЛИЗОВАНО|`notifications.py` + Celery Beat|
|Кампания завершена + ссылка на отчёт|⚠️ ЧАСТИЧНО|`notifications.py:format_campaign_done`|
|Возврат средств за несостоявшееся размещение|❌ НЕ РЕАЛИЗОВАНО|`billing_service.py`|
|A/B результат готов (через 24 ч)|❌ НЕ РЕАЛИЗОВАНО|`notifications.py` + Celery|
|Еженедельный дайджест (advertiser)|✅ РЕАЛИЗОВАНО|`notification_tasks.py:send_weekly_digest`|
|Еженедельный дайджест (owner)|✅ РЕАЛИЗОВАНО|`notification_tasks.py:send_weekly_digest`|

---

### Уведомление 1: Напоминание об ожидающей заявке

**Где должно быть:**
```python
# notification_tasks.py — требуется добавить:
@celery_app.task
def notify_pending_placement_reminder() -> dict[str, int]:
    """Напомнить владельцам о заявках старше 20 часов."""
    from datetime import timedelta
    
    # Найти заявки в PENDING_APPROVAL старше 20 часов
    twenty_hours_ago = datetime.now(UTC) - timedelta(hours=20)
    
    # Отправить уведомление владельцу
    stats = {"sent": 0, "errors": 0}
    for placement in pending_placements:
        try:
            await bot.send_message(
                chat_id=owner.telegram_id,
                text=f"⏰ <b>Напоминание о заявке</b>\n\n"
                     f"Заявка #{placement.id} ожидает вашего решения.\n"
                     f"Канал: @{channel.username}\n"
                     f"До автоодобрения: ~4 часа\n\n"
                     f"Перейдите в «Мои каналы» для просмотра.",
                parse_mode="HTML",
            )
            stats["sent"] += 1
        except Exception as e:
            stats["errors"] += 1
    
    return stats
```

**Планировщик (Celery Beat):**
```python
# celery_config.py — добавить:
"placement-reminder": {
    "task": "src.tasks.notification_tasks.notify_pending_placement_reminder",
    "schedule": crontab(minute=0, hour="*/4"),  # Каждые 4 часа
}
```

---

### Уведомление 2: Кампания завершена + ссылка на отчёт

**Где реализовано:**
```python
# notifications.py:61-75
def format_campaign_done(sent: int, total: int, rate: float) -> str:
    return (
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: <b>{sent}</b> из <b>{total}</b>\n"
        f"📊 Успешность: <b>{rate:.1f}%</b>\n\n"
        f"📄 Вы можете скачать подробный отчёт в формате PDF."
    )
```

**Проблема:** Кнопка "Скачать PDF" ведёт на заглушку (`download_report` → "🚧 Функция в разработке").

**Где отправляется:**
```python
# mailing_service.py — после завершения рассылки:
from src.bot.handlers.notifications import format_campaign_done

await bot.send_message(
    chat_id=user.telegram_id,
    text=format_campaign_done(sent, total, rate),
    # ❌ Нет кнопки для скачивания отчёта
)
```

---

### Уведомление 3: Возврат средств

**Где должно быть:**
```python
# billing_service.py — требуется добавить:
async def refund_campaign(campaign_id: int) -> bool:
    """Вернуть средства за несостоявшееся размещение."""
    # TODO: Реализовать
    # 1. Получить кампанию
    # 2. Рассчитать сумму возврата
    # 3. Зачислить на баланс
    # 4. Создать Transaction (type=REFUND)
    # 5. Отправить уведомление
    
async def notify_refund(user_id: int, amount: float, campaign_title: str) -> None:
    """Уведомить о возврате средств."""
    text = (
        f"💰 <b>Возврат средств</b>\n\n"
        f"Кампания: {campaign_title}\n"
        f"Сумма возврата: {amount} кр\n\n"
        f"Средства зачислены на ваш баланс."
    )
    await bot.send_message(chat_id=user_id, text=text)
```

---

### Уведомление 4: A/B результат готов

**Где должно быть:**
```python
# notification_tasks.py — требуется добавить:
@celery_app.task
def notify_ab_test_result(campaign_id: int) -> None:
    """Уведомить о результате A/B теста."""
    # TODO: Реализовать
    # Через 24 часа после запуска A/B теста:
    # 1. Получить статистику по вариантам
    # 2. Определить победителя
    # 3. Отправить уведомление
    
    text = (
        f"📊 <b>Результат A/B теста</b>\n\n"
        f"Кампания: {campaign.title}\n\n"
        f"🏆 Победитель: Вариант {winner}\n"
        f"• CTR: {winner_ctr:.2f}%\n"
        f"• Конверсия: {winner_conv:.2f}%\n\n"
        f"Вариант A: {a_ctr:.2f}% CTR\n"
        f"Вариант B: {b_ctr:.2f}% CTR"
    )
```

---

## РАЗДЕЛ D: ИСПРАВЛЕНИЯ FSM

### Ошибка в CampaignStates

**Проблема:** В разделе 10.2 указано состояние `waiting_title`, но в Flow 17 первым шагом указан `waiting_topic`.

**Реальность по коду:**
```python
# campaigns.py:56-100
@router.callback_query(MainMenuCB.filter(F.action == "create_campaign"))
async def start_campaign_wizard(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать wizard создания кампании."""
    text = (
        "📝 <b>Создание кампании</b>\n\n"
        "Шаг 1 из 7: Выберите тематику вашей кампании."
    )
    await safe_callback_edit(callback, text, reply_markup=get_topics_kb())
    await state.set_state(CampaignStates.waiting_topic)  # ✅ ПЕРВЫЙ ШАГ
```

**CampaignStates (campaign.py:8-32):**
```python
class CampaignStates(StatesGroup):
    waiting_title = State()       # ❌ НЕ ИСПОЛЬЗУЕТСЯ
    waiting_topic = State()       # ✅ ШАГ 1
    waiting_header = State()      # ✅ ШАГ 2 (заголовок, не title)
    waiting_text = State()        # ✅ ШАГ 3
    waiting_ai_description = State()  # ✅ Для AI генерации
    waiting_image = State()       # ✅ ШАГ 4
    waiting_member_count = State()  # ✅ ШАГ 5
    waiting_schedule = State()    # ✅ ШАГ 6
    waiting_confirm = State()     # ✅ ШАГ 7
```

**Исправление:** `waiting_title` — **мёртвое состояние**, не используется. Должно быть удалено или переименовано в `waiting_header`.

---

### Тупики (Dead-ends)

**Анализ FSM матрицы из раздела 13.3:**

#### CampaignCreateState (AI wizard)

|Состояние|Кнопка "Назад"|Кнопка "Отмена"|Статус|
|---------|-------------|---------------|------|
|`selecting_style`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`selecting_category`|✅ Есть (`back_to_style`)|❌ Нет|⚠️ Частично|
|`entering_custom_category`|✅ Есть (`back_to_category`)|❌ Нет|⚠️ Частично|
|`waiting_for_description`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`waiting_for_campaign_name`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`selecting_variant`|✅ Есть (`back_to_category`)|❌ Нет|⚠️ Частично|
|`editing_text`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`waiting_for_url`|✅ Есть (`skip_url`)|❌ Нет|⚠️ Частично|
|`waiting_for_image`|✅ Есть (`skip_image`)|❌ Нет|⚠️ Частично|
|`selecting_audience`|✅ Есть (`back_to_image`)|❌ Нет|⚠️ Частично|
|`setting_budget`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`setting_schedule`|✅ Есть (`back_to_budget`)|❌ Нет|⚠️ Частично|
|`entering_schedule_date`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`confirming`|❌ Нет|❌ Нет|🔴 ТУПИК|

**Итого:** 7 тупиков из 14 состояний (50%)

#### CampaignStates (Manual wizard)

|Состояние|Кнопка "Назад"|Кнопка "Отмена"|Статус|
|---------|-------------|---------------|------|
|`waiting_topic`|✅ Есть|✅ Есть|✅ OK|
|`waiting_header`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`waiting_text`|✅ Есть|✅ Есть|✅ OK|
|`waiting_ai_description`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`waiting_image`|✅ Есть|✅ Есть|✅ OK|
|`waiting_member_count`|✅ Есть|✅ Есть|✅ OK|
|`waiting_schedule`|✅ Есть|✅ Есть|✅ OK|
|`waiting_confirm`|✅ Есть|✅ Есть|✅ OK|

**Итого:** 2 тупика из 9 состояний (22%)

#### AddChannelStates

|Состояние|Кнопка "Назад"|Кнопка "Отмена"|Статус|
|---------|-------------|---------------|------|
|`waiting_username`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`waiting_bot_admin_confirmation`|✅ Есть (`back_to_username`)|❌ Нет|⚠️ Частично|
|`waiting_price`|❌ Нет|❌ Нет|🔴 ТУПИК|
|`waiting_topics`|✅ Есть (`back_to_price`)|❌ Нет|⚠️ Частично|
|`waiting_settings`|✅ Есть (`back_to_topics`)|❌ Нет|⚠️ Частично|
|`waiting_confirm`|✅ Есть (`back_to_settings`)|❌ Нет|⚠️ Частично|

**Итого:** 2 тупика из 6 состояний (33%)

---

## РАЗДЕЛ E: THROTTLING

**Статус:** ✅ РЕАЛИЗОВАНО

**Файл:** `src/bot/middlewares/throttling.py`

**Лимиты:**
```python
THROTTLE_TIME = 0.5  # секунды между запросами
```

**Что ограничивается:**
- Все сообщения (`Message`)
- Все callback query (`CallbackQuery`)
- Все обновления (`Update`)

**Сообщение при превышении:**
```python
if isinstance(event, Message):
    await event.answer("⏳ Подождите немного...")
elif isinstance(event, CallbackQuery):
    await event.answer("⏳ Подождите немного...", show_alert=False)
```

**Проблема:** Лимит **0.5 секунды** слишком мал для пользователей. Рекомендуется увеличить до 1-2 секунд.

**Где применяется:**
```python
# bot/main.py — middleware registration:
dp.update.middleware(ThrottlingMiddleware(redis))
```

---

## РАЗДЕЛ F: PRD VS РЕАЛИЗАЦИЯ

### Таблица сравнения

|Функция по PRD|Статус по PRD|Статус в коде|Расхождение|
|--------------|-------------|-------------|-----------|
|Эскроу при запуске кампании|✅ В PRD|❌ Заглушка|P0 БЛОКЕР|
|Предпросмотр поста (шаг 6 визарда)|✅ В PRD|✅ Реализовано|OK|
|Умное выбор времени публикации|❌ В PRD|❌ Не реализовано|OK (не планировалось)|
|A/B тестирование|✅ В PRD|❌ Не реализовано|P1 БЛОКЕР|
|Детектор накрутки|❌ В PRD|❌ Не реализовано|OK|
|Сравнение каналов|❌ В PRD|❌ Не реализовано|OK|
|Медиакит канала|❌ В PRD|❌ Не реализовано|OK|
|Автоодобрение заявок (24ч)|✅ В PRD|❌ Не реализовано|P1 БЛОКЕР|
|Напоминание о заявке (20ч)|✅ В PRD|❌ Не реализовано|P2|
|Возврат средств|✅ В PRD|❌ Заглушка|P0 БЛОКЕР|
|PDF отчёт|✅ В PRD|⚠️ Заглушка|P2|
|История выплат|✅ В PRD|❌ Не реализовано|P1|

---

### Эскроу-механика (P0 БЛОКЕР)

**По PRD:**
> При запуске кампании средства замораживаются на эскроу-счёте. После публикации поста 80% переводится владельцу, 20% — платформе.

**По коду:**
```python
# billing_service.py — заглушка:
async def freeze_campaign_funds(campaign_id: int) -> bool:
    """Заморозить средства кампании на эскроу."""
    # TODO: Реализовать
    return False

async def release_escrow_funds(placement_id: int) -> bool:
    """Освободить средства эскроу после публикации."""
    # TODO: Реализовать
    return False
```

**Проблема:** В `confirm_launch()` (campaigns.py:830) **нет вызова** `freeze_campaign_funds()`. Средства списываются сразу или не списываются вообще.

**Где должно быть:**
```python
# campaigns.py:830-900 — confirm_launch
async def confirm_launch(callback: CallbackQuery, state: FSMContext) -> None:
    # ... проверки ...
    
    # ✅ ДОЛЖНО БЫТЬ:
    frozen = await billing_service.freeze_campaign_funds(campaign.id)
    if not frozen:
        await callback.answer("❌ Ошибка заморозки средств", show_alert=True)
        return
    
    # Запуск рассылки
    await send_campaign.delay(campaign.id)
```

---

### A/B тестирование (P1 БЛОКЕР)

**По PRD:**
> Рекламодатель создаёт 2 варианта текста. Бот отправляет каждый вариант 50% аудитории. Через 24 часа сравнивается CTR и определяется победитель.

**По коду:**
- ❌ Нет модели `CampaignVariant`
- ❌ Нет handler для создания вариантов
- ❌ Нет Celery задачи для сравнения результатов
- ❌ Нет уведомления о результате

**Где должно быть:**
```python
# campaign_create_ai.py — после выбора варианта:
@router.callback_query(AIEditCB.filter(F.action == "create_ab_test"))
async def create_ab_test(callback: CallbackQuery) -> None:
    """Создать A/B тест с двумя вариантами."""
    # TODO: Реализовать
    # 1. Сгенерировать второй вариант
    # 2. Сохранить оба варианта
    # 3. Разделить аудиторию 50/50
    # 4. Запустить рассылку
```

---

## РАЗДЕЛ G: НЕСООТВЕТСТВИЯ

### Реферальный бонус

**В отчёте:** "50₽ за каждого"

**По коду:**
```python
# start.py:228-236
if ref_code and is_new:
    referrer = await user_repo.get_by_referral_code(ref_code)
    if referrer:
        bonus_amount = 50.0  # 50₽ бонус за реферала
        await billing_service.apply_referral_bonus(
            referrer_id=referrer.id,
            referred_user_id=user.id,
            bonus_amount=Decimal(str(bonus_amount)),
        )
```

**В billing_service.py:**
```python
async def apply_referral_bonus(self, referrer_id: int, referred_user_id: int, bonus_amount: Decimal) -> None:
    """Применить реферальный бонус."""
    # Зачислить 50₽ (кредитов) на баланс
```

**Итог:** **50 кредитов** (не рублей), что ≈ 50₽. В отчёте указано верно.

---

### Уровни XP

**В отчёте:** "7 уровней (1-7)"

**По коду:**
```python
# cabinet.py:38-45
LEVEL_NAMES = {
    1: "Новичок 🌱",
    2: "Участник ⭐",
    3: "Активный 🔥",
    4: "Опытный 💎",
    5: "Профи 🚀",
    6: "Эксперт 🎯",
    7: "Мастер 👑",
}

LEVEL_XP = {
    1: 0,
    2: 500,
    3: 1500,
    4: 3500,
    5: 7500,
    6: 15000,
    7: 30000,
}
```

**Итог:** **7 уровней** — верно. В PRD могло быть 5 или 10, но в коде 7.

---

### Точка входа в реферальную программу

**В отчёте:** `billing:referral`

**По коду:**
```python
# cabinet.py:317-377
@router.callback_query(BillingCB.filter(F.action == "referral"))
async def referral_callback(callback: CallbackQuery) -> None:
    """Показать реферальную информацию."""
```

**Где вызывается:**
```python
# cabinet.py:260-280 — get_cabinet_kb
builder.button(text="👥 Рефералы", callback_data=BillingCB(action="referral"))
```

**Итог:** `billing:referral` — **верно**, вызывается из кабинета.

---

## РАЗДЕЛ H: ДОПОЛНИТЕЛЬНЫЕ HANDLERS

### channels_db.py

**Назначение:** База каналов — статистика, поиск по категориям, фильтры.

**Точки входа:**
- `main:channels_db` → `show_channels_menu()`
- `channels:stats` → `handle_channels_stats()`
- `channels:categories` → `handle_categories()`
- `channels:category` → `handle_category_selected()`
- `channels:subcategories` → `handle_subcategories()`
- `channels:tariff` → `handle_tariff_filter()`
- `channels:top_channels` → `handle_top_channels()`
- `channels:advanced_filters` → `handle_advanced_filters()`
- `channels:filter_er` → `handle_er_filter()`
- `channels:filter_rating` → `handle_rating_filter()`
- `channels:filter_fraud` → `handle_fraud_filter()`
- `channels:menu` → `handle_channels_menu()`

**Flow:** Пользователь выбирает категорию → применяются фильтры → показывается список каналов с пагинацией.

---

### templates.py

**Назначение:** Библиотека шаблонов рекламных текстов.

**Точки входа:**
- `main:templates` → `handle_templates_menu()`
- `campaign:template_category` → `handle_category_selected()`
- `campaign:template_preview` → `handle_template_preview()`
- `campaign:template_use` → `handle_template_use()`

**Flow:** Пользователь выбирает категорию → выбирает шаблон → просматривает → использует в визарде создания кампании.

**Связь с Flow 17:** После выбора шаблона переход на `CampaignStates.waiting_title`.

---

### models.py

**Назначение:** Выбор AI модели (для админов).

**Точки входа:**
- Команда: `/models` → `handle_models()`
- `model:tariff_info` → `handle_tariff_info()`
- `model:select` → `handle_model_select()`
- `model:back` → `handle_model_back()`

**Доступ:** Только для админов (`is_admin(user_id)`).

**Проблема:** Для обычных пользователей команда `/models` показывает заглушку.

---

### monitoring.py

**Назначение:** Мониторинг сервера и задач Celery (admin only).

**Точки входа:**
- `admin:server_monitoring` → `show_server_monitoring()`
- `admin:celery_tasks` → `show_celery_tasks()`

**Статус:** ⚠️ Заглушки. Реальные данные требуют SSH/API доступа.

---

## РАЗДЕЛ I: ИТОГОВАЯ ТАБЛИЦА ИСПРАВЛЕНИЙ

|Проблема|Приоритет|Где исправить|Статус|
|--------|---------|-------------|------|
|Flow 3.7-3.10, 3.13-3.15, 3.18, 3.20-3.21, 3.24-3.27|P0|Добавить handlers|❌ Требует реализации|
|Эскроу-механика|P0|`billing_service.py`|❌ Заглушка|
|A/B тестирование|P1|`campaign_create_ai.py`|❌ Не реализовано|
|Автоодобрение заявок|P1|`notification_tasks.py`|❌ Не реализовано|
|Напоминание о заявке (20ч)|P2|`notification_tasks.py`|❌ Не реализовано|
|PDF отчёт|P2|`notifications.py`|⚠️ Заглушка|
|История выплат|P1|`channel_owner.py`|❌ Не реализовано|
|Тупики FSM (11 состояний)|P2|Все `*_create.py`, `campaigns.py`|⚠️ Требует кнопок|
|Throttling 0.5с|P3|`throttling.py`|⚠️ Увеличить до 1-2с|
|Рефбонус 50 кр|OK|—|✅ Верно|
|7 уровней XP|OK|—|✅ Верно|

---

**ЗАКЛЮЧЕНИЕ:**

UX_AUDIT_REPORT.md принят **частично**. Требуется дополнение по 14 пунктам (см. выше). Критические проблемы:

1. **12 flow не описаны** — добавлены в Разделе A
2. **Эскроу не работает** — P0 блокер, требует реализации
3. **5 типов уведомлений пропущены** — добавлены в Разделе C
4. **Flow выплат не описан** — добавлен в Разделе B
5. **FSM тупики не проанализированы** — добавлены в Разделе D
6. **PRD vs реализация отсутствует** — добавлен в Разделе F

**Рекомендация:** Использовать этот документ как **чек-лист для доработки** перед релизом.
