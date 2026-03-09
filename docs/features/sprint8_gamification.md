# 📋 СПРИНТ 8: ГЕЙМИФИКАЦИЯ (P2)

## ОБЗОР СПРИНТА

**Цель:** Реализовать автоматическую систему достижений и значков, завершить систему стриков активности.

**Срок:** 5-7 дней  
**Приоритет:** P2 (средний)  
**Зависимости:** Спринт 4 (базовая модель UserBadge), Спринт 5 (XP система)

---

## 📦 ЗАДАЧИ СПРИНТА

| № | Задача | Приоритет | Оценка | Статус |
|---|--------|-----------|--------|--------|
| 8.1 | Модели BadgeAchievement (триггеры достижений) | P2 | 4ч | ⏳ |
| 8.2 | Сервис badge_service: check_achievements() | P2 | 6ч | ⏳ |
| 8.3 | Celery задачи: badge_tasks.py | P2 | 4ч | ⏳ |
| 8.4 | Триггер: "Первая кампания" | P2 | 2ч | ⏳ |
| 8.5 | Триггер: "100 размещений" | P2 | 2ч | ⏳ |
| 8.6 | Триггер: "Топ рекламодатель" | P3 | 2ч | ⏳ |
| 8.7 | Стрики в /cabinet + прогресс-бар | P2 | 3ч | ⏳ |
| 8.8 | Бонусы за стрики (кредиты/XP) | P3 | 3ч | ⏳ |
| 8.9 | Уведомление о получении значка | P2 | 2ч | ⏳ |
| 8.10 | Alembic миграции | P1 | 1ч | ⏳ |

---

## 🔧 ЗАДАЧА 8.1: Модели BadgeAchievement

**Файл:** `src/db/models/badge.py` (расширение)

### Что добавить:

```python
class BadgeAchievement(Base, TimestampMixin):
    """
    Шаблоны достижений для автоматического начисления значков.
    
    Примеры:
    - "first_campaign" → Первая кампания
    - "100_placements" → 100 успешных размещений
    - "streak_7_days" → 7 дней стрика
    - "top_advertiser" → Топ-10 рекламодателей месяца
    """
    __tablename__ = "badge_achievements"
    
    id: Mapped[int] = primary_key
    badge_id: Mapped[int] = ForeignKey("badges.id")  # Какой значок выдавать
    achievement_type: Mapped[str]  # "campaign_count", "placement_count", "streak_days", "xp_level"
    threshold: Mapped[int]  # Порог срабатывания (например, 100 размещений)
    description: Mapped[str]  # Описание достижения
    is_active: Mapped[bool] = True  # Включено ли достижение
```

### Новая модель Badge (расширение):

```python
class Badge(Base, TimestampMixin):
    __tablename__ = "badges"
    
    id: Mapped[int] = primary_key
    name: Mapped[str]  # "Первая кампания"
    description: Mapped[str]  # "Запуск первой рекламной кампании"
    icon_emoji: Mapped[str]  # "🚀"
    xp_reward: Mapped[int]  # 50 XP
    credits_reward: Mapped[int] = 0  # Бонус кредитами (опционально)
    category: Mapped[str]  # "campaign", "streak", "placement", "level"
    is_rare: Mapped[bool] = False  # Редкий значок
```

**Миграция:** `src/db/migrations/versions/202603XX_0012_add_badge_achievements.py`

---

## 🔧 ЗАДАЧА 8.2: Сервис badge_service

**Файл:** `src/core/services/badge_service.py` (расширение)

### Методы для добавления:

```python
class BadgeService:
    async def check_achievements(self, user_id: int) -> list[UserBadge]:
        """
        Проверить все достижения пользователя и выдать новые значки.
        
        Возвращает список newly earned badges.
        """
        
    async def award_badge(self, user_id: int, badge_id: int, 
                         reason: str) -> UserBadge | None:
        """
        Выдать значок пользователю.
        
        Проверяет что значок ещё не выдан.
        Создаёт UserBadge запись.
        Начисляет XP и кредиты.
        """
        
    async def get_available_badges(self, user_id: int) -> list[dict]:
        """
        Получить список всех доступных значков с прогрессом.
        
        Returns:
            [{"badge": ..., "progress": 0.75, "earned": False}, ...]
        """
```

---

## 🔧 ЗАДАЧА 8.3: Celery задачи badge_tasks

**Файл:** `src/tasks/badge_tasks.py` (новый)

### Задачи:

```python
@celery_app.task(name="badges:check_user_achievements")
def check_user_achievements(user_id: int) -> dict:
    """
    Проверить достижения конкретного пользователя.
    Вызывается после ключевых событий.
    """

@celery_app.task(name="badges:daily_badge_check")
def daily_badge_check() -> dict:
    """
    Ежедневная проверка достижений всех активных пользователей.
    Запуск: каждый день в 00:00 UTC.
    """

@celery_app.task(name="badges:notify_badge_earned")
def notify_badge_earned(user_id: int, badge_id: int) -> bool:
    """
    Отправить уведомление о получении значка.
    """
```

