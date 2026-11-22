from fastapi.testclient import TestClient

from noomin_api.main import app

client = TestClient(app)


def test_health_check_reports_service_status() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "NOOMIN API", "environment": "development"}


def test_root_describes_api_links() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["health"] == "/api/v1/health"
