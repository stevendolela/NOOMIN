from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from noomin_api.main import app

client = TestClient(app)


def test_health_check_reports_service_status(monkeypatch) -> None:
    from noomin_api.api import health

    monkeypatch.setattr(health, "engine", create_engine("sqlite://", poolclass=StaticPool))
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "NOOMIN API", "environment": "development"}


def test_health_check_reports_database_failure(monkeypatch) -> None:
    from noomin_api.api import health

    monkeypatch.setattr(health, "engine", create_engine("postgresql+psycopg://bad:bad@127.0.0.1:1/noomin", connect_args={"connect_timeout": 1}))
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


def test_readiness_requires_database_and_redis(monkeypatch) -> None:
    from noomin_api.api import health

    monkeypatch.setattr(health, "engine", create_engine("sqlite://", poolclass=StaticPool))

    class AvailableRedis:
        def ping(self):
            return True

        def close(self):
            return None

    monkeypatch.setattr(health.Redis, "from_url", lambda *args, **kwargs: AvailableRedis())
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    class UnavailableRedis:
        def ping(self):
            raise ConnectionError("Redis unavailable")

        def close(self):
            return None

    monkeypatch.setattr(health.Redis, "from_url", lambda *args, **kwargs: UnavailableRedis())
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


def test_root_describes_api_links() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["health"] == "/api/v1/health"
