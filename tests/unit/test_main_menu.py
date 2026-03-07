"""Unit тесты роль-зависимого главного меню."""

from src.bot.keyboards.main_menu import (
    get_advertiser_menu_kb,
    get_combined_menu_kb,
    get_main_menu,
    get_onboarding_kb,
    get_owner_menu_kb,
)
from src.core.services.user_role_service import UserContext, UserRole


class TestMenuByRole:
    """Проверить что правильное меню возвращается для каждой роли."""

    def test_new_user_gets_onboarding(self):
        """Новый пользователь → кнопки выбора роли."""
        kb = get_main_menu(credits=0, role="new")
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        # Должны быть кнопки онбординга
        assert any("рекламу" in t or "Telegram-канал" in t for t in buttons_text)
        # НЕ должно быть кнопок рекламодателя/владельца
        assert not any("Создать кампанию" in t for t in buttons_text)
        assert not any("Мои каналы" in t for t in buttons_text)

    def test_advertiser_gets_campaign_buttons(self):
        """Рекламодатель → видит кнопки кампаний."""
        kb = get_main_menu(credits=1000, role="advertiser")
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        assert any("Создать кампанию" in t for t in buttons_text)
        assert any("Мои кампании" in t for t in buttons_text)
        assert any("Каталог каналов" in t for t in buttons_text)
        # НЕ должно быть владельческих кнопок
        assert not any("Мои каналы" in t for t in buttons_text)

    def test_owner_gets_channel_buttons(self):
        """Владелец канала → видит кнопки управления каналами."""
        kb = get_main_menu(credits=500, role="owner")
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        assert any("Мои каналы" in t for t in buttons_text)
        assert any("Заявки" in t for t in buttons_text)
        # НЕ должно быть рекламных кнопок
        assert not any("Создать кампанию" in t for t in buttons_text)

    def test_both_roles_shows_all_sections(self):
        """Обе роли → видны оба раздела."""
        kb = get_main_menu(credits=750, role="both")
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        assert any("Создать кампанию" in t for t in buttons_text)
        assert any("Мои каналы" in t for t in buttons_text)

    def test_pending_badge_shown_for_owner(self):
        """Бейдж с количеством заявок отображается для владельца."""
        kb = get_main_menu(credits=0, role="owner", pending_count=3)
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        assert any("[3]" in t for t in buttons_text)

    def test_no_pending_badge_when_zero(self):
        """Бейдж не показывается если заявок нет."""
        kb = get_main_menu(credits=0, role="owner", pending_count=0)
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        assert not any("[0]" in t for t in buttons_text)

    def test_credits_shown_in_cabinet_button(self):
        """Баланс отображается в кнопке кабинета."""
        kb = get_main_menu(credits=1234, role="advertiser")
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        assert any("1 234" in t or "1234" in t for t in buttons_text)

    def test_admin_button_shown_for_admin(self):
        """Кнопка Админ видна администраторам."""
        from src.config.settings import settings

        admin_id = settings.admin_ids[0] if settings.admin_ids else None
        if admin_id:
            kb = get_main_menu(credits=0, role="advertiser", user_id=admin_id)
            buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]
            assert any("Админ" in t for t in buttons_text)

    def test_admin_button_hidden_for_regular_user(self):
        """Кнопка Админ скрыта для обычных пользователей."""
        kb = get_main_menu(credits=0, role="advertiser", user_id=999999999)
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        assert not any("Админ" in t for t in buttons_text)


class TestOnboardingKeyboard:
    """Тесты онбординг клавиатуры."""

    def test_onboarding_has_advertiser_option(self):
        """Онбординг должен иметь кнопку «Хочу размещать рекламу»."""
        kb = get_onboarding_kb()
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        assert any("рекламу" in t for t in buttons_text)

    def test_onboarding_has_owner_option(self):
        """Онбординг должен иметь кнопку «У меня есть Telegram-канал»."""
        kb = get_onboarding_kb()
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        assert any("Telegram-канал" in t for t in buttons_text)

    def test_onboarding_has_platform_stats(self):
        """Онбординг должен иметь кнопку «Посмотреть статистику платформы»."""
        kb = get_onboarding_kb()
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        assert any("статистику" in t or "платформу" in t for t in buttons_text)


