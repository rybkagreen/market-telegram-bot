# Qwen Code Промт: Спринт 3 — B2B-маркетплейс и рейтинговая система

## Обязательная ориентация перед стартом

```powershell
cd ~/python-projects/market-telegram-bot
source .venv/Scripts/activate

# 1. Прочитай дорожную карту целиком
cat ROADMAP.md

# 2. Убедись что Спринт 2 завершён и смержен в develop
git log --oneline develop | head -20
# Должны быть все коммиты sprint/2:
# feat(timing): add optimal publication time suggestion via channel analysis
# feat(analytics): add CPM/CTR/ROI calculations and PDF campaign report
# feat(analytics): add CTR tracking with short links and redirect endpoint
# feat(campaign): add post preview step in campaign wizard
# feat(review): add review_service and post-campaign review request flow
# feat(review): add Review model and migration
```

После чтения дорожной карты зафикси:
- Что Спринт 3 добавляет поверх Спринта 2 (B2B-пакеты, ChannelRating, детектор накрутки)
- Как `Review.score_compliance` из Спринта 2 используется в `reliability_score` рейтинга
- Что из Спринта 3 нужно Спринту 4 (уровни геймификации используют `total_spent` которое пересчитывается рядом с выплатами)

---

## Контекст Спринта 3

### Что добавляет этот спринт

Закрывает **B2B-сегмент** (агентства и крупные рекламодатели) и строит **доверие к каталогу**
через верифицированные рейтинги и детектор накрутки — прямой ответ на риск упомянутый
в конкурентном анализе PRD.

Детектор накрутки — маркетинговый аргумент: «наш каталог верифицирован, фейков нет».

### Что уже есть после Спринта 2

| Сущность | Что доступно |
|----------|-------------|
| `Review` | score_compliance, score_audience, score_speed, score_material и др. |
| `review_service` | `get_channel_rating(channel_id)` — средняя оценка для каталога |
| `TelegramChat` | `bot_is_admin`, `is_accepting_ads`, `rating`, `member_count`, `last_avg_views` |
| `link_tracking_service` | CTR данные для расчёта ER косвенно |
| Каталог каналов | `channels_db.py` с базовыми фильтрами |

### Состав Спринта 3

| # | Задача | Файлы |
|---|--------|-------|
| 3.1 | Модели B2BPackage + ChannelRating + миграции | `models/b2b_package.py`, `models/channel_rating.py` |
| 3.2 | RatingService + формула из PRD §7.1 | `services/rating_service.py` |
| 3.3 | Детектор накрутки | `services/rating_service.py` |
| 3.4 | Celery задачи рейтингов | `tasks/rating_tasks.py` |
| 3.5 | /b2b хэндлер + B2BPackageService | `handlers/b2b.py`, `services/b2b_package_service.py` |
| 3.6 | Медиакит PDF + расширение фильтров каталога | `services/b2b_package_service.py`, `handlers/channels_db.py` |

---

## ГЛОБАЛЬНЫЕ ПРАВИЛА

1. **Читай файл целиком** перед любым изменением
2. **Формула рейтинга строго по PRD §7.1** — не изобретай свою
3. **Детектор накрутки — только флаг**, не бан: устанавливает `fraud_flag=True`, не удаляет канал
4. **Один коммит на задачу**, имена строго по плану

```powershell
# После каждой задачи:
poetry run ruff check src/
poetry run mypy src/ --ignore-missing-imports 2>&1 | tail -3
```

---

## ПОДГОТОВКА

```powershell
git checkout develop && git pull origin develop
git checkout -b sprint/3
git log --oneline -10
```

### Разведка структуры

```powershell
# Текущая модель TelegramChat — откуда берём данные для рейтинга
grep -n "member_count\|last_avg_views\|rating\|er\|engagement\|growth" \
  $(grep -rl "class TelegramChat" src/ --include="*.py")

# Текущий каталог — что расширяем
cat src/bot/handlers/channels_db.py

# Как добавлены B2B-нишки в topic_classifier
grep -rn "TOPIC\|category\|niche\|it\|crypto\|business" \
  src/api/constants/ src/utils/telegram/ --include="*.py" | head -15

# Telethon для медиакита — примеры постов
grep -rn "iter_messages\|get_messages" src/utils/telegram/parser.py | head -5
```

---

## ЗАДАЧА 3.1: Модели B2BPackage и ChannelRating

### Шаг 3.1.1 — Изучи образцовые модели

```powershell
cat src/db/models/payout.py   # стиль Mapped + enum
cat src/db/models/review.py   # пример UniqueConstraint
```

### Шаг 3.1.2 — Создай B2BPackage

**Файл:** `src/db/models/b2b_package.py`

```python
"""
Пакетные предложения B2B-маркетплейса.
6 ниш по PRD §5.2: it, business, realestate, crypto, marketing, finance.
Пакет = набор каналов с гарантированным охватом и скидкой 10-25%.
"""
from enum import Enum as PyEnum

class B2BNiche(str, PyEnum):
    IT = "it"
    BUSINESS = "business"
    REALESTATE = "realestate"
    CRYPTO = "crypto"
    MARKETING = "marketing"
    FINANCE = "finance"


class B2BPackage(Base):
    __tablename__ = "b2b_packages"

    # id, created_at — по образцу
    name: ...            # String(200) — название пакета
    niche: ...           # String(30) — B2BNiche enum
    description: ...     # Text — описание целевой аудитории
    channels_count: ...  # Integer — количество каналов в пакете
    guaranteed_reach: ...# Integer — гарантированный охват (просмотры/24ч)
    min_er: ...          # Float — минимальный ER по всем каналам пакета
    price: ...           # Numeric(12, 2) — цена пакета
    discount_pct: ...    # SmallInteger — скидка % (10-25)
    is_active: ...       # Boolean, default=True
    channel_ids: ...     # JSONB — список Integer ID каналов в пакете
                         # from sqlalchemy.dialects.postgresql import JSONB
```

