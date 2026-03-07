# Qwen Code Промт: Спринт 4 — Геймификация и удержание

## Обязательная ориентация перед стартом

```powershell
cd ~/python-projects/market-telegram-bot
source .venv/Scripts/activate

# 1. Прочитай дорожную карту целиком
cat ROADMAP.md

# 2. Убедись что Спринт 3 завершён и смержен в develop
git log --oneline develop | head -25
# Все коммиты sprint/3 должны быть в develop
```

После чтения дорожной карты зафикси:
- Что Спринт 4 добавляет поверх всего предыдущего (XP, уровни, значки, реферальная)
- Почему реферальная программа требует поля из Спринта 0-1 (`referred_by_id` уже в User)
- Что `total_spent` и `total_earned` нужно пересчитывать при каждом billing-событии

---

## Контекст Спринта 4

### Что добавляет этот спринт

Создаёт **психологические стимулы** к долгосрочному использованию.
Уровни и скидки удерживают рекламодателей (стоимость переключения).
Реферальная программа даёт органический рост без затрат на рекламу.
Дайджест возвращает неактивных пользователей.

### Что уже есть в User (поле `referred_by_id`)

```powershell
grep -n "referred_by_id\|referral_code" src/db/models/user.py
```

Это поле уже есть — Спринт 4 только добавляет **логику** начисления бонусов.

### Состав Спринта 4

| # | Задача | Файлы |
|---|--------|-------|
| 4.1 | Badge, UserBadge + поля User (level, xp, streak) | `models/badge.py`, `models/user.py` |
| 4.2 | XPService — уровни и прогресс | `services/xp_service.py` |
| 4.3 | BadgeService — выдача значков | `services/badge_service.py` |
| 4.4 | Геймификация в кабинете — прогресс-бар | `handlers/cabinet.py` |
| 4.5 | Реферальная программа — логика бонусов | `services/billing_service.py`, `handlers/cabinet.py`, `handlers/start.py` |
| 4.6 | Celery: стрики, дайджест, сезонные события | `tasks/gamification_tasks.py` |

---

## ГЛОБАЛЬНЫЕ ПРАВИЛА

1. **Читай файл целиком** перед любым изменением
2. **Таблица уровней строго из PRD §9.1** — используй реальные XP-пороги
3. **XP-триггеры добавляй к существующим событиям** — не переписывай их
4. **Один коммит на задачу** строго по плану

```powershell
# После каждой задачи:
poetry run ruff check src/
poetry run mypy src/ --ignore-missing-imports 2>&1 | tail -3
```

---

## ПОДГОТОВКА

```powershell
git checkout develop && git pull origin develop
git checkout -b sprint/4
git log --oneline -10
```

### Разведка структуры

```powershell
# User модель — что уже есть, что добавляем
cat src/db/models/user.py

# Cabinet handler — будем расширять
cat src/bot/handlers/cabinet.py

# Start handler — добавим обработку ref-параметра
cat src/bot/handlers/start.py | head -80

# Billing service — добавим реферальные бонусы
cat src/core/services/billing_service.py | grep -n "def \|async def "

# Как работают mailing_tasks — найдём точки для XP-триггеров
grep -n "campaign.*done\|DONE\|completed\|status.*=.*DONE\|CampaignStatus" \
  src/tasks/mailing_tasks.py | head -10
```

---

## ЗАДАЧА 4.1: Модели Badge/UserBadge и поля геймификации в User

### Шаг 4.1.1 — Изучи текущую модель User

```powershell
cat src/db/models/user.py
```

Зафикси:
- Стиль объявления полей (Mapped vs Column)
- Какие поля уже есть (credits, balance, plan, referred_by_id)
- Есть ли уже `level`, `xp_points`, `total_spent`?

### Шаг 4.1.2 — Создай модели Badge/UserBadge

**Файл:** `src/db/models/badge.py`

```python
"""
Модели системы значков.

Badge — каталог всех возможных значков платформы (создаётся через seed).
UserBadge — факт выдачи значка конкретному пользователю.

PRD §9.2: значки за действия — Первый запуск, 100 размещений, Идеальный CTR и т.д.
"""
from enum import Enum as PyEnum


class BadgeCategory(str, PyEnum):
    ADVERTISER = "advertiser"  # только для рекламодателей
    OWNER = "owner"            # только для владельцев каналов
    BOTH = "both"              # для всех


class BadgeConditionType(str, PyEnum):
    CAMPAIGNS_COUNT = "campaigns_count"       # количество кампаний
    SPEND_AMOUNT = "spend_amount"             # суммарно потрачено
    PLACEMENTS_COUNT = "placements_count"     # количество размещений (для владельцев)
    EARNED_AMOUNT = "earned_amount"           # суммарно заработано
    STREAK_DAYS = "streak_days"               # стрик активности
    REVIEW_COUNT = "review_count"             # количество оставленных отзывов
    MANUAL = "manual"                         # выдаётся вручную администратором


class Badge(Base):
    __tablename__ = "badges"

    # id — по образцу
    code: ...         # String(100), unique — "first_campaign", "hundred_posts" и т.д.
    name: ...         # String(200)
    description: ...  # Text
    icon_emoji: ...   # String(10)
    xp_reward: ...    # Integer — сколько XP даёт значок
    category: ...     # String(20) — BadgeCategory
    condition_type: ... # String(50) — BadgeConditionType
    condition_value: ...# Integer — порог (например 1 для "первая кампания", 100 для "100 кампаний")
    is_active: ...    # Boolean, default=True


class UserBadge(Base):
    __tablename__ = "user_badges"

    # id — по образцу
    user_id: ...    # BigInteger FK → users.id
    badge_id: ...   # Integer FK → badges.id
    earned_at: ...  # DateTime(timezone=True), default=now

    # ⚠️ UniqueConstraint: каждый значок выдаётся пользователю только один раз
    # __table_args__ = (UniqueConstraint("user_id", "badge_id"),)
```