### Beat расписание (celery_config.py):

```python
"daily-badge-check": {
    "task": "src.tasks.badge_tasks.daily_badge_check",
    "schedule": crontab(hour=0, minute=0),
    "options": {"queue": "gamification"},
},
```

---

## 🔧 ЗАДАЧА 8.4: Триггер "Первая кампания"

**Файл:** `src/bot/handlers/campaigns.py` (расширение)

### Где вызвать:

```python
# В confirm_launch() после успешного запуска кампании
from src.tasks.badge_tasks import check_user_achievements

# После создания кампании
check_user_achievements.delay(user.id)
```

### Достижение в БД:

```python
# BadgeAchievement запись:
{
    "badge_id": 1,  # "Первая кампания" 🚀
    "achievement_type": "campaign_count",
    "threshold": 1,
    "description": "Запуск первой рекламной кампании",
    "is_active": True
}
```

---

## 🔧 ЗАДАЧА 8.5: Триггер "100 размещений"

**Файл:** `src/tasks/mailing_tasks.py` (расширение)

### Где вызвать:

```python
# В send_campaign() после завершения рассылки
# После обновления статистики кампании

from src.tasks.badge_tasks import check_user_achievements

# Для каждого пользователя у которого кампания завершилась
check_user_achievements.delay(campaign.user_id)
```

### Достижение в БД:

```python
{
    "badge_id": 2,  # "100 размещений" 💯
    "achievement_type": "placement_count",
    "threshold": 100,
    "description": "100 успешных публикаций",
    "is_active": True
}
```

---

## 🔧 ЗАДАЧА 8.6: Триггер "Топ рекламодатель"

**Файл:** `src/tasks/badge_tasks.py` (расширение)

### Логика:

```python
async def check_top_advertisers() -> list[int]:
    """
    Получить топ-10 рекламодателей месяца.
    
    Считает sum(campaign.cost) за текущий месяц.
    Возвращает список user_id.
    """

@celery_app.task(name="badges:monthly_top_advertisers")
def monthly_top_advertisers() -> dict:
    """
    Проверка топ рекламодателей.
    Запуск: 1-го числа каждого месяца в 00:00 UTC.
    """
```

### Достижение в БД:

```python
{
    "badge_id": 3,  # "Топ рекламодатель" 👑
    "achievement_type": "top_advertiser_monthly",
    "threshold": 10,  # Топ-10
    "description": "Вход в топ-10 рекламодателей месяца",
    "is_active": True
}
```

---

## 🔧 ЗАДАЧА 8.7: Стрики в /cabinet

**Файл:** `src/bot/handlers/cabinet.py` (расширение)

### Обновить текст кабинета:

```python
# Для advertiser роли
text += (
    f"\n━━━━ СТРИКИ ━━━━\n"
    f"🔥 <b>Текущая серия:</b> {user.login_streak_days} дн.\n"
    f"📈 <b>Максимальная:</b> {user.max_streak_days} дн.\n"
)

# Прогресс-бар до следующего бонуса
streak_progress = user.login_streak_days % 7  # Бонус каждые 7 дней
streak_bar = "█" * streak_progress + "░" * (7 - streak_progress)
text += f"   {streak_bar}  до бонуса: {7 - streak_progress} дн.\n"
```

### Клавиатура:

```python
builder.button(
    text="🔥 Стрик: {user.login_streak_days} дн.",
    callback_data=CabinetCB(action="streaks"),
)
```

---

## 🔧 ЗАДАЧА 8.8: Бонусы за стрики

**Файл:** `src/core/services/xp_service.py` (расширение)

### Метод:

```python
async def award_streak_bonus(self, user_id: int, streak_days: int) -> dict:
    """
    Начислить бонус за стрик активности.
    
    Бонусы:
    - 7 дней: +50 XP + 10 кредитов
    - 14 дней: +100 XP + 25 кредитов
    - 30 дней: +300 XP + 100 кредитов + значок
    - 100 дней: +1000 XP + 500 кредитов + редкий значок
    """
    
    bonuses = {
        7: {"xp": 50, "credits": 10, "badge_id": None},
        14: {"xp": 100, "credits": 25, "badge_id": None},
        30: {"xp": 300, "credits": 100, "badge_id": 4},  # "Месяц активности"
        100: {"xp": 1000, "credits": 500, "badge_id": 5},  # "100 дней" (редкий)
    }
    
    if streak_days in bonuses:
        bonus = bonuses[streak_days]
        # Начислить XP
        await self.add_xp(user_id, bonus["xp"], reason=f"streak_{streak_days}")
        # Начислить кредиты
        await user_repo.update_credits(user_id, bonus["credits"])
        # Выдать значок если есть
        if bonus["badge_id"]:
            await badge_service.award_badge(user_id, bonus["badge_id"], 
                                           f"streak_{streak_days}_days")
```