### Шаг 3.1.3 — Создай ChannelRating

**Файл:** `src/db/models/channel_rating.py`

```python
"""
Ежедневный снимок рейтинга канала.
Каждый день создаётся новая запись — история за 6 месяцев.
Формула: PRD §7.1 (6 компонентов с весами).
"""
from datetime import date as date_type

class ChannelRating(Base):
    __tablename__ = "channel_ratings"

    # id — по образцу
    channel_id: ...      # BigInteger FK → telegram_chats.id
    date: ...            # Date — дата расчёта (не DateTime)

    # Исходные метрики для расчёта
    subscribers: ...     # Integer
    avg_views: ...       # Integer — средние просмотры
    er: ...              # Float — engagement rate

    # Компоненты рейтинга (каждый 0-100)
    reach_score: ...     # Float — вес 30%
    er_score: ...        # Float — вес 25%
    growth_score: ...    # Float — вес 15%
    frequency_score: ... # Float — вес 10%
    reliability_score: ...# Float — вес 15% (из review_service.get_channel_rating)
    age_score: ...       # Float — вес 5%

    total_score: ...     # Float — итог 0-100
    rank_in_topic: ...   # Integer, nullable — позиция среди каналов той же тематики
    fraud_flag: ...      # Boolean, default=False

    # ⚠️ Уникальный индекс: (channel_id, date) — один снимок в день
    # __table_args__ = (UniqueConstraint("channel_id", "date"),)
```

### Шаг 3.1.4 — Миграции

```powershell
# Добавь оба импорта в alembic/env.py
poetry run alembic revision --autogenerate -m "add_b2b_package_model"
poetry run alembic upgrade head

poetry run alembic revision --autogenerate -m "add_channel_rating_model"
poetry run alembic upgrade head

poetry run alembic current  # → head
```

Прочитай оба сгенерированных файла — убедись что JSONB для `channel_ids` корректен.
PostgreSQL JSONB в Alembic:
```python
from sqlalchemy.dialects.postgresql import JSONB
sa.Column("channel_ids", JSONB, nullable=False, server_default="[]")
```

### Проверка

```powershell
poetry run ruff check src/db/models/b2b_package.py src/db/models/channel_rating.py
poetry run mypy src/db/models/b2b_package.py src/db/models/channel_rating.py \
  --ignore-missing-imports
```

### Коммит 3.1

```powershell
git add src/db/models/b2b_package.py src/db/models/channel_rating.py \
        alembic/versions/ alembic/env.py
git commit -m "feat(b2b): add B2BPackage and ChannelRating models with migrations"
```

---

## ЗАДАЧА 3.2: RatingService — формула рейтинга

### Шаг 3.2.1 — Разбери формулу из PRD §7.1

Строго по документу:

| Компонент | Вес | Логика |
|-----------|-----|--------|
| reach_score | 30% | avg_views / subscribers → нормализовать в 0-100 |
| er_score | 25% | reactions+comments+reposts / views → нормализовать |
| growth_score | 15% | органический прирост подписчиков за 30 дней |
| frequency_score | 10% | оптимум 1-3 поста/день; отклонение снижает балл |
| reliability_score | 15% | доля успешных размещений (из `review_service`) |
| age_score | 5% | каналы > 6 мес получают +5 |

**Итог: total_score = сумма (компонент × вес)**

### Шаг 3.2.2 — Создай RatingService

**Файл:** `src/core/services/rating_service.py`