### Шаг 4.1.3 — Добавь поля геймификации в User

**Файл:** `src/db/models/user.py`

Добавь к существующим полям (не меняй существующие):

```python
# === Геймификация (Спринт 4) ===
level: ...        # Integer, default=1 — уровень 1-10
xp_points: ...    # Integer, default=0 — опыт
total_spent: ...  # Numeric(12, 2), default=0 — суммарно потрачено (для уровня рекламодателя)
total_earned: ... # Numeric(12, 2), default=0 — суммарно заработано (для уровня владельца)
streak_days: ...  # Integer, default=0 — дни активности подряд
```

### Шаг 4.1.4 — Создай seed-файл базовых значков

**Файл:** `scripts/seed_badges.py` (создать)

```python
"""
Seed-скрипт для наполнения таблицы badges базовыми значками.
Запуск: python scripts/seed_badges.py

PRD §9.2 примеры значков.
"""

INITIAL_BADGES = [
    {
        "code": "first_campaign",
        "name": "Первый запуск",
        "description": "Запустите первую рекламную кампанию",
        "icon_emoji": "🚀",
        "xp_reward": 200,
        "category": "advertiser",
        "condition_type": "campaigns_count",
        "condition_value": 1,
    },
    {
        "code": "ten_campaigns",
        "name": "Опытный рекламодатель",
        "description": "10 запущенных кампаний",
        "icon_emoji": "💼",
        "xp_reward": 500,
        "category": "advertiser",
        "condition_type": "campaigns_count",
        "condition_value": 10,
    },
    {
        "code": "hundred_campaigns",
        "name": "Мастер рекламы",
        "description": "100 запущенных кампаний",
        "icon_emoji": "💎",
        "xp_reward": 2000,
        "category": "advertiser",
        "condition_type": "campaigns_count",
        "condition_value": 100,
    },
    {
        "code": "first_placement",
        "name": "Первое размещение",
        "description": "Выполните первое рекламное размещение в своём канале",
        "icon_emoji": "📢",
        "xp_reward": 150,
        "category": "owner",
        "condition_type": "placements_count",
        "condition_value": 1,
    },
    {
        "code": "streak_7",
        "name": "Неделя активности",
        "description": "7 дней активности подряд",
        "icon_emoji": "🔥",
        "xp_reward": 300,
        "category": "both",
        "condition_type": "streak_days",
        "condition_value": 7,
    },
    {
        "code": "streak_30",
        "name": "Месяц активности",
        "description": "30 дней активности подряд",
        "icon_emoji": "⚡",
        "xp_reward": 1000,
        "category": "both",
        "condition_type": "streak_days",
        "condition_value": 30,
    },
    {
        "code": "review_master",
        "name": "Честный отзыв",
        "description": "Оставьте 10 отзывов о размещениях",
        "icon_emoji": "⭐",
        "xp_reward": 400,
        "category": "both",
        "condition_type": "review_count",
        "condition_value": 10,
    },
]

# ⚠️ АДАПТИРУЙ: добавь логику сохранения в БД
# Используй тот же способ получения сессии что в других скриптах
if __name__ == "__main__":
    print(f"Would seed {len(INITIAL_BADGES)} badges")
    # for badge_data in INITIAL_BADGES:
    #     badge = Badge(**badge_data)
    #     session.merge(badge)  # upsert по code
    # session.commit()
```

### Шаг 4.1.5 — Миграции

```powershell
# Добавь импорты в alembic/env.py
poetry run alembic revision --autogenerate -m "add_badge_models"
poetry run alembic upgrade head

poetry run alembic revision --autogenerate -m "add_gamification_fields_to_user"
poetry run alembic upgrade head

poetry run alembic current  # → head
```

### Проверка

```powershell
poetry run ruff check src/db/models/badge.py src/db/models/user.py
poetry run mypy src/db/models/badge.py src/db/models/user.py --ignore-missing-imports
```

### Коммит 4.1

```powershell
git add src/db/models/badge.py src/db/models/user.py \
        alembic/versions/ alembic/env.py scripts/seed_badges.py
git commit -m "feat(gamification): add Badge, UserBadge models and gamification fields to User"
```

---

## ЗАДАЧА 4.2: XPService — уровни и прогресс

### Шаг 4.2.1 — Таблица уровней из PRD §9.1

| Уровень | Название | XP от | XP до | Скидка |
|---------|----------|-------|-------|--------|
| 1 | Новичок | 0 | 499 | 0% |
| 2 | Активный | 500 | 1 499 | 0% |
| 3 | Опытный | 1 500 | 3 999 | 3% |
| 4 | Продвинутый | 4 000 | 8 999 | 3% |
| 5 | Профи | 9 000 | 19 999 | 7% |
| 6 | Эксперт | 20 000 | 39 999 | 7% |
| 7 | Ветеран | 40 000 | 79 999 | 7% |
| 8 | Мастер | 80 000 | 149 999 | 12% |
| 9 | Гранд-мастер | 150 000 | 299 999 | 12% |
| 10 | Легенда | 300 000 | ∞ | 15% |

