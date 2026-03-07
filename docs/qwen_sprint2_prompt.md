# Qwen Code Промт: Спринт 2 — Маркетплейс, аналитика, отзывы

## Обязательная ориентация перед стартом

```powershell
cd ~/python-projects/market-telegram-bot
source .venv/Scripts/activate

# 1. Прочитай дорожную карту целиком
cat ROADMAP.md

# 2. Убедись что Спринт 1 завершён и смержен в develop
git log --oneline develop | head -15
# Должны быть все коммиты sprint/1:
# feat(notifications): add owner placement and payout notification tasks
# feat(billing): add escrow freeze/release/refund to billing_service
# feat(payout): add payout_service with calculation logic
# feat(channel-owner): add placement approval flow
# feat(channel-owner): add /my_channels and channel settings
# feat(payout): add Payout model and migration
```

После чтения дорожной карты зафикси:
- Какие сущности из Спринта 1 использует Спринт 2 (`placement_id` в Review, `Payout` для уведомлений)
- Что из Спринта 2 потребуется Спринту 3 (рейтинги используют `Review.score_compliance`)
- Какой конкурентный gap закрывает этот спринт (измеримость vs Telega.io)

---

## Контекст Спринта 2

### Что добавляет этот спринт

Рекламодатель впервые получает **измеримый результат**: CTR, CPM, ROI, PDF-отчёт.
Система отзывов строит доверие между сторонами. Предпросмотр устраняет конфликты
«пост выглядит не так».

Это прямой ответ на слабость прямых договорённостей и ключевой аргумент продаж.

### Что уже есть после Спринта 1

| Сущность | Что доступно |
|----------|-------------|
| `Payout` | Модель с `placement_id`, `owner_id`, `channel_id`, `amount`, `status` |
| `billing_service` | `freeze_funds`, `release_funds_for_placement`, `refund_frozen_funds` |
| `payout_service` | `calculate_payout_amount`, `create_pending_payout`, `get_owner_balance` |
| Модель размещения | Известна из Спринта 1 — есть `placement_id`, `campaign_id`, `channel_id` |
| `channel_owner.py` | Одобрение/отклонение заявок |

### Состав Спринта 2

| # | Задача | Файлы |
|---|--------|-------|
| 2.1 | Модель Review + миграция | `models/review.py`, `alembic/` |
| 2.2 | Сервис и хэндлер отзывов | `services/review_service.py`, `handlers/campaigns.py` |
| 2.3 | Предпросмотр поста в мастере | `handlers/campaigns.py` |
| 2.4 | CTR-трекинг коротких ссылок | `models/`, `api/routers/`, `services/link_tracking_service.py` |
| 2.5 | CPM / CTR / ROI + PDF-отчёт | `services/analytics_service.py`, `handlers/campaign_analytics.py` |
| 2.6 | Умный выбор времени публикации | `services/timing_service.py`, `handlers/campaigns.py` |

---

## ГЛОБАЛЬНЫЕ ПРАВИЛА

1. **Читай файл целиком** перед любым изменением
2. **Не ломай существующий флоу** создания кампании — только добавляй шаги
3. **Один коммит на задачу** строго по плану
4. **После каждой задачи** — полный прогон проверок:

```powershell
poetry run ruff check src/
poetry run mypy src/ --ignore-missing-imports 2>&1 | tail -3
```

---

## ПОДГОТОВКА

```powershell
git checkout develop && git pull origin develop
git checkout -b sprint/2
git log --oneline -8
```

### Разведка структуры

```powershell
# Модель размещения (placement/mailing_log) — нужна для Review.placement_id
grep -rn "class.*MailingLog\|class.*Placement\|__tablename__" \
  src/db/models/ --include="*.py" | grep -iv "user\|campaign\|transaction\|content\|notif"

# Текущий мастер кампании — будем добавлять шаги
cat src/bot/handlers/campaigns.py | head -120

# Текущий campaign_analytics.py — будем расширять
cat src/bot/handlers/campaign_analytics.py

# Как устроены FastAPI роутеры
cat src/api/routers/analytics.py | head -60

# Telethon клиент — нужен для timing_service
grep -rn "TelegramClient\|telethon\|get_entity\|iter_messages" \
  src/ --include="*.py" | grep -v "test\|#" | head -10
```

---

## ЗАДАЧА 2.1: Модель Review и миграция

### Шаг 2.1.1 — Изучи образцовую модель

```powershell
# Возьми Transaction или Payout за образец стиля
cat src/db/models/transaction.py 2>/dev/null || cat src/db/models/payout.py
# Зафикси: стиль (Mapped vs Column), как импортируется Base
```

### Шаг 2.1.2 — Создай модель

**Файл:** `src/db/models/review.py`