```python
"""
Сервис расчёта рейтинга каналов.

Формула: PRD §7.1 — 6 компонентов с весами.
Рейтинг пересчитывается ежедневно через Celery Beat.
"""
import logging
from datetime import date, datetime, timezone, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Веса компонентов рейтинга (сумма = 1.0)
WEIGHTS = {
    "reach":       0.30,
    "er":          0.25,
    "growth":      0.15,
    "frequency":   0.10,
    "reliability": 0.15,
    "age":         0.05,
}

# Пороги нормализации
REACH_OPTIMAL = 0.30       # 30% просмотров от подписчиков → 100 баллов
ER_OPTIMAL = 0.05          # 5% ER → 100 баллов
GROWTH_OPTIMAL = 0.10      # 10% прирост за 30 дней → 100 баллов
FREQUENCY_OPTIMAL = (1, 3) # 1-3 поста в день → 100 баллов
AGE_BONUS_MONTHS = 6       # каналы старше 6 мес → age_score = 100


@dataclass
class FraudReport:
    channel_id: int
    fraud_flag: bool
    reasons: list[str]


class RatingService:

    # ⚠️ АДАПТИРУЙ инжекцию зависимостей под стиль проекта

    def _normalize(self, value: float, optimal: float) -> float:
        """Нормализовать значение в 0-100. При value >= optimal → 100."""
        if optimal <= 0:
            return 0.0
        return min(100.0, (value / optimal) * 100)

    def _calc_reach_score(self, avg_views: int, subscribers: int) -> float:
        """Охват аудитории: avg_views / subscribers → 0-100."""
        if subscribers <= 0:
            return 0.0
        ratio = avg_views / subscribers
        return self._normalize(ratio, REACH_OPTIMAL)

    def _calc_er_score(self, er: float) -> float:
        """ER → 0-100."""
        return self._normalize(er, ER_OPTIMAL)

    def _calc_growth_score(self, growth_rate_30d: float) -> float:
        """Прирост подписчиков за 30 дней (0.1 = 10%) → 0-100."""
        if growth_rate_30d < 0:
            return 0.0  # отток = 0 баллов
        return self._normalize(growth_rate_30d, GROWTH_OPTIMAL)

    def _calc_frequency_score(self, posts_per_day: float) -> float:
        """
        Частота публикаций → 0-100.
        Оптимум 1-3 поста/день. Слишком редко или слишком часто — штраф.
        """
        low, high = FREQUENCY_OPTIMAL
        if low <= posts_per_day <= high:
            return 100.0
        elif posts_per_day < low:
            # Менее 1 поста в день: 0.5/день → 50 баллов
            return self._normalize(posts_per_day, low)
        else:
            # Более 3 постов в день: спам-штраф
            excess = posts_per_day - high
            penalty = min(100.0, excess * 10)
            return max(0.0, 100.0 - penalty)

    def _calc_age_score(self, created_at: datetime) -> float:
        """Возраст канала: > 6 мес → 100 баллов, иначе пропорционально."""
        age_months = (datetime.now(timezone.utc) - created_at).days / 30
        return self._normalize(age_months, AGE_BONUS_MONTHS)

    async def calculate_channel_score(
        self,
        channel_id: int,
        calc_date: date | None = None,
    ) -> "ChannelRating":
        """
        Рассчитать рейтинг канала на указанную дату.
        Сохраняет запись ChannelRating в БД (upsert по channel_id + date).

        Returns: созданная/обновлённая запись ChannelRating
        """
        if calc_date is None:
            calc_date = date.today()

        # ⚠️ АДАПТИРУЙ: получи данные канала из БД
        # channel = await chat_repo.get_by_id(channel_id)
        # if channel is None:
        #     raise ValueError(f"Channel {channel_id} not found")

        # Получи reliability_score из отзывов (Спринт 2)
        # review_rating = await review_service.get_channel_rating(channel_id)
        # reliability_score = review_rating * 20  # 5 звёзд = 100 баллов

        # Временные заглушки — замени на реальные данные:
        avg_views = 0       # channel.last_avg_views
        subscribers = 1     # channel.member_count
        er = 0.0            # channel.er (если есть) или 0
        growth_30d = 0.0    # (current - 30d_ago) / 30d_ago
        posts_per_day = 1.0 # из истории постов
        reliability_score = 50.0  # из review_service
        created_at = datetime.now(timezone.utc)  # channel.created_at

        # Рассчитать компоненты
        reach_score = self._calc_reach_score(avg_views, subscribers)
        er_score = self._calc_er_score(er)
        growth_score = self._calc_growth_score(growth_30d)
        frequency_score = self._calc_frequency_score(posts_per_day)
        age_score = self._calc_age_score(created_at)

        # Итоговый балл
        total_score = (
            reach_score * WEIGHTS["reach"] +
            er_score * WEIGHTS["er"] +
            growth_score * WEIGHTS["growth"] +
            frequency_score * WEIGHTS["frequency"] +
            reliability_score * WEIGHTS["reliability"] +
            age_score * WEIGHTS["age"]
        )

        # ⚠️ АДАПТИРУЙ: сохрани ChannelRating через репозиторий
        # rating = ChannelRating(
        #     channel_id=channel_id,
        #     date=calc_date,
        #     subscribers=subscribers,
        #     avg_views=avg_views,
        #     er=er,
        #     reach_score=reach_score,
        #     er_score=er_score,
        #     growth_score=growth_score,
        #     frequency_score=frequency_score,
        #     reliability_score=reliability_score,
        #     age_score=age_score,
        #     total_score=round(total_score, 2),
        #     fraud_flag=False,
        # )
        # await session.merge(rating)  # upsert
        # return rating
        pass  # ← замени

    async def recalculate_all_ratings(self) -> dict:
        """
        Пересчитать рейтинги всех активных каналов.
        Вызывается Celery задачей ежедневно в 04:00 UTC.
        """
        # ⚠️ АДАПТИРУЙ: получи все каналы с bot_is_admin=True
        # channels = await chat_repo.get_all_active()
        success, failed = 0, 0
        # for channel in channels:
        #     try:
        #         await self.calculate_channel_score(channel.id)
        #         success += 1
        #     except Exception as e:
        #         logger.error(f"Rating calc failed for {channel.id}: {e}")
        #         failed += 1
        return {"success": success, "failed": failed}

    async def get_top_channels(self, topic: str, limit: int = 10) -> list:
        """
        Топ каналов по тематике — по total_score последней ChannelRating.
        Исключает каналы с fraud_flag=True.
        """
        # ⚠️ АДАПТИРУЙ: JOIN telegram_chats с channel_ratings
        return []

    async def get_reliability_stars(self, channel_id: int) -> float:
        """
        Рейтинг надёжности от 1 до 5 звёзд (PRD §7.2).
        Основан на поведении владельца: своевременность, отмены, жалобы.
        Использует review_service.get_channel_rating() как базу.
        """
        # 5-балльная шкала отзывов → 1-5 звёзд напрямую
        # ⚠️ АДАПТИРУЙ
        raw_rating = 0.0  # await review_service.get_channel_rating(channel_id)
        return max(1.0, min(5.0, raw_rating))
```