---

## 🔧 ЗАДАЧА 8.9: Уведомление о значке

**Файл:** `src/tasks/notification_tasks.py` (расширение)

### Функция:

```python
@celery_app.task(name="notifications:notify_badge_earned")
def notify_badge_earned(user_id: int, badge_name: str, badge_emoji: str, 
                       xp_reward: int, credits_reward: int) -> bool:
    """
    Отправить красивое уведомление о получении значка.
    """
    
    message = (
        f"🏅 <b>Новый значок!</b>\n\n"
        f"{badge_emoji} <b>{badge_name}</b>\n\n"
    )
    
    if xp_reward > 0:
        message += f"+{xp_reward} XP\n"
    if credits_reward > 0:
        message += f"+{credits_reward} кр\n"
    
    message += "\nПоздравляем с достижением!"
    
    # Отправить через bot.send_message
```

---

## 🔧 ЗАДАЧА 8.10: Alembic миграции

**Файл:** `src/db/migrations/versions/202603XX_0012_add_badge_achievements.py`

### Migration:

```python
def upgrade() -> None:
    # Таблица достижений
    op.create_table('badge_achievements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('badge_id', sa.Integer(), nullable=False),
        sa.Column('achievement_type', sa.String(50), nullable=False),
        sa.Column('threshold', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(['badge_id'], ['badges.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Индексы
    op.create_index('ix_badge_achievements_type', 'badge_achievements', ['achievement_type'])
    op.create_index('ix_badge_achievements_active', 'badge_achievements', ['is_active'])
    
    # Данные по умолчанию
    op.bulk_insert(badge_achievements_table, [
        {
            "badge_id": 1,
            "achievement_type": "campaign_count",
            "threshold": 1,
            "description": "Запуск первой рекламной кампании",
            "is_active": True
        },
        {
            "badge_id": 2,
            "achievement_type": "placement_count",
            "threshold": 100,
            "description": "100 успешных публикаций",
            "is_active": True
        },
        # ... другие достижения
    ])

def downgrade() -> None:
    op.drop_table('badge_achievements')
```

---

## 📊 ПОРЯДОК ВЫПОЛНЕНИЯ

```
День 1: Задачи 8.1, 8.10 (модели + миграции)
День 2: Задача 8.2 (badge_service)
День 3: Задача 8.3 (Celery задачи)
День 4: Задачи 8.4, 8.5 (триггеры кампаний)
День 5: Задачи 8.6, 8.7, 8.8 (топ + стрики + бонусы)
День 6: Задача 8.9 (уведомления) + тестирование
День 7: Фикс багов + документация
```

---

## ✅ КРИТЕРИИ ПРИЁМКИ

### Задача 8.1-8.3 (Базовая инфраструктура):
- [ ] Миграция применена (`alembic current` показывает head)
- [ ] `badge_service.check_achievements()` проверяет все типы достижений
- [ ] Celery задача запускается по расписанию

### Задача 8.4-8.6 (Триггеры):
- [ ] После первой кампании → значок "Первая кампания"
- [ ] После 100 размещений → значок "100 размещений"
- [ ] 1-го числа → проверка топ рекламодателей

### Задача 8.7-8.8 (Стрики):
- [ ] В /cabinet отображается текущий стрик
- [ ] Прогресс-бар до следующего бонуса
- [ ] Бонусы начисляются автоматически (7/14/30/100 дней)

### Задача 8.9 (Уведомления):
- [ ] Пользователь получает уведомление сразу после получения значка
- [ ] Уведомление содержит: название, emoji, XP, кредиты

---

## 📁 ИТОГОВЫЙ СПИСОК ФАЙЛОВ

### Новые файлы:
```
src/db/models/badge.py              (расширение)
src/tasks/badge_tasks.py            (новый)
src/db/migrations/versions/202603XX_0012_add_badge_achievements.py
```

### Изменённые файлы:
```
src/core/services/badge_service.py  (расширение)
src/core/services/xp_service.py     (бонусы за стрики)
src/bot/handlers/cabinet.py         (отображение стриков)
src/bot/handlers/campaigns.py       (триггер первой кампании)
src/tasks/mailing_tasks.py          (триггер размещений)
src/tasks/notification_tasks.py     (уведомления о значках)
src/tasks/celery_config.py          (Beat расписание)
```

---

## 🎯 СВЯЗАННЫЕ ЗАДАЧИ ИЗ PREVIOUS SPRINTS

- **Спринт 4:** Базовая модель UserBadge ✅
- **Спринт 5:** XP система (advertiser_xp, owner_xp) ✅
- **Спринт 3:** Стрики активности (login_streak_days) ✅

---

**Готов приступить к реализации Спринта 8. С какой задачи начать?**