### Шаг 4.2.2 — Создай XPService

**Файл:** `src/core/services/xp_service.py`

```python
"""
Сервис системы опыта и уровней.
Таблица уровней: PRD §9.1.
"""
import logging
from dataclasses import dataclass
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class LevelUpEvent:
    """Событие повышения уровня."""
    user_id: int
    old_level: int
    new_level: int
    new_privileges: "LevelPrivileges"


@dataclass
class LevelPrivileges:
    """Привилегии уровня."""
    level: int
    name: str
    discount_pct: int     # скидка на комиссию платформы
    features: list[str]   # список дополнительных возможностей


@dataclass
class LevelProgress:
    """Прогресс пользователя к следующему уровню."""
    current_level: int
    current_xp: int
    level_min_xp: int     # XP с которого начинается текущий уровень
    level_max_xp: int     # XP с которого начнётся следующий (-1 для Легенды)
    progress_pct: float   # 0.0 - 100.0
    xp_to_next: int       # сколько XP до следующего уровня (0 для Легенды)


# Таблица уровней (xp_min включительно)
LEVEL_TABLE: list[tuple[int, str, int, list[str]]] = [
    # (xp_min, name, discount_pct, features)
    (0,       "Новичок",        0,   []),
    (500,     "Активный",       0,   ["Доступ к топ-листам"]),
    (1_500,   "Опытный",        3,   ["Скидка 3% на комиссию"]),
    (4_000,   "Продвинутый",    3,   ["Скидка 3% на комиссию"]),
    (9_000,   "Профи",          7,   ["Скидка 7%", "Приоритетная поддержка"]),
    (20_000,  "Эксперт",        7,   ["Скидка 7%", "Приоритетная поддержка"]),
    (40_000,  "Ветеран",        7,   ["Скидка 7%", "Ранний доступ к новым функциям"]),
    (80_000,  "Мастер",         12,  ["Скидка 12%", "Ранний доступ"]),
    (150_000, "Гранд-мастер",   12,  ["Скидка 12%"]),
    (300_000, "Легенда",        15,  ["Скидка 15%", "Именная карточка в каталоге"]),
]


def get_level_for_xp(xp: int) -> int:
    """Вернуть уровень (1-10) для данного количества XP."""
    level = 1
    for i, (xp_min, _, _, _) in enumerate(LEVEL_TABLE):
        if xp >= xp_min:
            level = i + 1
        else:
            break
    return level


def get_level_privileges(level: int) -> LevelPrivileges:
    """Вернуть привилегии для уровня."""
    if not (1 <= level <= 10):
        level = max(1, min(10, level))
    xp_min, name, discount, features = LEVEL_TABLE[level - 1]
    return LevelPrivileges(
        level=level,
        name=name,
        discount_pct=discount,
        features=features,
    )


def get_progress(xp: int) -> LevelProgress:
    """Рассчитать прогресс к следующему уровню."""
    current_level = get_level_for_xp(xp)
    level_idx = current_level - 1

    level_min_xp = LEVEL_TABLE[level_idx][0]

    if current_level == 10:
        return LevelProgress(
            current_level=10,
            current_xp=xp,
            level_min_xp=level_min_xp,
            level_max_xp=-1,
            progress_pct=100.0,
            xp_to_next=0,
        )

    level_max_xp = LEVEL_TABLE[level_idx + 1][0]
    xp_in_level = xp - level_min_xp
    xp_for_level = level_max_xp - level_min_xp
    progress_pct = (xp_in_level / xp_for_level) * 100 if xp_for_level > 0 else 0

    return LevelProgress(
        current_level=current_level,
        current_xp=xp,
        level_min_xp=level_min_xp,
        level_max_xp=level_max_xp,
        progress_pct=min(100.0, progress_pct),
        xp_to_next=max(0, level_max_xp - xp),
    )


class XPService:

    # ⚠️ АДАПТИРУЙ инжекцию зависимостей

    async def add_xp(
        self,
        user_id: int,
        amount: int,
        reason: str,
    ) -> LevelUpEvent | None:
        """
        Начислить XP пользователю.
        Если уровень повысился — вернуть LevelUpEvent, иначе None.

        Reason используется для логирования (например: "campaign_launched").
        """
        if amount <= 0:
            return None

        # ⚠️ АДАПТИРУЙ: получи и обнови User
        # user = await user_repo.get_by_id(user_id)
        # if user is None:
        #     logger.error(f"add_xp: user {user_id} not found")
        #     return None

        # old_level = user.level
        # new_xp = user.xp_points + amount
        # new_level = get_level_for_xp(new_xp)

        # await user_repo.update_xp(user_id, xp_points=new_xp, level=new_level)
        # logger.info(f"User {user_id}: +{amount} XP ({reason}). Total: {new_xp}")

        # if new_level > old_level:
        #     return LevelUpEvent(
        #         user_id=user_id,
        #         old_level=old_level,
        #         new_level=new_level,
        #         new_privileges=get_level_privileges(new_level),
        #     )
        return None  # ← замени

    async def get_progress_to_next_level(self, user_id: int) -> LevelProgress:
        """Получить прогресс пользователя к следующему уровню."""
        # ⚠️ АДАПТИРУЙ
        # user = await user_repo.get_by_id(user_id)
        # return get_progress(user.xp_points)
        return get_progress(0)  # ← замени
```