### Шаг 3.2.3 — Unit тесты формулы

**Файл:** `tests/unit/test_rating_service.py`

```python
"""Unit тесты RatingService — строгая проверка формулы из PRD §7.1."""
import pytest
from datetime import datetime, timezone, timedelta
from src.core.services.rating_service import RatingService, WEIGHTS


class TestRatingFormula:

    def setup_method(self):
        self.svc = RatingService()  # ⚠️ адаптируй

    # ── Компонент Reach ──────────────────────────────────────────

    def test_reach_score_optimal(self):
        """30% просмотров от подписчиков → 100 баллов."""
        score = self.svc._calc_reach_score(avg_views=300, subscribers=1000)
        assert score == 100.0

    def test_reach_score_half_optimal(self):
        """15% просмотров → ~50 баллов."""
        score = self.svc._calc_reach_score(avg_views=150, subscribers=1000)
        assert abs(score - 50.0) < 1.0

    def test_reach_score_zero_subscribers(self):
        """0 подписчиков → 0 баллов, нет деления на ноль."""
        score = self.svc._calc_reach_score(avg_views=100, subscribers=0)
        assert score == 0.0

    # ── Компонент Frequency ───────────────────────────────────────

    def test_frequency_score_optimal(self):
        """2 поста в день (в оптимуме 1-3) → 100 баллов."""
        score = self.svc._calc_frequency_score(posts_per_day=2.0)
        assert score == 100.0

    def test_frequency_score_too_rare(self):
        """0.2 поста в день → меньше 100."""
        score = self.svc._calc_frequency_score(posts_per_day=0.2)
        assert score < 100.0
        assert score >= 0.0

    def test_frequency_score_spam(self):
        """20 постов в день → сильный штраф."""
        score = self.svc._calc_frequency_score(posts_per_day=20.0)
        assert score < 30.0

    # ── Компонент Age ─────────────────────────────────────────────

    def test_age_score_mature_channel(self):
        """Канал старше 6 месяцев → 100 баллов."""
        old_date = datetime.now(timezone.utc) - timedelta(days=200)
        score = self.svc._calc_age_score(old_date)
        assert score == 100.0

    def test_age_score_new_channel(self):
        """Новый канал (1 месяц) → меньше 100."""
        new_date = datetime.now(timezone.utc) - timedelta(days=30)
        score = self.svc._calc_age_score(new_date)
        assert score < 100.0
        assert score >= 0.0

    # ── Веса суммируются в 1.0 ────────────────────────────────────

    def test_weights_sum_to_one(self):
        """Сумма всех весов = 1.0 (проверка формулы PRD §7.1)."""
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    # ── Итоговый балл ─────────────────────────────────────────────

    def test_total_score_range(self):
        """total_score всегда в диапазоне 0-100."""
        # Идеальный канал
        scores = {
            "reach": 100, "er": 100, "growth": 100,
            "frequency": 100, "reliability": 100, "age": 100,
        }
        total = sum(scores[k] * WEIGHTS[k] for k in scores)
        assert 0.0 <= total <= 100.0

    def test_total_score_worst_channel(self):
        """Худший канал → 0 баллов."""
        scores = {k: 0 for k in WEIGHTS}
        total = sum(scores[k] * WEIGHTS[k] for k in scores)
        assert total == 0.0
```

```powershell
poetry run pytest tests/unit/test_rating_service.py -v
# Ожидаем: все тесты PASS
```

### Коммит 3.2

```powershell
git add src/core/services/rating_service.py tests/unit/test_rating_service.py
git commit -m "feat(rating): add rating_service with scoring formula from PRD §7.1"
```

---

## ЗАДАЧА 3.3: Детектор накрутки

### Шаг 3.3.1 — Добавь метод detect_fraud в RatingService

```python
async def detect_fraud(self, channel_id: int) -> FraudReport:
    """
    Детектор накрутки (PRD §7.3).
    Три признака аномалии — при ANY из них fraud_flag=True.

    Признак 1: прирост подписчиков > 50% за 7 дней
    Признак 2: ER < 0.5% при > 10k подписчиков
    Признак 3: отток > 30% в течение 14 дней после роста

    При fraud_flag=True:
    - channel.fraud_flag = True в channel_ratings
    - Канал перемещается в конец каталога (низкий total_score)
    - Уведомление администратору
    """
    reasons: list[str] = []

    # ⚠️ АДАПТИРУЙ: получи данные канала и историю подписчиков
    # channel = await chat_repo.get_by_id(channel_id)
    # rating_7d_ago = await channel_rating_repo.get_by_date(
    #     channel_id, date.today() - timedelta(days=7)
    # )
    # rating_current = await channel_rating_repo.get_latest(channel_id)

    # Признак 1: резкий прирост
    # if rating_7d_ago and rating_current:
    #     if rating_7d_ago.subscribers > 0:
    #         growth = (rating_current.subscribers - rating_7d_ago.subscribers) / rating_7d_ago.subscribers
    #         if growth > 0.5:
    #             reasons.append(f"Резкий прирост {growth*100:.0f}% за 7 дней")

    # Признак 2: аномально низкий ER при большой аудитории
    # if channel.member_count > 10_000 and channel.er < 0.005:
    #     reasons.append(f"ER {channel.er*100:.2f}% при {channel.member_count} подписчиках")

    # Признак 3: отток после роста
    # ... (реализуй по PRD §7.3)

    fraud_flag = len(reasons) > 0

    if fraud_flag:
        # ⚠️ Обнови fraud_flag в последней ChannelRating
        # await channel_rating_repo.set_fraud_flag(channel_id, True)
        #
        # Уведомить администратора
        # from src.tasks.notification_tasks import notify_admin_fraud_detected
        # notify_admin_fraud_detected.delay(channel_id, reasons)
        logger.warning(f"Fraud detected for channel {channel_id}: {reasons}")

    return FraudReport(
        channel_id=channel_id,
        fraud_flag=fraud_flag,
        reasons=reasons,
    )
```

