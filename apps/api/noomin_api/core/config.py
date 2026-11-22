from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NOOMIN API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://noomin:noomin@localhost:5432/noomin"
    redis_url: str = "redis://localhost:6379/0"
    celery_task_always_eager: bool = False
    cors_origins: str = "http://localhost:5173"
    jwt_secret_key: str = Field(default="development-only-change-me-use-at-least-32-characters", min_length=32)
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def secure_cookies(self) -> bool:
        return self.environment.lower() not in {"development", "local", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