### Шаг 4.2.3 — Unit тесты XPService

**Файл:** `tests/unit/test_xp_service.py`

```python
"""Unit тесты XPService — строгая проверка таблицы уровней."""
import pytest
from src.core.services.xp_service import (
    get_level_for_xp, get_level_privileges, get_progress, LEVEL_TABLE,
)


class TestLevelTable:

    def test_level_1_at_zero_xp(self):
        assert get_level_for_xp(0) == 1

    def test_level_1_just_before_threshold(self):
        assert get_level_for_xp(499) == 1

    def test_level_2_at_threshold(self):
        assert get_level_for_xp(500) == 2

    def test_level_3_at_threshold(self):
        assert get_level_for_xp(1_500) == 3

    def test_level_10_at_threshold(self):
        assert get_level_for_xp(300_000) == 10

    def test_level_10_above_threshold(self):
        assert get_level_for_xp(999_999) == 10

    def test_all_10_levels_defined(self):
        assert len(LEVEL_TABLE) == 10

    def test_thresholds_strictly_increasing(self):
        thresholds = [t[0] for t in LEVEL_TABLE]
        assert thresholds == sorted(thresholds)
        assert len(set(thresholds)) == len(thresholds)


class TestLevelPrivileges:

    def test_level_1_no_discount(self):
        privs = get_level_privileges(1)
        assert privs.discount_pct == 0

    def test_level_3_discount_3_pct(self):
        privs = get_level_privileges(3)
        assert privs.discount_pct == 3

    def test_level_5_discount_7_pct(self):
        privs = get_level_privileges(5)
        assert privs.discount_pct == 7

    def test_level_8_discount_12_pct(self):
        privs = get_level_privileges(8)
        assert privs.discount_pct == 12

    def test_level_10_discount_15_pct(self):
        privs = get_level_privileges(10)
        assert privs.discount_pct == 15


class TestLevelProgress:

    def test_progress_at_zero_xp(self):
        p = get_progress(0)
        assert p.current_level == 1
        assert p.progress_pct == 0.0
        assert p.xp_to_next == 500  # до уровня 2

    def test_progress_halfway_to_level_2(self):
        p = get_progress(250)  # половина пути к уровню 2 (500)
        assert p.current_level == 1
        assert abs(p.progress_pct - 50.0) < 1.0

    def test_progress_at_max_level(self):
        p = get_progress(300_000)
        assert p.current_level == 10
        assert p.progress_pct == 100.0
        assert p.xp_to_next == 0

    def test_progress_bar_always_0_to_100(self):
        for xp in [0, 499, 500, 1000, 5000, 100_000, 300_000, 999_999]:
            p = get_progress(xp)
            assert 0.0 <= p.progress_pct <= 100.0
```

```powershell
poetry run pytest tests/unit/test_xp_service.py -v
# Ожидаем: все тесты PASS — таблица уровней верна
```

### Коммит 4.2

```powershell
git add src/core/services/xp_service.py tests/unit/test_xp_service.py
git commit -m "feat(gamification): add xp_service with level system from PRD §9.1"
```

---

## ЗАДАЧА 4.3: BadgeService и XP-триггеры

### Шаг 4.3.1 — Создай BadgeService

**Файл:** `src/core/services/badge_service.py`