### Шаг 3.3.2 — Добавь уведомление администратору

В `src/tasks/notification_tasks.py`:

```python
@celery_app.task(name="notifications:notify_admin_fraud_detected")
def notify_admin_fraud_detected(channel_id: int, reasons: list[str]) -> None:
    """Уведомить администратора о подозрительной активности канала."""
    # ⚠️ АДАПТИРУЙ: получи admin_telegram_id из settings
    # Отправь сообщение с деталями: channel_id, reasons, ссылка на ручную проверку
    pass
```

### Шаг 3.3.3 — Unit тест детектора

```python
# Добавить в tests/unit/test_rating_service.py

class TestFraudDetector:

    def setup_method(self):
        self.svc = RatingService()

    @pytest.mark.asyncio
    async def test_no_fraud_for_normal_channel(self):
        """Обычный канал без аномалий → fraud_flag=False."""
        # ⚠️ Создай mock с нормальными данными: ER=3%, growth=5%, отток нет
        # report = await self.svc.detect_fraud(channel_id=1)
        # assert report.fraud_flag == False
        # assert len(report.reasons) == 0
        pass

    @pytest.mark.asyncio
    async def test_rapid_growth_triggers_fraud(self):
        """Прирост > 50% за 7 дней → fraud_flag=True."""
        # ⚠️ Mock: subscribers 7 дней назад = 1000, сейчас = 2000 (100% рост)
        # report = await self.svc.detect_fraud(channel_id=2)
        # assert report.fraud_flag == True
        # assert any("прирост" in r.lower() for r in report.reasons)
        pass

    @pytest.mark.asyncio
    async def test_low_er_triggers_fraud(self):
        """ER < 0.5% при > 10k подписчиков → fraud_flag=True."""
        # ⚠️ Mock: member_count=50000, er=0.001
        pass
```

### Коммит 3.3

```powershell
git add src/core/services/rating_service.py \
        src/tasks/notification_tasks.py \
        tests/unit/test_rating_service.py
git commit -m "feat(rating): add fraud detector with three anomaly signals"
```

---

## ЗАДАЧА 3.4: Celery задачи рейтингов

**Файл:** `src/tasks/rating_tasks.py` (создать)

```python
"""
Celery задачи для рейтинговой системы.

Расписание:
- recalculate_ratings_daily: каждый день 04:00 UTC
- update_weekly_toplists: каждый понедельник 05:00 UTC
- run_fraud_detection: каждый день 06:00 UTC (после пересчёта)
"""
import logging
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="rating:recalculate_ratings_daily", bind=True, max_retries=3)
def recalculate_ratings_daily(self) -> dict:
    """
    Ежедневный пересчёт рейтингов всех активных каналов.
    Запускается в 04:00 UTC — после ночного обновления метрик парсером.
    """
    # ⚠️ АДАПТИРУЙ: создай rating_service и вызови recalculate_all_ratings()
    # Паттерн из mailing_tasks.py или другой задачи с БД
    try:
        # result = rating_service.recalculate_all_ratings_sync()
        # logger.info(f"Ratings recalculated: {result}")
        # return result
        return {"status": "ok", "success": 0, "failed": 0}
    except Exception as exc:
        logger.error(f"recalculate_ratings_daily failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(name="rating:update_weekly_toplists")
def update_weekly_toplists() -> dict:
    """
    Еженедельное обновление топ-листов по тематикам.
    Для каждой тематики — топ-10 по total_score.
    Результаты кэшируются в Redis для быстрой отдачи в каталоге.
    """
    # ⚠️ АДАПТИРУЙ: для каждой тематики вызови rating_service.get_top_channels()
    # Сохрани результат в Redis: SET "toplists:{topic}" json(channels) EX 7*24*3600
    return {"status": "ok", "topics_updated": 0}


@celery_app.task(name="rating:run_fraud_detection")
def run_fraud_detection() -> dict:
    """
    Ежедневный прогон детектора накрутки по всем активным каналам.
    Запускается в 06:00 UTC — после пересчёта рейтингов.
    """
    # ⚠️ АДАПТИРУЙ: получи все активные каналы, для каждого вызови detect_fraud()
    flagged_count = 0
    # for channel in active_channels:
    #     report = rating_service.detect_fraud_sync(channel.id)
    #     if report.fraud_flag:
    #         flagged_count += 1
    return {"status": "ok", "flagged": flagged_count}
```

Добавь в `src/tasks/celery_config.py`:

```python
# ⚠️ Найди beat_schedule в файле и добавь:
"recalculate-ratings-daily": {
    "task": "rating:recalculate_ratings_daily",
    "schedule": crontab(hour=4, minute=0),
},
"update-weekly-toplists": {
    "task": "rating:update_weekly_toplists",
    "schedule": crontab(day_of_week=1, hour=5, minute=0),
},
"run-fraud-detection": {
    "task": "rating:run_fraud_detection",
    "schedule": crontab(hour=6, minute=0),
},
```

### Проверка

```powershell
poetry run ruff check src/tasks/rating_tasks.py
poetry run mypy src/tasks/rating_tasks.py --ignore-missing-imports

# Убедись что задачи есть в beat_schedule
grep -A 3 "recalculate-ratings\|toplists\|fraud-detection" src/tasks/celery_config.py
```

### Коммит 3.4

```powershell
git add src/tasks/rating_tasks.py src/tasks/celery_config.py
git commit -m "feat(rating): add rating_tasks Celery jobs with beat schedule"
```

---

## ЗАДАЧА 3.5: /b2b хэндлер и B2BPackageService

### Шаг 3.5.1 — Создай B2BPackageService

**Файл:** `src/core/services/b2b_package_service.py`

```python
"""
Сервис B2B-маркетплейса.
Управление пакетными предложениями по нишам (PRD §5.2-5.3).
"""
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class B2BPackageService:

    # ⚠️ АДАПТИРУЙ инжекцию

    async def get_packages_by_niche(self, niche: str) -> list:
        """Получить активные пакеты для ниши, отсортированные по цене."""
        # ⚠️ SELECT * FROM b2b_packages WHERE niche=niche AND is_active=True ORDER BY price
        return []

    async def validate_package_channels(self, package_id: int) -> tuple[bool, list[int]]:
        """
        Проверить что все каналы пакета активны (bot_is_admin=True, is_accepting_ads=True).

        Returns:
            (is_valid, list_of_inactive_channel_ids)
        """
        # ⚠️ АДАПТИРУЙ: загрузи пакет → проверь каждый channel_id
        return True, []

    async def get_package_actual_reach(self, package_id: int) -> int:
        """Реальный суммарный охват пакета на текущий момент (сумма member_count)."""
        # ⚠️ АДАПТИРУЙ: SUM(member_count) для каналов в пакете
        return 0

    async def get_package_discount_value(self, package_id: int) -> Decimal:
        """Сколько рекламодатель экономит vs разовые размещения."""
        # ⚠️ Сумма price_per_post каналов - цена пакета
        return Decimal("0")
```

### Шаг 3.5.2 — Создай хэндлер /b2b

**Файл:** `src/bot/handlers/b2b.py`

```python
"""
Хэндлер B2B-маркетплейса.
Команда /b2b — просмотр ниш и пакетных предложений.
Спринт 3, задача 3.5.
"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, InaccessibleMessage,
)
from src.bot.utils.safe_callback import safe_callback_edit

logger = logging.getLogger(__name__)
router = Router(name="b2b")

# Описания ниш для UI (PRD §5.2)
NICHE_INFO = {
    "it": ("💻", "IT и разработка", "Разработчики, DevOps, AI/ML специалисты"),
    "business": ("💼", "Бизнес и стартапы", "Предприниматели, инвесторы, топ-менеджеры"),
    "realestate": ("🏠", "Недвижимость", "Покупатели, арендаторы, инвесторы"),
    "crypto": ("🔗", "Крипта и DeFi", "Трейдеры, долгосрочные инвесторы"),
    "marketing": ("📈", "Маркетинг и SMM", "Маркетологи, контент-мейкеры"),
    "finance": ("💰", "Финансы и инвестиции", "Частные инвесторы, люди интересующиеся деньгами"),
}


@router.message(Command("b2b"))
async def cmd_b2b(message: Message) -> None:
    """Показать B2B-маркетплейс: выбор ниши."""
    buttons = []
    for niche_code, (emoji, name, _) in NICHE_INFO.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {name}",
                callback_data=f"b2b_niche:{niche_code}",
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(
        "🏢 <b>B2B-маркетплейс</b>\n\n"
        "Готовые пакеты размещений по нишам.\n"
        "Скидка 10–25% vs разовые размещения.\n\n"
        "Выберите тематику:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("b2b_niche:"))
async def show_niche_packages(callback: CallbackQuery) -> None:
    """Показать пакеты выбранной ниши."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    niche_code = (callback.data or "").split(":")[1]
    niche_info = NICHE_INFO.get(niche_code)
    if niche_info is None:
        await callback.answer("Ниша не найдена")
        return

    emoji, name, audience = niche_info

    # ⚠️ АДАПТИРУЙ: получи пакеты из b2b_package_service
    # packages = await b2b_package_service.get_packages_by_niche(niche_code)

    # Временная заглушка — замени на реальные пакеты:
    packages = []

    if not packages:
        await safe_callback_edit(
            callback.message,
            f"{emoji} <b>{name}</b>\n\n"
            f"👥 Аудитория: {audience}\n\n"
            "⏳ Пакеты для этой ниши ещё формируются.\n"
            "Попробуйте позже или свяжитесь с поддержкой.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="◀️ Назад к нишам", callback_data="b2b_back")
            ]]),
            parse_mode="HTML",
        )
        return

    # Показать список пакетов
    buttons = []
    for pkg in packages:
        # ⚠️ Адаптируй под реальные поля пакета
        buttons.append([
            InlineKeyboardButton(
                text=f"{pkg.name} — {pkg.price} ₽ (−{pkg.discount_pct}%)",
                callback_data=f"b2b_package:{pkg.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="b2b_back")])

    await safe_callback_edit(
        callback.message,
        f"{emoji} <b>{name}</b>\n\n"
        f"👥 Аудитория: {audience}\n\n"
        "Выберите пакет:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("b2b_package:"))
async def show_package_details(callback: CallbackQuery) -> None:
    """Детальная карточка пакета."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    package_id = int((callback.data or "").split(":")[1])

    # ⚠️ АДАПТИРУЙ: получи пакет и его реальный охват
    # package = await b2b_package_service.get_by_id(package_id)
    # actual_reach = await b2b_package_service.get_package_actual_reach(package_id)
    # discount_value = await b2b_package_service.get_package_discount_value(package_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Медиакит", callback_data=f"b2b_mediakit:{package_id}")],
        [InlineKeyboardButton(
            text="🚀 Запустить кампанию с этим пакетом",
            callback_data=f"b2b_buy:{package_id}",
        )],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="b2b_back")],
    ])

    # ⚠️ Подставь реальные данные пакета
    await safe_callback_edit(
        callback.message,
        "📦 <b>Название пакета</b>\n\n"
        "📺 Каналов: N\n"
        "👥 Гарантированный охват: X просмотров\n"
        "📊 Минимальный ER: X%\n"
        "💰 Цена: X ₽\n"
        "🎁 Скидка: X% (экономия Y ₽)\n\n"
        "Описание аудитории...",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "b2b_back")
async def b2b_back(callback: CallbackQuery) -> None:
    """Вернуться к выбору ниши."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return
    # Переиспользуй cmd_b2b логику
    await show_b2b_niches(callback.message, edit=True)


async def show_b2b_niches(message_or_callback, edit: bool = False) -> None:
    """Вспомогательная функция — показать меню ниш."""
    # ⚠️ АДАПТИРУЙ: та же клавиатура что в cmd_b2b
    pass
```