```python
"""
Модель отзывов — двусторонняя система оценки.
Рекламодатель оценивает канал, владелец оценивает рекламодателя.

Антифрод: отзыв только по завершённому размещению, один отзыв на пару
(reviewer_id + placement_id), дубликаты автоскрываются.
"""
# ⚠️ АДАПТИРУЙ импорты под стиль проекта

class ReviewerRole(str, PyEnum):
    ADVERTISER = "advertiser"  # рекламодатель оценивает канал
    OWNER = "owner"            # владелец оценивает рекламодателя


class Review(Base):
    __tablename__ = "reviews"

    # id, created_at — по образцу существующих моделей

    reviewer_id: ...     # BigInteger FK → users.id
    reviewee_id: ...     # BigInteger FK → users.id
    channel_id: ...      # BigInteger FK → telegram_chats.id, nullable
    placement_id: ...    # BigInteger FK → [таблица_размещений].id, NOT NULL

    reviewer_role: ...   # String(20), PayoutCurrency enum

    # Оценки рекламодателя → каналу (заполняются если reviewer_role=ADVERTISER)
    score_compliance: ... # SmallInteger 1-5, nullable
    score_audience: ...   # SmallInteger 1-5, nullable
    score_speed: ...      # SmallInteger 1-5, nullable

    # Оценки владельца → рекламодателю (заполняются если reviewer_role=OWNER)
    score_material: ...      # SmallInteger 1-5, nullable
    score_requirements: ...  # SmallInteger 1-5, nullable
    score_payment: ...       # SmallInteger 1-5, nullable

    comment: ...     # Text, nullable (до 1000 символов)
    is_hidden: ...   # Boolean, default=False (антифрод — скрыт до проверки)

    # ⚠️ Добавь уникальный индекс: (reviewer_id, placement_id)
    # чтобы не допустить двух отзывов от одного человека за одно размещение
    # __table_args__ = (UniqueConstraint("reviewer_id", "placement_id"),)
```

⚠️ Заполни все `...` реальными типами. Добавь `UniqueConstraint`.

### Шаг 2.1.3 — Миграция

```powershell
# Добавь импорт Review в alembic/env.py рядом с другими моделями
grep -n "import.*models" alembic/env.py

poetry run alembic revision --autogenerate -m "add_review_model"
cat alembic/versions/[последний].py  # проверь upgrade/downgrade

poetry run alembic upgrade head
poetry run alembic current  # → head
```

### Шаг 2.1.4 — Проверка

```powershell
poetry run ruff check src/db/models/review.py
poetry run mypy src/db/models/review.py --ignore-missing-imports
```

### Коммит 2.1

```powershell
git add src/db/models/review.py alembic/versions/ alembic/env.py
git commit -m "feat(review): add Review model and migration"
```

---

## ЗАДАЧА 2.2: Сервис и хэндлер отзывов

### Шаг 2.2.1 — Создай ReviewService

**Файл:** `src/core/services/review_service.py`

```python
"""
Сервис двусторонних отзывов.

Логика запроса:
- После завершения кампании → запрос рекламодателю об оценке каждого канала
- После зачисления выплаты → запрос владельцу об оценке рекламодателя

Антифрод:
- Один отзыв на (reviewer_id + placement_id) — контролируется UniqueConstraint
- Дубликаты по тексту (схожесть > 90%) → is_hidden=True до ручной проверки
"""
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ReviewService:

    # ⚠️ АДАПТИРУЙ: инжекция зависимостей как в других сервисах

    async def request_review_from_advertiser(self, placement_id: int) -> None:
        """
        Запросить отзыв от рекламодателя после завершения размещения.
        Отправляет уведомление через Celery задачу.
        """
        # ⚠️ Получи placement → campaign → advertiser user
        # Вызови notification_tasks.request_advertiser_review.delay(placement_id)
        pass

    async def request_review_from_owner(self, placement_id: int) -> None:
        """Запросить отзыв от владельца канала после выплаты."""
        # ⚠️ Получи placement → channel → owner user
        # Вызови notification_tasks.request_owner_review.delay(placement_id)
        pass

    async def submit_review(
        self,
        reviewer_id: int,
        placement_id: int,
        reviewer_role: str,
        scores: dict[str, int],
        comment: str | None = None,
    ) -> "Review":
        """
        Сохранить отзыв.

        scores пример для рекламодателя:
            {"compliance": 5, "audience": 4, "speed": 5}
        scores пример для владельца:
            {"material": 4, "requirements": 5, "payment": 5}

        Raises:
            ValueError: если отзыв уже существует (UniqueConstraint)
            ValueError: если оценки вне диапазона 1-5
        """
        # Валидация оценок
        for key, val in scores.items():
            if not (1 <= val <= 5):
                raise ValueError(f"Score '{key}' must be 1-5, got {val}")

        # Антифрод: проверка дубликатов комментариев
        is_hidden = False
        if comment:
            is_hidden = await self.check_duplicate_fraud(comment)

        # ⚠️ АДАПТИРУЙ: сохрани Review через репозиторий / сессию
        # Найди reviewee_id из placement (владелец канала или рекламодатель)
        pass

    async def get_channel_rating(self, channel_id: int) -> float:
        """
        Средняя оценка канала по score_compliance из всех НЕ скрытых отзывов.
        Используется в карточке канала и рейтинге надёжности.
        Returns 0.0 если отзывов нет.
        """
        # ⚠️ SELECT AVG(score_compliance) WHERE channel_id=... AND is_hidden=False
        return 0.0

    async def check_duplicate_fraud(self, comment: str) -> bool:
        """
        Антифрод: проверить похожесть нового комментария на последние 50 отзывов.
        Если схожесть > 90% хотя бы с одним — скрыть.
        """
        # ⚠️ Получи последние 50 комментариев
        # recent_comments = await review_repo.get_recent_comments(limit=50)
        # for existing in recent_comments:
        #     ratio = SequenceMatcher(None, comment.lower(), existing.lower()).ratio()
        #     if ratio > 0.9:
        #         return True
        return False
```