```python
"""
Сервис системы значков.
Проверяет условия выдачи и начисляет XP через xp_service.
"""
import logging

logger = logging.getLogger(__name__)


class BadgeService:

    # ⚠️ АДАПТИРУЙ: xp_service инжектируется как зависимость

    async def check_and_award_badges(self, user_id: int) -> list["Badge"]:
        """
        Проверить все активные значки и выдать незаработанные.
        Вызывается после любого события которое может дать значок.
        Returns: список только что выданных значков.
        """
        # ⚠️ АДАПТИРУЙ:
        # all_badges = await badge_repo.get_active()
        # user_badge_codes = await user_badge_repo.get_codes_for_user(user_id)
        # user_stats = await self._get_user_stats(user_id)
        #
        # newly_awarded = []
        # for badge in all_badges:
        #     if badge.code in user_badge_codes:
        #         continue  # уже есть
        #     if await self._check_condition(badge, user_stats):
        #         awarded = await self.award_badge(user_id, badge.code)
        #         if awarded:
        #             newly_awarded.append(awarded)
        # return newly_awarded
        return []

    async def award_badge(self, user_id: int, badge_code: str) -> "Badge | None":
        """
        Выдать конкретный значок пользователю.
        Начисляет XP за значок через xp_service.
        Идемпотентен — повторный вызов ничего не делает.
        """
        # ⚠️ АДАПТИРУЙ:
        # badge = await badge_repo.get_by_code(badge_code)
        # if badge is None:
        #     logger.error(f"Badge {badge_code} not found")
        #     return None
        #
        # try:
        #     await user_badge_repo.create(user_id=user_id, badge_id=badge.id)
        # except UniqueViolation:
        #     return None  # уже есть — ок, не ошибка
        #
        # # Начислить XP за значок
        # level_up = await xp_service.add_xp(user_id, badge.xp_reward, f"badge:{badge_code}")
        # if level_up:
        #     await self._notify_level_up(user_id, level_up)
        #
        # logger.info(f"Badge {badge_code} awarded to user {user_id}")
        # return badge
        return None

    async def get_user_badges(self, user_id: int) -> list["Badge"]:
        """Получить все значки пользователя, отсортированные по дате получения."""
        # ⚠️ АДАПТИРУЙ
        return []

    async def _check_condition(self, badge: "Badge", user_stats: dict) -> bool:
        """Проверить выполнено ли условие значка для пользователя."""
        condition_type = badge.condition_type
        condition_value = badge.condition_value

        if condition_type == "campaigns_count":
            return user_stats.get("campaigns_count", 0) >= condition_value
        elif condition_type == "spend_amount":
            return float(user_stats.get("total_spent", 0)) >= condition_value
        elif condition_type == "placements_count":
            return user_stats.get("placements_count", 0) >= condition_value
        elif condition_type == "earned_amount":
            return float(user_stats.get("total_earned", 0)) >= condition_value
        elif condition_type == "streak_days":
            return user_stats.get("streak_days", 0) >= condition_value
        elif condition_type == "review_count":
            return user_stats.get("review_count", 0) >= condition_value
        elif condition_type == "manual":
            return False  # только вручную администратором
        return False

    async def _get_user_stats(self, user_id: int) -> dict:
        """Собрать статистику пользователя для проверки условий значков."""
        # ⚠️ АДАПТИРУЙ: получи из User и связанных таблиц
        return {
            "campaigns_count": 0,
            "total_spent": 0,
            "placements_count": 0,
            "total_earned": 0,
            "streak_days": 0,
            "review_count": 0,
        }
```

### Шаг 4.3.2 — Добавь XP-триггеры в существующий код

Найди точки событий и добавь вызовы `xp_service.add_xp()`:

```powershell
# 1. Кампания запущена — +50 XP
grep -n "status.*QUEUED\|campaign.*queued\|freeze_funds" \
  src/tasks/mailing_tasks.py src/core/services/billing_service.py | head -10

# 2. Кампания завершена — +100 XP
grep -n "status.*DONE\|campaign.*done\|COMPLETED" \
  src/tasks/mailing_tasks.py | head -10

# 3. Размещение выполнено (владелец) — +30 XP
grep -n "release_funds\|placement.*sent\|SENT" \
  src/core/services/billing_service.py src/tasks/mailing_tasks.py | head -10

# 4. Отзыв оставлен — +20 XP
grep -n "submit_review" src/core/services/review_service.py
```

В каждое из этих мест добавь **после** основной логики (не вместо):

```python
# После основного события добавить вызов (паттерн):
try:
    # ⚠️ АДАПТИРУЙ: получи xp_service
    level_up = await xp_service.add_xp(user_id, amount=50, reason="campaign_launched")
    if level_up:
        # Уведомить пользователя о повышении уровня
        # await notification_tasks.notify_level_up.delay(user_id, level_up.new_level)
        pass
    # Проверить значки
    # await badge_service.check_and_award_badges(user_id)
except Exception as e:
    # XP-ошибки не должны ломать основной флоу
    logger.warning(f"XP award failed for user {user_id}: {e}")
```

⚠️ **XP-ошибки всегда в try/except** — геймификация не должна прерывать основные операции.

### Шаг 4.3.3 — Unit тест BadgeService

```python
# tests/unit/test_badge_service.py
import pytest
from src.core.services.badge_service import BadgeService


class TestBadgeConditionCheck:

    def setup_method(self):
        self.svc = BadgeService()  # ⚠️ адаптируй

    @pytest.mark.asyncio
    async def test_campaigns_count_condition_met(self):
        """Условие campaigns_count выполнено когда достигнут порог."""
        # mock badge: condition_type=campaigns_count, condition_value=1
        # user_stats: campaigns_count=1
        # assert _check_condition(badge, stats) == True
        pass

    @pytest.mark.asyncio
    async def test_campaigns_count_condition_not_met(self):
        """Условие не выполнено когда ниже порога."""
        # user_stats: campaigns_count=0, condition_value=1
        # assert _check_condition(badge, stats) == False
        pass

    @pytest.mark.asyncio
    async def test_manual_badge_never_auto_awarded(self):
        """Значок с condition_type=manual всегда возвращает False."""
        # Создай mock badge с condition_type="manual"
        # assert await svc._check_condition(badge, any_stats) == False
        pass
```

### Коммит 4.3

```powershell
git add src/core/services/badge_service.py \
        src/tasks/mailing_tasks.py \
        src/core/services/billing_service.py \
        src/core/services/review_service.py \
        tests/unit/test_badge_service.py
git commit -m "feat(gamification): add badge_service with condition checking and XP triggers"
```

---

## ЗАДАЧА 4.4: Прогресс-бар и значки в кабинете

### Шаг 4.4.1 — Прочитай текущий кабинет

```powershell
cat src/bot/handlers/cabinet.py
```

Зафикси: что сейчас показывается в кабинете, как добавить блок геймификации.

### Шаг 4.4.2 — Добавь блок геймификации

