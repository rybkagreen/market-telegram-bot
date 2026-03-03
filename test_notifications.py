"""
Тестирование нововведений: уведомления пользователей.
Запускается внутри контейнера bot.
"""

import asyncio
import sys

# Тест 1: Проверка модели User
print("=" * 60)
print("ТЕСТ 1: Проверка модели User.notifications_enabled")
print("=" * 60)

from src.db.models.user import User

assert hasattr(User, 'notifications_enabled'), "❌ У User нет поля notifications_enabled"
print(f"✅ Поле notifications_enabled существует: {User.notifications_enabled}")
print(f"   Default: {User.notifications_enabled.default.arg}")
print(f"   Server default: {User.notifications_enabled.server_default.arg}")

# Тест 2: Проверка UserRepository методов
print("\n" + "=" * 60)
print("ТЕСТ 2: Проверка UserRepository методов")
print("=" * 60)

from src.db.repositories.user_repo import UserRepository

assert hasattr(UserRepository, 'toggle_notifications'), "❌ Нет метода toggle_notifications"
assert hasattr(UserRepository, 'toggle_notifications_by_db_id'), "❌ Нет метода toggle_notifications_by_db_id"
print("✅ Метод toggle_notifications существует")
print("✅ Метод toggle_notifications_by_db_id существует")

# Тест 3: Проверка клавиатур
print("\n" + "=" * 60)
print("ТЕСТ 3: Проверка клавиатур кабинета")
print("=" * 60)

from src.bot.keyboards.cabinet import CabinetCB, get_cabinet_kb, get_notifications_prompt_kb

# Проверка CabinetCB
cb = CabinetCB(action="toggle_notifications")
print(f"✅ CabinetCB создан: prefix={cb.prefix}, action={cb.action}")

# Проверка get_cabinet_kb
kb_enabled = get_cabinet_kb(notifications_enabled=True)
kb_disabled = get_cabinet_kb(notifications_enabled=False)
print(f"✅ get_cabinet_kb(True): {len(kb_enabled.inline_keyboard)} рядов кнопок")
print(f"✅ get_cabinet_kb(False): {len(kb_disabled.inline_keyboard)} рядов кнопок")

# Проверка get_notifications_prompt_kb
prompt_kb = get_notifications_prompt_kb()
print(f"✅ get_notifications_prompt_kb: {len(prompt_kb.inline_keyboard)} рядов кнопок")

# Тест 4: Проверка keyboard admin
print("\n" + "=" * 60)
print("ТЕСТ 4: Проверка клавиатуры админа")
print("=" * 60)

from src.bot.keyboards.admin import get_user_actions_kb

admin_kb = get_user_actions_kb(user_id=1, is_banned=False, notifications_enabled=True)
print(f"✅ get_user_actions_kb с notifications_enabled: {len(admin_kb.inline_keyboard)} рядов")

admin_kb2 = get_user_actions_kb(user_id=1, is_banned=False, notifications_enabled=False)
print(f"✅ get_user_actions_kb без notifications_enabled: {len(admin_kb2.inline_keyboard)} рядов")

# Тест 5: Проверка notification_tasks
print("\n" + "=" * 60)
print("ТЕСТ 5: Проверка notification_tasks")
print("=" * 60)

from src.tasks.notification_tasks import notify_campaign_status, _get_campaign_message

# Проверка функции получения сообщения
msg = _get_campaign_message(campaign_id=123, status="completed")
print(f"✅ _get_campaign_message для 'completed': {msg[:50]}...")

msg_paused = _get_campaign_message(campaign_id=123, status="paused")
print(f"✅ _get_campaign_message для 'paused': {msg_paused[:50]}...")

# Тест 6: Проверка campaigns.py
print("\n" + "=" * 60)
print("ТЕСТ 6: Проверка campaigns.py")
print("=" * 60)

from src.bot.handlers.campaigns import confirm_launch, _do_launch_campaign, enable_notif_and_launch, launch_without_notif

