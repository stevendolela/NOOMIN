from fastapi import APIRouter, Response, status
from redis import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from noomin_api.core.config import get_settings
from noomin_api.schemas.health import HealthResponse
from noomin_api.db.session import engine

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(response: Response) -> HealthResponse:
    settings = get_settings()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unavailable", service=settings.app_name, environment=settings.environment)
    return HealthResponse(status="ok", service=settings.app_name, environment=settings.environment)


@router.get("/ready", response_model=HealthResponse)
def readiness_check(response: Response) -> HealthResponse:
    """Report ready only when both the database and Redis accept connections."""
    settings = get_settings()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        try:
            redis_client.ping()
        finally:
            redis_client.close()
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="unavailable", service=settings.app_name, environment=settings.environment)
    return HealthResponse(status="ok", service=settings.app_name, environment=settings.environment)