Найди основной хэндлер показа кабинета и добавь вызов геймификации:

```python
# В хэндлере /cabinet или кнопки «Кабинет» — добавить после основных данных:

# ⚠️ АДАПТИРУЙ: получи xp_service и badge_service
# progress = await xp_service.get_progress_to_next_level(user.id)
# badges = await badge_service.get_user_badges(user.id)
# privileges = get_level_privileges(progress.current_level)

def _format_progress_bar(progress_pct: float, width: int = 10) -> str:
    """Построить текстовый прогресс-бар. 67% → ██████████░░░░"""
    filled = int(progress_pct / 100 * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def _format_gamification_block(
    level: int,
    level_name: str,
    xp: int,
    progress: "LevelProgress",
    discount_pct: int,
    badges: list,
) -> str:
    """Форматировать блок геймификации для кабинета."""
    bar = _format_progress_bar(progress.progress_pct)
    badges_display = " ".join(b.icon_emoji for b in badges[:6]) if badges else "—"
    xp_info = (
        f"{xp:,} / {progress.level_max_xp:,} XP".replace(",", " ")
        if progress.current_level < 10
        else f"{xp:,} XP (максимум)".replace(",", " ")
    )

    discount_line = f"🎯 Скидка {discount_pct}% на размещения\n" if discount_pct > 0 else ""
    to_next = (
        f"До следующего уровня: {progress.xp_to_next:,} XP".replace(",", " ")
        if progress.current_level < 10
        else "🏆 Достигнут максимальный уровень!"
    )

    return (
        f"\n─────────────────\n"
        f"📊 Уровень {level} — <b>{level_name}</b>\n"
        f"⚡ {xp_info} {bar} {progress.progress_pct:.0f}%\n"
        f"{discount_line}"
        f"ℹ️ {to_next}\n"
        f"\n🏆 Значки ({len(badges)}): {badges_display}"
    )
```

Добавь кнопку «🏆 Все значки» в клавиатуру кабинета:

```python
InlineKeyboardButton(text="🏆 Все значки", callback_data="show_all_badges")
```

Добавь хэндлер показа всех значков:

```python
@router.callback_query(F.data == "show_all_badges")
async def show_all_badges(callback: CallbackQuery) -> None:
    """Показать все значки пользователя и незаработанные с условиями."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    # ⚠️ АДАПТИРУЙ: получи earned и all badges
    # earned_badges = await badge_service.get_user_badges(user.id)
    # all_badges = await badge_repo.get_active()
    # earned_codes = {b.code for b in earned_badges}

    # Построить текст:
    # ✅ для заработанных, 🔒 для незаработанных с условием
    await safe_callback_edit(
        callback.message,
        "🏆 <b>Ваши значки</b>\n\n"
        "✅ Заработанные:\n(нет)\n\n"  # ⚠️ реальные данные
        "🔒 Незаработанные:\n(нет)",   # ⚠️ реальные данные
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="◀️ Кабинет", callback_data="back_to_cabinet")
        ]]),
        parse_mode="HTML",
    )
```

### Шаг 4.4.3 — Проверка

```powershell
poetry run ruff check src/bot/handlers/cabinet.py
poetry run mypy src/bot/handlers/cabinet.py --ignore-missing-imports
```

### Коммит 4.4

```powershell
git add src/bot/handlers/cabinet.py
git commit -m "feat(cabinet): add level progress bar and badges display"
```

---

## ЗАДАЧА 4.5: Реферальная программа

### Шаг 4.5.1 — Проверь что уже есть

```powershell
# Поле referred_by_id уже должно быть в User (создано до Sprint 0)
grep -n "referred_by_id\|referral_code" src/db/models/user.py

# Как сейчас обрабатывается /start с параметрами
grep -n "start.*param\|command.*start\|deep_link\|payload" \
  src/bot/handlers/start.py | head -10
```

### Шаг 4.5.2 — Добавь бонусные методы в BillingService

В `src/core/services/billing_service.py`:

```python
async def apply_referral_bonus_advertiser(self, referred_user_id: int) -> bool:
    """
    Начислить бонус рефереру за приведённого рекламодателя.
    Вызывается после первой оплаченной кампании реферала.
    Бонус: +500 кр. (PRD §9.3)

    Returns True если бонус начислен, False если уже начислялся или реферера нет.
    """
    # ⚠️ АДАПТИРУЙ:
    # user = await user_repo.get_by_id(referred_user_id)
    # if user.referred_by_id is None:
    #     return False
    #
    # # Проверить что это первая кампания (чтобы не начислять повторно)
    # campaign_count = await campaign_repo.count_by_user(referred_user_id)
    # if campaign_count != 1:  # строго первая
    #     return False
    #
    # await billing_service.add_credits(user.referred_by_id, 500, "referral_advertiser")
    # logger.info(f"Referral bonus 500 cr → user {user.referred_by_id}")
    # return True
    return False

async def apply_referral_bonus_channel(self, referred_user_id: int) -> bool:
    """
    Начислить бонус рефереру за первое размещение приведённого владельца канала.
    Бонус: +300 кр. (PRD §9.3)
    """
    # ⚠️ АДАПТИРУЙ аналогично apply_referral_bonus_advertiser
    # Проверить что это первое размещение (placement_count == 1)
    return False
```

### Шаг 4.5.3 — Добавь вызовы бонусов в триггерных точках