### Шаг 2.2.2 — Добавь FSM запроса отзыва в хэндлер кампаний

```powershell
# Найди где завершается кампания в handlers
grep -n "DONE\|completed\|campaign_done\|finish\|завершена" \
  src/bot/handlers/campaigns.py src/bot/handlers/campaign_analytics.py | head -15

# Найди состояния FSM
cat src/bot/states/campaign.py
```

В `src/bot/states/campaign.py` добавь:
```python
class ReviewStates(StatesGroup):
    """Состояния флоу сбора отзыва после завершения кампании."""
    choosing_channel_to_review = State()   # выбор канала из списка
    rating_compliance = State()            # оценка соответствия договорённостям
    rating_audience = State()              # оценка качества аудитории
    rating_speed = State()                 # оценка скорости
    leaving_comment = State()             # опциональный комментарий
```

В `src/bot/handlers/campaigns.py` добавь хэндлер запроса отзыва:

```python
@router.callback_query(F.data.startswith("leave_review:"))
async def start_review_flow(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Начать флоу отзыва о конкретном канале.
    callback.data = "leave_review:{placement_id}"
    """
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    placement_id = int((callback.data or "").split(":")[1])
    await state.update_data(review_placement_id=placement_id)
    await state.set_state(ReviewStates.rating_compliance)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=str(i), callback_data=f"review_score:compliance:{i}")
        for i in range(1, 6)
    ]])

    await safe_callback_edit(
        callback.message,
        "⭐ <b>Оцените соответствие договорённостям</b>\n\n"
        "1 — обещания не выполнены\n"
        "5 — всё точно как договорились",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(
    ReviewStates.rating_compliance,
    F.data.startswith("review_score:compliance:"),
)
async def review_score_compliance(callback: CallbackQuery, state: FSMContext) -> None:
    """Записать оценку compliance, перейти к следующей."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    score = int((callback.data or "").split(":")[-1])
    await state.update_data(score_compliance=score)
    await state.set_state(ReviewStates.rating_audience)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=str(i), callback_data=f"review_score:audience:{i}")
        for i in range(1, 6)
    ]])

    await safe_callback_edit(
        callback.message,
        "⭐ <b>Оцените качество аудитории</b>\n\n"
        "Совпал ли реальный результат с ожидаемым охватом?",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ⚠️ По аналогии добавь rating_speed и leave_comment хэндлеры
# Финальный хэндлер вызывает review_service.submit_review(...)
```

### Шаг 2.2.3 — Добавь Celery задачу запроса отзыва

В `src/tasks/notification_tasks.py`:

```python
@celery_app.task(name="notifications:request_post_campaign_reviews")
def request_post_campaign_reviews(campaign_id: int) -> None:
    """
    После завершения кампании — отправить запросы отзывов обеим сторонам.
    Планируется с задержкой 1 час после завершения кампании.

    Для каждого placement кампании:
    - Рекламодателю: запрос оценить канал
    - Владельцу канала: запрос оценить рекламодателя
    """
    # ⚠️ АДАПТИРУЙ: получи все placements кампании → для каждого вызови
    # review_service.request_review_from_advertiser(placement_id)
    # review_service.request_review_from_owner(placement_id)
    pass
```

Найди в `mailing_tasks.py` где кампания переходит в статус DONE — добавь вызов:
```python
request_post_campaign_reviews.apply_async(
    args=[campaign_id],
    countdown=3600,  # через 1 час после завершения
)
```

### Проверка

```powershell
poetry run ruff check src/core/services/review_service.py src/bot/handlers/campaigns.py
poetry run mypy src/core/services/review_service.py --ignore-missing-imports
```

### Unit тест

**Файл:** `tests/unit/test_review_service.py`

```python
"""Unit тесты ReviewService."""
import pytest
from unittest.mock import AsyncMock, patch
from src.core.services.review_service import ReviewService


class TestReviewService:

    def setup_method(self):
        self.service = ReviewService()  # ⚠️ адаптируй если нужны аргументы

    def test_validate_scores_range(self):
        """Оценки вне 1-5 вызывают ValueError."""
        import asyncio
        with pytest.raises(ValueError, match="must be 1-5"):
            asyncio.run(self.service.submit_review(
                reviewer_id=1, placement_id=1,
                reviewer_role="advertiser",
                scores={"compliance": 6},  # невалидная оценка
            ))

    @pytest.mark.asyncio
    async def test_duplicate_fraud_high_similarity(self):
        """Очень похожие комментарии скрываются."""
        with patch.object(self.service, 'check_duplicate_fraud', return_value=True):
            # submit_review с is_hidden=True проходит без ошибки
            pass  # ⚠️ реализуй после изучения метода

    @pytest.mark.asyncio
    async def test_duplicate_fraud_unique_comment(self):
        """Уникальные комментарии не скрываются."""
        result = await self.service.check_duplicate_fraud("Отличный канал, рекомендую!")
        # Без данных в БД — всегда False (нечего сравнивать)
        assert isinstance(result, bool)
```