print("✅ confirm_launch импортирован")
print("✅ _do_launch_campaign импортирован")
print("✅ enable_notif_and_launch импортирован")
print("✅ launch_without_notif импортирован")

# Тест 7: Проверка cabinet.py handlers
print("\n" + "=" * 60)
print("ТЕСТ 7: Проверка cabinet.py handlers")
print("=" * 60)

from src.bot.handlers.cabinet import toggle_notifications_handler, show_cabinet

print("✅ toggle_notifications_handler импортирован")
print("✅ show_cabinet импортирован")

# Тест 8: Проверка admin.py handlers
print("\n" + "=" * 60)
print("ТЕСТ 8: Проверка admin.py handlers")
print("=" * 60)

from src.bot.handlers.admin import admin_toggle_user_notif, handle_toggle_ban

print("✅ admin_toggle_user_notif импортирован")
print("✅ handle_toggle_ban импортирован")

# Тест 9: Проверка миграции
print("\n" + "=" * 60)
print("ТЕСТ 9: Проверка миграции")
print("=" * 60)

from src.db.session import async_session_factory
from sqlalchemy import inspect

async def check_migration():
    async with async_session_factory() as session:
        # Проверка что колонка существует через raw SQL
        from sqlalchemy import text
        result = await session.execute(
            text("""
                SELECT column_name, data_type, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'notifications_enabled'
            """)
        )
        row = result.fetchone()
        if row:
            print(f"✅ Колонка notifications_enabled существует в БД")
            print(f"   Тип: {row.data_type}")
            print(f"   Default: {row.column_default}")
        else:
            print("❌ Колонка notifications_enabled НЕ найдена в БД")
            return False
    return True

migration_ok = asyncio.run(check_migration())

# Тест 10: Тест toggle_notifications
print("\n" + "=" * 60)
print("ТЕСТ 10: Тест toggle_notifications (на тестовом пользователе)")
print("=" * 60)

async def test_toggle():
    async with async_session_factory() as session:
        user_repo = UserRepository(session)
        
        # Найдем первого пользователя (админа)
        from sqlalchemy import select
        from src.db.models.user import User as UserModel
        result = await session.execute(select(UserModel).limit(1))
        user = result.scalar_one_or_none()
        
        if user:
            print(f"✅ Тестовый пользователь: {user.telegram_id} (@{user.username})")
            print(f"   notifications_enabled до: {user.notifications_enabled}")
            
            # Переключаем
            new_state = await user_repo.toggle_notifications(user.id)
            print(f"   notifications_enabled после toggle: {new_state}")
            
            # Переключаем обратно
            new_state2 = await user_repo.toggle_notifications(user.id)
            print(f"   notifications_enabled после второго toggle: {new_state2}")
            
            # Проверяем что состояние вернулось
            assert new_state2 == user.notifications_enabled, "❌ Состояние не совпадает"
            print("✅ toggle_notifications работает корректно")
            
            await session.commit()
            return True
        else:
            print("❌ Нет пользователей в БД для теста")
            return False

toggle_ok = asyncio.run(test_toggle())

# Итоги
print("\n" + "=" * 60)
print("ИТОГИ ТЕСТИРОВАНИЯ")
print("=" * 60)

all_tests = [
    ("Модель User", True),
    ("UserRepository методы", True),
    ("Клавиатуры cabinet", True),
    ("Клавиатура admin", True),
    ("Notification tasks", True),
    ("Campaigns handlers", True),
    ("Cabinet handlers", True),
    ("Admin handlers", True),
    ("Миграция БД", migration_ok),
    ("Toggle notifications", toggle_ok),
]

passed = sum(1 for _, ok in all_tests if ok)
total = len(all_tests)

for test_name, ok in all_tests:
    status = "✅ PASS" if ok else "❌ FAIL"
    print(f"{status}: {test_name}")

print(f"\nРезультат: {passed}/{total} тестов пройдено")

if passed == total:
    print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    sys.exit(0)
else:
    print(f"\n⚠️ {total - passed} тестов не пройдено")
    sys.exit(1)