```powershell
# Первая кампания рекламодателя — где переходит из DRAFT в QUEUED?
grep -n "freeze_funds\|campaign.*QUEUED\|first.*campaign" \
  src/tasks/mailing_tasks.py src/core/services/billing_service.py | head -10
```

Добавь вызов после первой оплаты кампании:
```python
# После успешного freeze_funds — первой оплаты:
try:
    await billing_service.apply_referral_bonus_advertiser(user_id)
except Exception as e:
    logger.warning(f"Referral bonus failed: {e}")
```

### Шаг 4.5.4 — Обработка параметра в /start

```powershell
cat src/bot/handlers/start.py | grep -n "CommandStart\|payload\|args\|deep"
```

Найди или добавь обработчик `/start ref_CODE`:

```python
from aiogram.filters import CommandStart, CommandObject

@router.message(CommandStart())
async def cmd_start_with_referral(
    message: Message,
    command: CommandObject,
) -> None:
    """
    /start — регистрация нового пользователя.
    /start ref_ABC123 — регистрация по реферальной ссылке.
    """
    # ⚠️ АДАПТИРУЙ: адаптируй под существующий /start флоу
    # Не заменяй существующий хэндлер — расширяй:

    referral_code: str | None = None
    if command.args and command.args.startswith("ref_"):
        referral_code = command.args[4:]  # убираем "ref_" префикс

    # При создании нового пользователя:
    if referral_code:
        # ⚠️ Найди реферера по referral_code и запиши referred_by_id
        # referrer = await user_repo.get_by_referral_code(referral_code)
        # if referrer:
        #     await user_repo.set_referred_by(new_user.id, referrer.id)
        pass
```

### Шаг 4.5.5 — Реферальный раздел в кабинете

В `src/bot/handlers/cabinet.py` добавь кнопку и хэндлер:

```python
InlineKeyboardButton(text="🔗 Реферальная программа", callback_data="referral_program")


@router.callback_query(F.data == "referral_program")
async def show_referral_program(callback: CallbackQuery) -> None:
    """Реферальный раздел кабинета."""
    if callback.message is None or isinstance(callback.message, InaccessibleMessage):
        return

    # ⚠️ АДАПТИРУЙ: получи данные пользователя
    # user = await user_repo.get_by_telegram_id(callback.from_user.id)
    # referrals_count = await user_repo.count_referrals(user.id)
    # referral_earnings = await billing_service.get_referral_earnings(user.id)
    # ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.referral_code}"

    await safe_callback_edit(
        callback.message,
        "🔗 <b>Реферальная программа</b>\n\n"
        "За каждого приведённого рекламодателя:\n"
        "<b>+500 кр</b> после его первой кампании\n\n"
        "За каждый приведённый канал:\n"
        "<b>+300 кр</b> после первого размещения\n\n"
        "Ваша ссылка:\n"
        "<code>https://t.me/bot?start=ref_YOUR_CODE</code>\n\n"  # ⚠️ реальная ссылка
        "👥 Приведено пользователей: 0\n"   # ⚠️ реальные данные
        "💰 Заработано через рефералов: 0 кр",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_cabinet")
        ]]),
        parse_mode="HTML",
    )
```

### Шаг 4.5.6 — Unit тест реферальных бонусов

```python
# tests/unit/test_referral.py
import pytest
from decimal import Decimal


class TestReferralBonuses:

    @pytest.mark.asyncio
    async def test_bonus_only_on_first_campaign(self):
        """Бонус начисляется только за первую кампанию реферала."""
        # Mock: user с referred_by_id, campaign_count=1
        # result = await billing_service.apply_referral_bonus_advertiser(user_id)
        # assert result == True
        pass

    @pytest.mark.asyncio
    async def test_no_bonus_on_second_campaign(self):
        """Бонус НЕ начисляется за вторую и последующие кампании."""
        # Mock: campaign_count=2
        # result = await billing_service.apply_referral_bonus_advertiser(user_id)
        # assert result == False
        pass

    @pytest.mark.asyncio
    async def test_no_bonus_without_referrer(self):
        """Без реферера бонус не начисляется."""
        # Mock: user.referred_by_id = None
        # result = await billing_service.apply_referral_bonus_advertiser(user_id)
        # assert result == False
        pass
```

### Коммит 4.5

```powershell
git add src/core/services/billing_service.py \
        src/bot/handlers/cabinet.py \
        src/bot/handlers/start.py \
        tests/unit/test_referral.py
git commit -m "feat(referral): implement referral bonus logic and cabinet referral section"
```

---

## ЗАДАЧА 4.6: Celery задачи геймификации

**Файл:** `src/tasks/gamification_tasks.py` (создать)

