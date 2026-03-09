"""
Константы платёжной системы Market Bot.
"""

# Пакеты кредитов: (label, credits, bonus_credits, callback_value)
# Используются в billing.py и billing_service.py
CREDIT_PACKAGES: list[tuple[str, int, int, str]] = [
    ("300 кр", 300, 0, "300"),
    ("600 кр", 600, 0, "600"),
    ("1 200 кр", 1200, 100, "1200"),
    ("3 500 кр", 3500, 500, "3500"),
]

# Бонусные пакеты для разных тарифов
CREDIT_PACKAGE_STANDARD = 100  # Бонус для STANDARD тарифа
CREDIT_PACKAGE_BUSINESS = 500  # Бонус для BUSINESS тарифа

# Поддерживаемые криптовалюты
CURRENCIES: list[str] = ["USDT", "TON", "BTC", "ETH", "LTC"]
CRYPTO_CURRENCIES: list[str] = ["USDT", "TON", "BTC", "ETH", "LTC"]

# Методы оплаты
PAYMENT_METHODS: list[str] = ["cryptobot", "stars"]