class TestAdvertiserKeyboard:
    """Тесты клавиатуры рекламодателя."""

    def test_advertiser_menu_layout(self):
        """Проверка раскладки меню рекламодателя."""
        kb = get_advertiser_menu_kb(credits=100)
        rows = kb.inline_keyboard

        # Проверяем что есть хотя бы 3 ряда
        assert len(rows) >= 3

    def test_advertiser_cabinet_button_format(self):
        """Кнопка кабинета должна содержать баланс в кредитах."""
        kb = get_advertiser_menu_kb(credits=500)
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        cabinet_button = next((t for t in buttons_text if "Кабинет" in t), None)
        assert cabinet_button is not None
        assert "500" in cabinet_button
        assert "кр" in cabinet_button


class TestOwnerKeyboard:
    """Тесты клавиатуры владельца канала."""

    def test_owner_menu_layout(self):
        """Проверка раскладки меню владельца."""
        kb = get_owner_menu_kb(credits=100)
        rows = kb.inline_keyboard

        # Проверяем что есть хотя бы 3 ряда
        assert len(rows) >= 3

    def test_owner_requests_badge_format(self):
        """Бейдж заявок должен быть в правильном формате."""
        kb = get_owner_menu_kb(credits=100, pending_count=5)
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        requests_button = next((t for t in buttons_text if "Заявки" in t), None)
        assert requests_button is not None
        assert "[5]" in requests_button

    def test_owner_no_requests_badge_when_zero(self):
        """Бейдж не должен показывать [0]."""
        kb = get_owner_menu_kb(credits=100, pending_count=0)
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        requests_button = next((t for t in buttons_text if "Заявки" in t), None)
        assert requests_button is not None
        assert "[0]" not in requests_button


class TestCombinedKeyboard:
    """Тесты комбинированной клавиатуры."""

    def test_combined_menu_has_two_sections(self):
        """Комбинированное меню должно иметь два раздела."""
        kb = get_combined_menu_kb(credits=100)
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        # Проверяем наличие разделителей
        assert any("Реклама" in t for t in buttons_text)
        assert any("Мой канал" in t for t in buttons_text)

    def test_combined_menu_advertiser_buttons(self):
        """Комбинированное меню должно иметь кнопки рекламодателя."""
        kb = get_combined_menu_kb(credits=100)
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        assert any("Создать кампанию" in t for t in buttons_text)
        assert any("Мои кампании" in t for t in buttons_text)

    def test_combined_menu_owner_buttons(self):
        """Комбинированное меню должно иметь кнопки владельца."""
        kb = get_combined_menu_kb(credits=100)
        buttons_text = [btn.text for row in kb.inline_keyboard for btn in row]

        assert any("Мои каналы" in t for t in buttons_text)
        assert any("Заявки" in t for t in buttons_text)


class TestUserRoleEnum:
    """Тесты перечисления UserRole."""

    def test_user_role_values(self):
        """Проверка значений UserRole."""
        assert UserRole.NEW.value == "new"
        assert UserRole.ADVERTISER.value == "advertiser"
        assert UserRole.OWNER.value == "owner"
        assert UserRole.BOTH.value == "both"


class TestUserContext:
    """Тесты dataclass UserContext."""

    def test_user_context_creation(self):
        """Создание UserContext с правильными значениями."""
        ctx = UserContext(
            role=UserRole.ADVERTISER,
            pending_requests_count=0,
            credits=1000,
            has_channels=False,
            has_campaigns=True,
        )

        assert ctx.role == UserRole.ADVERTISER
        assert ctx.pending_requests_count == 0
        assert ctx.credits == 1000
        assert ctx.has_channels is False
        assert ctx.has_campaigns is True

    def test_user_context_with_pending_requests(self):
        """UserContext с ожидающими заявками."""
        ctx = UserContext(
            role=UserRole.OWNER,
            pending_requests_count=5,
            credits=500,
            has_channels=True,
            has_campaigns=False,
        )

        assert ctx.role == UserRole.OWNER
        assert ctx.pending_requests_count == 5