### Коммит 2.2

```powershell
git add src/core/services/review_service.py \
        src/bot/handlers/campaigns.py \
        src/bot/states/campaign.py \
        src/tasks/notification_tasks.py \
        tests/unit/test_review_service.py
git commit -m "feat(review): add review_service and post-campaign review request flow"
```

---

## ЗАДАЧА 2.3: Предпросмотр поста в мастере кампании

### Шаг 2.3.1 — Найди текущие шаги мастера

```powershell
cat src/bot/handlers/campaigns.py
cat src/bot/states/campaign_create.py 2>/dev/null || cat src/bot/states/campaign.py
```

Зафикси:
- После какого шага идёт ввод текста объявления?
- Как в FSM-состояниях называется шаг подтверждения?
- Как хранится `text` и `image_file_id` в FSM-данных?

### Шаг 2.3.2 — Добавь состояние предпросмотра

В файл состояний добавь:
```python
preview_confirm = State()  # просмотр итогового вида поста
```

### Шаг 2.3.3 — Добавь шаг предпросмотра

Найди хэндлер который принимает текст объявления и переходит к следующему шагу.
После сохранения текста — вместо прямого перехода к следующему шагу,
**сначала показать предпросмотр**:

```python
# ⚠️ АДАПТИРУЙ: найди реальный хэндлер сохранения текста в FSM

async def show_post_preview(message_or_callback, state: FSMContext) -> None:
    """
    Показать пост точно в том виде как он будет выглядеть в канале.
    Это отдельный шаг перед подтверждением — без изменений в БД.
    """
    data = await state.get_data()
    ad_text: str = data.get("ad_text", "")
    image_file_id: str | None = data.get("image_file_id")

    await state.set_state(...)  # ⚠️ состояние preview_confirm

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Выглядит хорошо", callback_data="preview_ok"),
            InlineKeyboardButton(text="✏️ Изменить текст", callback_data="preview_edit_text"),
        ]
    ])

    preview_header = (
        "👁 <b>Предпросмотр поста</b>\n"
        "Именно так пост увидят подписчики канала:\n"
        "─────────────────────\n\n"
    )

    # Отправка с медиа или без — в зависимости от наличия image_file_id
    if image_file_id:
        # ⚠️ используй message.answer_photo если это Message,
        # или callback.message.answer_photo если CallbackQuery
        pass
    else:
        # ⚠️ answer с HTML parse_mode
        pass
```

⚠️ Предпросмотр — **только отображение**, никаких записей в БД.

### Шаг 2.3.4 — Хэндлеры confirm/edit

```python
@router.callback_query(F.data == "preview_ok")
async def preview_confirmed(callback: CallbackQuery, state: FSMContext) -> None:
    """Пользователь доволен — перейти к следующему шагу мастера."""
    # ⚠️ Переключи на следующее состояние (то что было после текста до этого изменения)
    pass


@router.callback_query(F.data == "preview_edit_text")
async def preview_edit_text(callback: CallbackQuery, state: FSMContext) -> None:
    """Вернуть пользователя к вводу текста."""
    # ⚠️ Переключи на состояние ввода текста
    pass
```

### Проверка

```powershell
poetry run ruff check src/bot/handlers/campaigns.py
poetry run mypy src/bot/handlers/campaigns.py --ignore-missing-imports
```

### Коммит 2.3

```powershell
git add src/bot/handlers/campaigns.py src/bot/states/
git commit -m "feat(campaign): add post preview step in campaign wizard"
```

---

## ЗАДАЧА 2.4: CTR-трекинг коротких ссылок

### Шаг 2.4.1 — Добавь поля трекинга в модель размещения

```powershell
# Найди модель размещения (из разведки)
cat src/db/models/[placement_model].py
```

Добавь поля (НЕ меняй существующие):
```python
# Трекинг ссылок (Спринт 2)
tracking_url: ...    # Text, nullable — оригинальная ссылка рекламодателя
short_code: ...      # String(16), nullable, unique — короткий код для редиректа
clicks_count: ...    # Integer, default=0 — счётчик кликов
```

Создай миграцию: `"add_tracking_fields_to_placement"`

### Шаг 2.4.2 — Создай LinkTrackingService

**Файл:** `src/core/services/link_tracking_service.py`

