from functools import lru_cache

from pydantic import Field, model_validator
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

    @model_validator(mode="after")
    def validate_shared_environment_secrets(self):
        if self.environment.lower() not in {"development", "dev", "local", "test"}:
            lowered_secret = self.jwt_secret_key.lower()
            if any(marker in lowered_secret for marker in ("development-only", "change-this", "dev_only")):
                raise ValueError("JWT_SECRET_KEY doit être remplacé par un secret propre à cet environnement partagé.")
            if "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS doit contenir des origines explicites dans un environnement partagé.")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def secure_cookies(self) -> bool:
        return self.environment.lower() not in {"development", "dev", "local", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