Зарегистрируй роутер в главном файле бота.

### Коммит 3.5

```powershell
git add src/bot/handlers/b2b.py \
        src/core/services/b2b_package_service.py
git commit -m "feat(b2b): add /b2b handler with niche browser and package details"
```

---

## ЗАДАЧА 3.6: Медиакит PDF и расширение фильтров каталога

### Шаг 3.6.1 — Медиакит

В `src/core/services/b2b_package_service.py` добавь:

```python
async def generate_mediakit_pdf(self, channel_id: int) -> bytes:
    """
    Сгенерировать PDF-медиакит канала (PRD §5.4).

    Содержит: название, @username, тематика, аудитория, динамика подписчиков,
    средние просмотры, ER, цена за пост, примеры 3 последних постов, контакт.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer,
        )
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from io import BytesIO
    except ImportError:
        raise ImportError("reportlab не установлен: poetry add reportlab")

    # ⚠️ АДАПТИРУЙ: получи данные канала и последний ChannelRating
    # channel = await chat_repo.get_by_id(channel_id)
    # latest_rating = await channel_rating_repo.get_latest(channel_id)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = []

    # Заголовок
    story.append(Paragraph("МЕДИАКИТ КАНАЛА", styles["Title"]))
    story.append(Paragraph("@channel_username", styles["Heading2"]))  # ⚠️ реальный username
    story.append(Spacer(1, 20))

    # Таблица метрик
    data = [
        ["Метрика", "Значение"],
        ["Подписчики", "0"],       # ⚠️ channel.member_count
        ["Средние просмотры", "0"],# ⚠️ channel.last_avg_views
        ["ER", "0%"],              # ⚠️ latest_rating.er * 100
        ["Рейтинг", "0/100"],      # ⚠️ latest_rating.total_score
        ["Цена за пост", "0 ₽"],  # ⚠️ channel.price_per_post
    ]

    table = Table(data, colWidths=[200, 200])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    story.append(table)
    story.append(Spacer(1, 20))

    # Контакт
    story.append(Paragraph(
        "Для размещения рекламы: RekHarborBot → /add_channel",
        styles["Normal"],
    ))

    doc.build(story)
    return buffer.getvalue()
```

Добавь в `/b2b` хэндлер обработку `b2b_mediakit:{channel_id}`:

```python
@router.callback_query(F.data.startswith("b2b_mediakit:"))
async def send_channel_mediakit(callback: CallbackQuery) -> None:
    """Сгенерировать и отправить PDF медиакит канала."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    channel_id = int((callback.data or "").split(":")[1])
    await callback.answer("Генерирую медиакит...")

    try:
        # ⚠️ АДАПТИРУЙ: получи b2b_package_service
        # pdf = await b2b_package_service.generate_mediakit_pdf(channel_id)
        # from aiogram.types import BufferedInputFile
        # await callback.message.answer_document(
        #     BufferedInputFile(pdf, filename=f"mediakit_{channel_id}.pdf"),
        #     caption="📄 Медиакит канала",
        # )
        pass
    except Exception as e:
        logger.error(f"Mediakit generation failed for channel {channel_id}: {e}")
        await callback.answer("Ошибка генерации медиакита.", show_alert=True)
```

### Шаг 3.6.2 — Расширение фильтров каталога

```powershell
# Прочитай текущие фильтры
cat src/bot/handlers/channels_db.py
```

Добавь новые фильтры в существующий UI (не ломай текущие):