```python
"""
Сервис отслеживания переходов по рекламным ссылкам.
Генерирует короткие коды, обрабатывает редиректы, считает клики.
"""
import secrets
import string
import logging

logger = logging.getLogger(__name__)

SHORT_CODE_ALPHABET = string.ascii_letters + string.digits  # a-z A-Z 0-9
SHORT_CODE_LENGTH = 8


class LinkTrackingService:

    def generate_short_code(self) -> str:
        """Генерировать уникальный 8-символьный код (62^8 = ~218 трлн вариантов)."""
        return "".join(secrets.choice(SHORT_CODE_ALPHABET) for _ in range(SHORT_CODE_LENGTH))

    async def create_tracking_link(
        self,
        placement_id: int,
        original_url: str,
    ) -> str:
        """
        Создать короткую ссылку для размещения.
        Сохраняет short_code и tracking_url в запись размещения.
        Returns: полный URL короткой ссылки (например: https://t.me/bot?start=r_abc12345)
        """
        code = self.generate_short_code()

        # Проверь уникальность — если коллизия, сгенерировать заново
        # ⚠️ АДАПТИРУЙ: сохрани short_code в placement через репозиторий
        # await placement_repo.update_tracking(placement_id, short_code=code, tracking_url=original_url)

        # ⚠️ АДАПТИРУЙ: используй реальный username бота из settings
        # bot_username = settings.BOT_USERNAME
        return f"https://t.me/bot?start=r_{code}"

    async def handle_click(self, short_code: str) -> str | None:
        """
        Обработать клик по короткой ссылке.
        Инкрементирует clicks_count, возвращает оригинальный URL для редиректа.
        Returns None если код не найден.
        """
        # ⚠️ АДАПТИРУЙ:
        # placement = await placement_repo.get_by_short_code(short_code)
        # if placement is None:
        #     return None
        # await placement_repo.increment_clicks(placement.id)
        # return placement.tracking_url
        return None

    async def get_click_stats(self, placement_id: int) -> dict:
        """Статистика кликов для размещения."""
        # ⚠️ АДАПТИРУЙ
        return {"clicks": 0, "short_code": None}
```

### Шаг 2.4.3 — FastAPI эндпоинт редиректа

В `src/api/routers/` найди подходящий роутер или создай `tracking.py`:

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

router = APIRouter(tags=["tracking"])


@router.get("/r/{short_code}", include_in_schema=False)
async def redirect_tracking_link(short_code: str) -> RedirectResponse:
    """
    Редирект по короткой ссылке с подсчётом кликов.
    Доступен без авторизации.
    """
    # ⚠️ АДАПТИРУЙ: получи link_tracking_service
    # url = await link_tracking_service.handle_click(short_code)
    # if url is None:
    #     raise HTTPException(status_code=404, detail="Link not found")
    # return RedirectResponse(url=url, status_code=302)
    raise HTTPException(status_code=404, detail="Not implemented yet")
```

Зарегистрируй роутер в главном файле FastAPI:
```powershell
grep -rn "include_router\|app.include" src/api/ --include="*.py" | head -10
```

### Шаг 2.4.4 — Unit тест генерации кодов

```python
# tests/unit/test_link_tracking.py
from src.core.services.link_tracking_service import LinkTrackingService, SHORT_CODE_LENGTH


def test_generate_short_code_length():
    svc = LinkTrackingService()
    code = svc.generate_short_code()
    assert len(code) == SHORT_CODE_LENGTH


def test_generate_short_code_uniqueness():
    svc = LinkTrackingService()
    codes = {svc.generate_short_code() for _ in range(1000)}
    assert len(codes) == 1000  # все 1000 уникальны


def test_generate_short_code_charset():
    import string
    svc = LinkTrackingService()
    code = svc.generate_short_code()
    allowed = set(string.ascii_letters + string.digits)
    assert all(c in allowed for c in code)
```

```powershell
poetry run pytest tests/unit/test_link_tracking.py -v
```

### Коммит 2.4

```powershell
git add src/db/models/ alembic/versions/ \
        src/core/services/link_tracking_service.py \
        src/api/routers/ \
        tests/unit/test_link_tracking.py
git commit -m "feat(analytics): add CTR tracking with short links and redirect endpoint"
```

---

## ЗАДАЧА 2.5: CPM / CTR / ROI и PDF-отчёт

### Шаг 2.5.1 — Прочитай analytics_service

```powershell
cat src/core/services/analytics_service.py
```

Зафикси: какие методы уже есть, как сервис получает данные из БД.

### Шаг 2.5.2 — Добавь методы расчёта

В `src/core/services/analytics_service.py` добавь (не меняй существующие):

```python
from decimal import Decimal
from dataclasses import dataclass


@dataclass
class CampaignMetrics:
    """Рассчитанные метрики кампании для отчёта."""
    total_views: int
    total_clicks: int
    total_cost: Decimal
    cpm: Decimal         # cost per 1000 views
    ctr: float           # clicks / views (0.0 если нет трекинга)
    cpc: Decimal         # cost per click (0 если нет кликов)
    channels_count: int
    success_rate: float  # доля успешно размещённых постов


async def calculate_campaign_metrics(self, campaign_id: int) -> CampaignMetrics:
    """
    Рассчитать полный набор метрик для кампании.

    CPM = cost / views * 1000
    CTR = clicks / views (только если есть tracking_url)
    CPC = cost / clicks (только если clicks > 0)
    """
    # ⚠️ АДАПТИРУЙ: получи campaign + placements + их метрики из БД
    # campaign = await campaign_repo.get_by_id(campaign_id)
    # placements = await placement_repo.get_by_campaign_id(campaign_id)
    #
    # total_views = sum(p.views_count for p in placements if p.views_count)
    # total_clicks = sum(p.clicks_count for p in placements if p.clicks_count)
    # total_cost = campaign.cost
    #
    # cpm = (total_cost / total_views * 1000) if total_views > 0 else Decimal(0)
    # ctr = (total_clicks / total_views) if total_views > 0 else 0.0
    # cpc = (total_cost / total_clicks) if total_clicks > 0 else Decimal(0)

    return CampaignMetrics(
        total_views=0, total_clicks=0, total_cost=Decimal("0"),
        cpm=Decimal("0"), ctr=0.0, cpc=Decimal("0"),
        channels_count=0, success_rate=0.0,
    )  # ← замени заглушки реальными расчётами


