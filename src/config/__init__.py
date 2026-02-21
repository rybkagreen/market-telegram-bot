from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram Bot
    bot_token: str = ""

    # PostgreSQL
    postgres_user: str = "market_bot"
    postgres_password: str = "market_bot_pass"
    postgres_db: str = "market_bot_db"
    postgres_port: int = 5432
    database_url: str = ""

    # Redis
    redis_port: int = 6379
    redis_url: str = ""

    # Celery
    celery_broker_url: str = ""
    celery_result_backend: str = ""

    # Ports
    api_port: int = 8000
    flower_port: int = 5555
    nginx_port: int = 80

    # Environment
    environment: str = "development"
    debug: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