```python
# В клавиатуру фильтров добавить:

# ER-фильтр
InlineKeyboardButton(text="📊 ER ≥ 1%", callback_data="filter_er:1"),
InlineKeyboardButton(text="📊 ER ≥ 3%", callback_data="filter_er:3"),
InlineKeyboardButton(text="📊 ER ≥ 5%", callback_data="filter_er:5"),

# Рейтинг надёжности
InlineKeyboardButton(text="⭐ ≥ 3 звезды", callback_data="filter_stars:3"),
InlineKeyboardButton(text="⭐⭐ ≥ 4 звезды", callback_data="filter_stars:4"),

# Только растущие
InlineKeyboardButton(text="📈 Только растущие", callback_data="filter_growing:1"),
```

В SQL-запрос каталога добавить WHERE-условия (не заменять, добавлять к существующим):

```python
# ⚠️ Найди место формирования запроса каталога
# Добавить условия:

# if filters.get("min_er"):
#     query = query.join(ChannelRating, ...).where(
#         ChannelRating.er >= filters["min_er"] / 100
#     )
#
# if filters.get("min_stars"):
#     # через review_service или channel_rating
#     pass
#
# Всегда: исключить каналы с fraud_flag=True
# query = query.where(
#     ~exists(
#         select(ChannelRating.id).where(
#             ChannelRating.channel_id == TelegramChat.id,
#             ChannelRating.fraud_flag == True,
#         )
#     )
# )
```

### Шаг 3.6.3 — Unit тест медиакита

```python
# tests/unit/test_b2b_package_service.py
import pytest

class TestMediakit:
    @pytest.mark.asyncio
    async def test_generate_mediakit_returns_pdf_bytes(self):
        """generate_mediakit_pdf возвращает непустые PDF-байты."""
        # ⚠️ АДАПТИРУЙ с mock данными канала
        # svc = B2BPackageService(...)
        # pdf = await svc.generate_mediakit_pdf(channel_id=1)
        # assert isinstance(pdf, bytes)
        # assert len(pdf) > 0
        # assert pdf[:4] == b"%PDF"  # PDF magic bytes
        pass
```

```powershell
poetry run pytest tests/unit/test_b2b_package_service.py -v
```

### Проверка

```powershell
poetry run ruff check src/bot/handlers/b2b.py \
  src/core/services/b2b_package_service.py \
  src/bot/handlers/channels_db.py
poetry run mypy src/bot/handlers/b2b.py \
  src/core/services/b2b_package_service.py --ignore-missing-imports
```

### Коммит 3.6

```powershell
git add src/core/services/b2b_package_service.py \
        src/bot/handlers/b2b.py \
        src/bot/handlers/channels_db.py \
        tests/unit/test_b2b_package_service.py
git commit -m "feat(b2b): add mediakit PDF generation and ER/reliability catalog filters"
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
poetry run alembic current && poetry run alembic check

# 4. Тесты — особенно формула рейтинга
poetry run pytest tests/unit/test_rating_service.py -v
poetry run pytest tests/unit/ -v --tb=short 2>&1 | tail -25

# 5. Beat-расписание
grep "recalculate\|toplists\|fraud" src/tasks/celery_config.py

# 6. Ровно 6 коммитов
git log --oneline sprint/3 ^develop
```

Ожидаемые коммиты:
```
feat(b2b): add mediakit PDF generation and ER/reliability catalog filters
feat(b2b): add /b2b handler with niche browser and package details
feat(rating): add rating_tasks Celery jobs with beat schedule
feat(rating): add fraud detector with three anomaly signals
feat(rating): add rating_service with scoring formula from PRD §7.1
feat(b2b): add B2BPackage and ChannelRating models with migrations
```

```powershell
git push origin sprint/3
```

---

## Итоговый отчёт

```
═══════════════════════════════════════════════
 ОТЧЁТ: СПРИНТ 3 — B2B и рейтинговая система
═══════════════════════════════════════════════

Ветка: sprint/3

3.1 — Модели:
  B2BPackage мигрирована: [✅/❌]  JSONB channel_ids: [✅/❌]
  ChannelRating мигрирована: [✅/❌]  UniqueConstraint: [✅/❌]

3.2 — RatingService формула:
  Все 6 компонентов: [✅/❌]
  Веса в сумме = 1.0: [✅/❌]
  Unit тесты формулы: [N passed из 10]
  calculate_channel_score реальный: [✅/⚠️ заглушки]

3.3 — Детектор накрутки:
  Признак 1 (рост > 50%): [✅/⚠️]
  Признак 2 (низкий ER): [✅/⚠️]
  Признак 3 (отток): [✅/⚠️]
  Уведомление админа: [✅/⚠️]

3.4 — Celery задачи:
  recalculate_ratings_daily: [✅ в beat]
  update_weekly_toplists: [✅ в beat]
  run_fraud_detection: [✅ в beat]

3.5 — /b2b хэндлер:
  6 ниш отображаются: [✅/❌]
  Карточка пакета: [✅/❌]
  Пакеты из БД: [✅ реальные / ⚠️ пусто]

3.6 — Медиакит + фильтры:
  PDF медиакит: [✅ PDF bytes / ⚠️ заглушка]
  ER фильтр в каталоге: [✅/❌]
  fraud_flag исключает каналы: [✅/❌]

Ruff: [✅/❌]  Mypy: [✅/❌]
Тесты: [N passed, N failed]
Коммитов: [N]/7

Заглушки → Спринт 4: [список]
PR: sprint/3 → develop
```