async def generate_campaign_pdf_report(self, campaign_id: int) -> bytes:
    """
    Сгенерировать PDF-отчёт по кампании.
    Использует reportlab.

    Содержит: название, период, метрики (CPM/CTR/ROI), таблицу по каналам.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from io import BytesIO
    except ImportError:
        raise ImportError("reportlab не установлен: poetry add reportlab")

    # ⚠️ АДАПТИРУЙ: получи данные кампании
    # campaign = await campaign_repo.get_by_id(campaign_id)
    # metrics = await self.calculate_campaign_metrics(campaign_id)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Заголовок
    story.append(Paragraph(
        f"Отчёт по рекламной кампании",
        styles["Title"]
    ))
    story.append(Spacer(1, 12))

    # Таблица метрик
    # ⚠️ Подставь реальные данные из metrics
    data = [
        ["Метрика", "Значение"],
        ["Просмотры", "0"],
        ["CPM", "0 ₽"],
        ["CTR", "0%"],
        ["Каналов", "0"],
    ]
    story.append(Table(data))

    doc.build(story)
    return buffer.getvalue()
```

### Шаг 2.5.3 — Добавь вывод метрик в campaign_analytics

```powershell
cat src/bot/handlers/campaign_analytics.py
```

Найди хэндлер просмотра завершённой кампании.
Добавь в конец сообщения блок метрик и кнопку «📄 Скачать PDF»:

```python
# В хэндлере показа завершённой кампании добавить:
# metrics = await analytics_service.calculate_campaign_metrics(campaign_id)
# metrics_text = (
#     f"\n📊 <b>Итоговые метрики:</b>\n"
#     f"👁 Просмотры: {metrics.total_views:,}\n"
#     f"💰 CPM: {metrics.cpm:.0f} ₽\n"
#     f"🖱 CTR: {metrics.ctr*100:.2f}%\n"
#     f"✅ Размещено: {metrics.success_rate*100:.0f}%\n"
# )

# Кнопка PDF:
# InlineKeyboardButton(text="📄 Скачать отчёт PDF", callback_data=f"download_pdf:{campaign_id}")


@router.callback_query(F.data.startswith("download_pdf:"))
async def send_pdf_report(callback: CallbackQuery) -> None:
    """Сгенерировать и отправить PDF-отчёт пользователю."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    campaign_id = int((callback.data or "").split(":")[1])

    await callback.answer("Генерирую отчёт...")

    try:
        # ⚠️ АДАПТИРУЙ: получи analytics_service
        # pdf_bytes = await analytics_service.generate_campaign_pdf_report(campaign_id)
        # from aiogram.types import BufferedInputFile
        # await callback.message.answer_document(
        #     document=BufferedInputFile(pdf_bytes, filename=f"report_{campaign_id}.pdf"),
        #     caption="📄 Отчёт по кампании",
        # )
        pass
    except Exception as e:
        logger.error(f"PDF generation failed for campaign {campaign_id}: {e}")
        await callback.answer("Ошибка генерации PDF. Попробуйте позже.", show_alert=True)
```

### Шаг 2.5.4 — Unit тесты метрик

```python
# tests/unit/test_analytics_metrics.py
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch


class TestCampaignMetrics:

    @pytest.mark.asyncio
    async def test_cpm_calculation(self):
        """CPM = cost / views * 1000."""
        # cost=1000, views=5000 → CPM = 200
        # ⚠️ АДАПТИРУЙ под реальный метод calculate_campaign_metrics с mock данными
        cost = Decimal("1000")
        views = 5000
        cpm = cost / views * 1000
        assert cpm == Decimal("200")

    @pytest.mark.asyncio
    async def test_ctr_calculation(self):
        """CTR = clicks / views."""
        clicks, views = 50, 5000
        ctr = clicks / views
        assert abs(ctr - 0.01) < 0.0001  # 1%

    @pytest.mark.asyncio
    async def test_zero_views_returns_zero_cpm(self):
        """При 0 просмотрах CPM = 0, нет деления на ноль."""
        views = 0
        cpm = Decimal("1000") / views * 1000 if views > 0 else Decimal("0")
        assert cpm == Decimal("0")

    def test_pdf_returns_bytes(self):
        """generate_campaign_pdf_report возвращает непустые байты."""
        # ⚠️ Запусти через asyncio.run или pytest-asyncio
        # с mock данными кампании
        pass
```

```powershell
poetry run pytest tests/unit/test_analytics_metrics.py -v
```

### Проверка

```powershell
poetry run ruff check src/core/services/analytics_service.py \
  src/bot/handlers/campaign_analytics.py
poetry run mypy src/core/services/analytics_service.py \
  src/bot/handlers/campaign_analytics.py --ignore-missing-imports
