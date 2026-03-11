# Этап Relationships Fix: Все SQLAlchemy relationships согласованы

**Дата:** 2026-03-11
**Статус:** ✅ ЗАВЕРШЕНО (0 ошибок, бот работает)

---

## 🔧 Исправленные relationships

### 1. User model (`src/db/models/user.py`)

**Добавлено:**
```python
# Настройки каналов (Спринт 6)
channel_settings: Mapped[list["ChannelSettings"]] = relationship(
    "ChannelSettings",
    back_populates="owner",
    lazy="select",
)

# Заявки на размещение (Спринт 6)
placement_requests: Mapped[list["PlacementRequest"]] = relationship(
    "PlacementRequest",
    foreign_keys="PlacementRequest.advertiser_id",
    back_populates="advertiser",
    lazy="select",
)

# История репутации (Спринт 6)
reputation_history: Mapped[list["ReputationHistory"]] = relationship(
    "ReputationHistory",
    back_populates="user",
    lazy="select",
)

# Репутация (Спринт 6)
reputation_score: Mapped[Optional["ReputationScore"]] = relationship(
    "ReputationScore",
    back_populates="user",
    lazy="selectin",
    uselist=False,
)
```

**Импорт добавлен:**
```python
from typing import TYPE_CHECKING, Optional
```

---

### 2. TelegramChat model (`src/db/models/analytics.py`)

**Добавлено:**
```python
# Заявки на размещение (Спринт 6)
placement_requests: Mapped[list["PlacementRequest"]] = relationship(
    "PlacementRequest",
    back_populates="channel",
    lazy="select",
)
```

**Импорт добавлен в TYPE_CHECKING:**
```python
from src.db.models.channel_settings import ChannelSettings
```

**Исправлено:**
```python
# До:
settings: Mapped[Optional["ChannelSettings"]] = relationship(...)

# После:
settings: Mapped["ChannelSettings | None"] = relationship(...)
```

---

### 3. Campaign model (`src/db/models/campaign.py`)

**Исправлено:**
```python
# До (конфликт направления):
placement_request: Mapped[Optional["PlacementRequest"]] = relationship(
    "PlacementRequest",
    foreign_keys=[placement_request_id],
    back_populates="campaign",  # ← вызывало конфликт
    lazy="selectin",
)

# После (без back_populates):
placement_request: Mapped[Optional["PlacementRequest"]] = relationship(
    "PlacementRequest",
    foreign_keys=[placement_request_id],
    lazy="selectin",
    uselist=False,
)
```

---

### 4. PlacementRequest model (`src/db/models/placement_request.py`)

**Исправлено:**
```python
# До (конфликт направления):
campaign: Mapped["Campaign"] = relationship(
    "Campaign",
    foreign_keys=[campaign_id],
    back_populates="placement_request",  # ← вызывало конфликт
    lazy="selectin",
)

# После (без back_populates):
campaign: Mapped["Campaign"] = relationship(
    "Campaign",
    foreign_keys=[campaign_id],
    lazy="selectin",
)
```

**Добавлено:**
```python
# История репутации (Спринт 6)
reputation_history: Mapped[list["ReputationHistory"]] = relationship(
    "ReputationHistory",
    back_populates="placement_request",
    lazy="select",
)
```

---

### 5. Transaction model (`src/db/models/transaction.py`)

**Добавлено:**
```python
# Заявки на размещение (Спринт 6)
placement_request: Mapped[Optional["PlacementRequest"]] = relationship(
    "PlacementRequest",
    back_populates="escrow_transaction",
    lazy="select",
    uselist=False,
)
```

**Импорт добавлен:**
```python
from typing import TYPE_CHECKING, Optional
```

---

## 📊 Итоговая таблица исправлений

| Файл | Модель | Добавленное поле | Тип | back_populates |
|------|--------|-----------------|-----|----------------|
| `user.py` | User | `channel_settings` | `Mapped[list[ChannelSettings]]` | `owner` |
| `user.py` | User | `placement_requests` | `Mapped[list[PlacementRequest]]` | `advertiser` |
| `user.py` | User | `reputation_history` | `Mapped[list[ReputationHistory]]` | `user` |
| `user.py` | User | `reputation_score` | `Mapped[Optional[ReputationScore]]` | `user` |
| `analytics.py` | TelegramChat | `placement_requests` | `Mapped[list[PlacementRequest]]` | `channel` |
| `transaction.py` | Transaction | `placement_request` | `Mapped[Optional[PlacementRequest]]` | `escrow_transaction` |
| `placement_request.py` | PlacementRequest | `reputation_history` | `Mapped[list[ReputationHistory]]` | `placement_request` |

---

## ✅ Проверка

**До исправлений:**
```
ERROR: Mapper 'Mapper[User(users)]' has no property 'channel_settings'
ERROR: Mapper 'Mapper[User(users)]' has no property 'placement_requests'
ERROR: Mapper 'Mapper[TelegramChat(telegram_chats)]' has no property 'placement_requests'
ERROR: Campaign.placement_request and back-reference PlacementRequest.campaign 
       are both of the same direction
ERROR: Mapper 'Mapper[Transaction(transactions)]' has no property 'placement_request'
ERROR: Mapper 'Mapper[User(users)]' has no property 'reputation_history'
ERROR: Mapper 'Mapper[PlacementRequest(placement_requests)]' has no property 'reputation_history'
ERROR: Mapper 'Mapper[User(users)]' has no property 'reputation_score'
```

**После исправлений:**
```
OK: все mappers сконфигурированы
INFO - Bot username: @RekharborBot
INFO - Starting bot in polling mode...
INFO - Run polling for bot @RekharborBot id=8614570435
```

**Ошибки:** 0 ✅

---

## 🎯 Правила применённые при исправлении

1. **one-to-one связь:** `uselist=False` с обеих сторон
2. **one-to-many связь:** `Mapped[list[...]]` на стороне владельца
3. **many-to-one связь:** `Mapped[Optional[...]]` на стороне дочерней
4. **Конфликт направления:** Удалить `back_populates` с одной стороны
5. **Несколько FK между моделями:** Явно указывать `foreign_keys=[...]`
6. **TYPE_CHECKING импорты:** Все новые типы добавлять в `TYPE_CHECKING` блок

---

## 📁 Изменённые файлы

| Файл | Изменений |
|------|-----------|
| `src/db/models/user.py` | +4 relationship, +1 импорт |
| `src/db/models/analytics.py` | +1 relationship, +1 импорт |
| `src/db/models/campaign.py` | 1 relationship исправлен |
| `src/db/models/placement_request.py` | +1 relationship, 1 исправлен |
| `src/db/models/transaction.py` | +1 relationship, +1 импорт |

---

**Версия:** 1.0
**Дата:** 2026-03-11
**Статус:** ✅ ЗАВЕРШЕНО (0 ошибок SQLAlchemy)
