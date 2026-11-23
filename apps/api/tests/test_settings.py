import pytest
from pydantic import ValidationError

from noomin_api.core.config import Settings


def test_shared_environment_rejects_development_jwt_secrets() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(environment="staging", jwt_secret_key="development-only-change-me-use-at-least-32-characters")


def test_shared_environment_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(environment="staging", jwt_secret_key="a" * 48, cors_origins="*")


def test_production_accepts_explicit_origins_and_custom_secret() -> None:
    settings = Settings(
        environment="production",
        jwt_secret_key="random-production-secret-with-over-32-characters",
        cors_origins="https://app.noomin.example",
    )
    assert settings.secure_cookies is True
    assert settings.allowed_origins == ["https://app.noomin.example"]