```python
"""
Celery задачи геймификации.

Расписание:
- update_streaks_daily: каждый день 02:00 UTC
- send_weekly_digest: каждый понедельник 08:00 UTC
- check_seasonal_events: каждый день 03:00 UTC
"""
import logging
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="gamification:update_streaks_daily")
def update_streaks_daily() -> dict:
    """
    Обновить стрики активности всех пользователей.

    Логика:
    - Если пользователь был активен вчера (создал кампанию или выполнил размещение)
      → streak_days + 1
    - Если не был активен → streak_days = 0
    - При достижении 7 или 30 дней → check_and_award_badges
    """
    updated, reset = 0, 0
    # ⚠️ АДАПТИРУЙ:
    # Вчерашняя дата: yesterday = date.today() - timedelta(days=1)
    # active_users = active_yesterday(yesterday)  # из campaigns/placements
    # all_users_with_streak = users_with_streak_gt_0()
    # ...
    return {"status": "ok", "updated": updated, "reset": reset}


@celery_app.task(name="gamification:send_weekly_digest")
def send_weekly_digest() -> dict:
    """
    Еженедельный дайджест для активных пользователей (каждый понедельник).

    Для рекламодателей: суммарный охват за неделю, лучшая кампания, прогресс уровня.
    Для владельцев: заработок за неделю, количество размещений, изменение рейтинга.
    Только пользователям с notifications_enabled=True.
    """
    sent, skipped = 0, 0
    # ⚠️ АДАПТИРУЙ:
    # active_users = users_active_last_7_days()
    # for user in active_users:
    #     if not user.notifications_enabled:
    #         skipped += 1; continue
    #     try:
    #         _send_digest_for_user(user)
    #         sent += 1
    #     except Exception as e:
    #         logger.warning(f"Digest failed for {user.id}: {e}")
    return {"status": "ok", "sent": sent, "skipped": skipped}


@celery_app.task(name="gamification:check_seasonal_events")
def check_seasonal_events() -> dict:
    """
    Проверить активные сезонные ивенты и начислить бонусы.
    Текущая реализация: заглушка — ивенты добавляются вручную.
    """
    # Сезонные ивенты реализуются отдельно по мере необходимости
    logger.info("check_seasonal_events: no active events")
    return {"status": "ok", "active_events": 0}
```

Добавь в `src/tasks/celery_config.py`:

```python
"update-streaks-daily": {
    "task": "gamification:update_streaks_daily",
    "schedule": crontab(hour=2, minute=0),
},
"send-weekly-digest": {
    "task": "gamification:send_weekly_digest",
    "schedule": crontab(day_of_week=1, hour=8, minute=0),
},
"check-seasonal-events": {
    "task": "gamification:check_seasonal_events",
    "schedule": crontab(hour=3, minute=0),
},
```

### Проверка

```powershell
poetry run ruff check src/tasks/gamification_tasks.py
poetry run mypy src/tasks/gamification_tasks.py --ignore-missing-imports
grep "update-streaks\|weekly-digest\|seasonal-events" src/tasks/celery_config.py
```

### Коммит 4.6

```powershell
git add src/tasks/gamification_tasks.py src/tasks/celery_config.py
git commit -m "feat(gamification): add weekly digest, streak and seasonal event Celery tasks"
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

# 4. Тесты — особенно таблица уровней (критична для бизнес-логики)
poetry run pytest tests/unit/test_xp_service.py -v
poetry run pytest tests/unit/ -v --tb=short 2>&1 | tail -25

# 5. Beat-расписание геймификации
grep "streaks\|digest\|seasonal" src/tasks/celery_config.py

# 6. Ровно 6 коммитов
git log --oneline sprint/4 ^develop
```

Ожидаемые коммиты:
```
feat(gamification): add weekly digest, streak and seasonal event Celery tasks
feat(referral): implement referral bonus logic and cabinet referral section
feat(cabinet): add level progress bar and badges display
feat(gamification): add badge_service with condition checking and XP triggers
feat(gamification): add xp_service with level system from PRD §9.1
feat(gamification): add Badge, UserBadge models and gamification fields to User
```

```powershell
git push origin sprint/4
```

---

## Итоговый отчёт

```
═══════════════════════════════════════════════
 ОТЧЁТ: СПРИНТ 4 — Геймификация и удержание
═══════════════════════════════════════════════

Ветка: sprint/4

4.1 — Модели:
  Badge мигрирована: [✅/❌]  UniqueConstraint user+badge: [✅/❌]
  level/xp/streak в User: [✅/❌]
  seed_badges.py создан: [✅/❌]

4.2 — XPService:
  get_level_for_xp строго по PRD: [✅/❌]
  Unit тесты таблицы уровней: [N passed из 12]
  Все 10 уровней с правильными XP: [✅/❌]
  Скидки (0/0/3/3/7/7/7/12/12/15%): [✅/❌]

4.3 — BadgeService + XP-триггеры:
  _check_condition для 6 типов: [✅/❌]
  XP-триггеры в try/except: [✅/❌]
  Точки: кампания запущена, завершена, размещение, отзыв: [N из 4]

4.4 — Кабинет:
  Прогресс-бар отображается: [✅/❌]
  Значки (до 6): [✅/❌]
  «Все значки» кнопка: [✅/❌]

4.5 — Реферальная программа:
  apply_referral_bonus_advertiser: [✅ реальный / ⚠️ заглушка]
  /start ref_CODE обрабатывается: [✅/❌]
  Реферальный раздел в кабинете: [✅/❌]

4.6 — Celery задачи:
  update_streaks_daily: [✅ в beat]
  send_weekly_digest: [✅ в beat]
  check_seasonal_events: [✅ в beat]

Ruff: [✅/❌]  Mypy: [✅/❌]
Тесты: [N passed, N failed]
Коммитов: [N]/6

Заглушки к доработке: [список]
PR: sprint/4 → develop → main (финальный релиз)
```