```

### Коммит 2.5

```powershell
git add src/core/services/analytics_service.py \
        src/bot/handlers/campaign_analytics.py \
        tests/unit/test_analytics_metrics.py
git commit -m "feat(analytics): add CPM/CTR/ROI calculations and PDF campaign report"
```

---

## ЗАДАЧА 2.6: Умный выбор времени публикации

### Шаг 2.6.1 — Найди Telethon клиент

```powershell
# Как инициализируется Telethon в проекте
grep -rn "TelegramClient\|client\s*=\|get_entity\|iter_messages" \
  src/ --include="*.py" | grep -v "test\|#" | head -10

# Прочитай parser.py — там используется Telethon
cat src/utils/telegram/parser.py | head -80
```

Зафикси: как получить Telethon клиент, как вызывать `iter_messages`.

### Шаг 2.6.2 — Создай TimingService

**Файл:** `src/core/services/timing_service.py`

```python
"""
Сервис умного выбора времени публикации.

Анализирует историю постов канала через Telethon и определяет
пиковые часы активности аудитории.

Уникальный дифференциатор платформы — отсутствует у прямых конкурентов.
"""
import logging
from datetime import datetime, timezone, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# Анализируем последние N постов канала
POSTS_TO_ANALYZE = 50

# Часовой пояс для анализа (по умолчанию Москва)
DEFAULT_TIMEZONE_OFFSET = 3  # UTC+3


class TimingService:

    # ⚠️ АДАПТИРУЙ: получи Telethon клиент так же как в parser.py

    async def suggest_optimal_time(
        self,
        channel_username: str,
        target_date: datetime | None = None,
    ) -> datetime:
        """
        Предложить оптимальное время публикации для конкретного канала.

        Алгоритм:
        1. Читаем последние POSTS_TO_ANALYZE постов через Telethon
        2. Для каждого поста смотрим час публикации И часы с наибольшим ростом просмотров
        3. Находим час с максимальной средней активностью
        4. Возвращаем ближайший подходящий datetime (завтра или позже)

        Returns:
            datetime в UTC с оптимальным временем публикации
        """
        try:
            optimal_hour = await self._analyze_channel_activity(channel_username)
        except Exception as e:
            logger.warning(
                f"Cannot analyze channel @{channel_username}: {e}. "
                "Returning default time (10:00 Moscow)."
            )
            optimal_hour = 10  # дефолт если анализ недоступен

        return self._next_occurrence_of_hour(optimal_hour, target_date)

    async def _analyze_channel_activity(self, channel_username: str) -> int:
        """
        Проанализировать активность канала и вернуть оптимальный час (0-23, UTC).

        Логика: для каждого часа суток считаем среднее количество просмотров
        у постов опубликованных в этот час. Возвращаем час с максимальным средним.
        """
        # ⚠️ АДАПТИРУЙ под реальный Telethon клиент из parser.py
        # async for message in client.iter_messages(channel_username, limit=POSTS_TO_ANALYZE):
        #     if message.date and message.views:
        #         hour = message.date.astimezone(timezone.utc).hour
        #         views_by_hour[hour].append(message.views)

        # Временная заглушка — вернуть 10 (утро, хороший дефолт)
        # ⚠️ Замени на реальный анализ
        views_by_hour: dict[int, list[int]] = defaultdict(list)

        if not views_by_hour:
            return 10  # дефолт

        avg_by_hour = {
            hour: sum(views) / len(views)
            for hour, views in views_by_hour.items()
        }
        return max(avg_by_hour, key=avg_by_hour.get)  # type: ignore[arg-type]

    def _next_occurrence_of_hour(
        self,
        hour_utc: int,
        target_date: datetime | None = None,
    ) -> datetime:
        """
        Найти ближайший datetime с данным часом (не раньше чем через 2 часа).
        """
        now = datetime.now(timezone.utc)
        base = target_date or now

        candidate = base.replace(hour=hour_utc, minute=0, second=0, microsecond=0)

        # Если время уже прошло или слишком близко — сдвинуть на завтра
        if candidate <= now + timedelta(hours=2):
            candidate += timedelta(days=1)

        return candidate
```

### Шаг 2.6.3 — Добавь кнопку «Оптимальное время» в мастер кампании

```powershell
# Найди шаг расписания в мастере
grep -n "schedule\|расписан\|scheduled_at\|Расписание" \
  src/bot/handlers/campaigns.py | head -10
```

Найди клавиатуру шага расписания. Добавь кнопку:
```python
InlineKeyboardButton(
    text="🎯 Оптимальное время",
    callback_data="schedule_optimal",
)
```

Добавь хэндлер:
```python
@router.callback_query(F.data == "schedule_optimal")
async def schedule_optimal_time(callback: CallbackQuery, state: FSMContext) -> None:
    """Определить и установить оптимальное время публикации."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    await callback.answer("Анализирую активность канала...")

    data = await state.get_data()
    # ⚠️ Получи username канала из FSM-данных
    # selected_channels = data.get("selected_channels", [])

    try:
        # ⚠️ АДАПТИРУЙ: получи timing_service
        # optimal_dt = await timing_service.suggest_optimal_time(channel_username)
        # await state.update_data(scheduled_at=optimal_dt.isoformat())

        await safe_callback_edit(
            callback.message,
            f"🎯 <b>Оптимальное время установлено</b>\n\n"
            f"Публикация запланирована на: <b>завтра 10:00 МСК</b>\n\n"  # ⚠️ подставь реальное время
            f"Это время когда аудитория канала наиболее активна.",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Optimal time calculation failed: {e}")
        await callback.answer("Не удалось проанализировать канал. Выберите время вручную.", show_alert=True)
```

### Шаг 2.6.4 — Unit тест TimingService

```python
# tests/unit/test_timing_service.py
import pytest
from datetime import datetime, timezone, timedelta
from src.core.services.timing_service import TimingService


class TestTimingService:

    def setup_method(self):
        self.service = TimingService()

    def test_next_occurrence_future_today(self):
        """Час в будущем сегодня возвращает сегодня."""
        future_hour = (datetime.now(timezone.utc) + timedelta(hours=5)).hour
        result = self.service._next_occurrence_of_hour(future_hour)
        assert result > datetime.now(timezone.utc)
        assert result.hour == future_hour

    def test_next_occurrence_past_hour_returns_tomorrow(self):
        """Час в прошлом возвращает тот же час завтра."""
        past_hour = (datetime.now(timezone.utc) - timedelta(hours=5)).hour
        result = self.service._next_occurrence_of_hour(past_hour)
        tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
        assert result.date() == tomorrow.date()

    def test_next_occurrence_too_close_returns_tomorrow(self):
        """Час менее чем через 2 часа → завтра."""
        soon_hour = (datetime.now(timezone.utc) + timedelta(hours=1)).hour
        result = self.service._next_occurrence_of_hour(soon_hour)
        assert result > datetime.now(timezone.utc) + timedelta(hours=2)
```

```powershell
poetry run pytest tests/unit/test_timing_service.py -v
```

### Проверка

```powershell
poetry run ruff check src/core/services/timing_service.py \
  src/bot/handlers/campaigns.py
poetry run mypy src/core/services/timing_service.py --ignore-missing-imports
```

### Коммит 2.6

```powershell
git add src/core/services/timing_service.py \
        src/bot/handlers/campaigns.py \
        tests/unit/test_timing_service.py
git commit -m "feat(timing): add optimal publication time suggestion via channel analysis"
```

---

## ФИНАЛЬНАЯ ПРОВЕРКА И ОТПРАВКА

```powershell
# 1. Линтинг
poetry run ruff check src/ tests/
echo "Ruff exit: $?"

# 2. Типизация
poetry run mypy src/ --ignore-missing-imports 2>&1 | tail -5

# 3. Миграции
poetry run alembic current
poetry run alembic check

# 4. Тесты
poetry run pytest tests/unit/ -v --tb=short 2>&1 | tail -20

# 5. Ровно 6 коммитов
git log --oneline sprint/2 ^develop
```

Ожидаемые коммиты:
```
feat(timing): add optimal publication time suggestion via channel analysis
feat(analytics): add CPM/CTR/ROI calculations and PDF campaign report
feat(analytics): add CTR tracking with short links and redirect endpoint
feat(campaign): add post preview step in campaign wizard
feat(review): add review_service and post-campaign review request flow
feat(review): add Review model and migration
```

```powershell
git push origin sprint/2
```

---

## Итоговый отчёт

```
═══════════════════════════════════════════════
 ОТЧЁТ: СПРИНТ 2 — Маркетплейс и аналитика
═══════════════════════════════════════════════

Ветка: sprint/2
Предыдущий спринт смержен: [✅/❌]

2.1 — Review модель: [✅ мигрирована / ❌]
  UniqueConstraint (reviewer_id, placement_id): [✅/❌]

2.2 — ReviewService:
  submit_review: [✅ реальный / ⚠️ заглушка]
  get_channel_rating: [✅ реальный / ⚠️ заглушка]
  check_duplicate_fraud: [✅ реальный / ⚠️ заглушка]
  FSM флоу отзыва: [N шагов из 5]
  Celery задача запроса отзыва: [✅/❌]

2.3 — Предпросмотр:
  Шаг добавлен: [✅/❌]
  С медиа и без: [✅ оба варианта / ⚠️ только текст]

2.4 — CTR трекинг:
  Поля в модели размещения: [✅/❌]
  Сервис генерации кодов: [✅/❌]
  FastAPI редирект /r/{code}: [✅/❌]
  Unit тесты кодов: [N passed]

2.5 — CPM/CTR/ROI:
  calculate_campaign_metrics: [✅ реальный / ⚠️ заглушки]
  PDF-отчёт возвращает bytes: [✅/❌]
  reportlab установлен: [✅/❌]

2.6 — Оптимальное время:
  _analyze_channel_activity: [✅ Telethon / ⚠️ заглушка — почему]
  Кнопка в мастере: [✅/❌]
  Unit тесты _next_occurrence: [N passed]

Ruff: [✅/❌]  Mypy: [✅/❌]
Тесты: [N passed, N failed]
Коммитов: [N]/6

Заглушки → Спринт 3: [список]
PR: sprint/2 → develop
```
