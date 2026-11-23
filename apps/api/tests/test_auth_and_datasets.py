import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from noomin_api.db.base import Base
from noomin_api.db.session import get_db
from noomin_api.main import app


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.state.test_session_factory = TestingSession
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def create_account(client: TestClient, email: str = "camille@example.com") -> dict:
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "full_name": "Camille Martin",
        "organization_name": "Acme Studio",
        "password": "correct-horse-2026!",
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_registration_creates_owner_session_and_rejects_duplicate(client: TestClient) -> None:
    session = create_account(client)
    assert session["user"]["email"] == "camille@example.com"
    assert session["organizations"][0]["role"] == "owner"
    assert "session" in client.cookies
    assert client.get("/api/v1/auth/session").status_code == 200
    duplicate = client.post("/api/v1/auth/register", json={
        "email": "CAMILLE@example.com",
        "full_name": "Camille Martin",
        "organization_name": "Other Studio",
        "password": "correct-horse-2026!",
    })
    assert duplicate.status_code == 409


def test_login_sets_session_and_logout_clears_it(client: TestClient) -> None:
    create_account(client)
    old_cookie = client.cookies.get("session")
    client.post("/api/v1/auth/logout")
    revoked_client = TestClient(app)
    revoked_client.cookies.set("session", old_cookie)
    assert revoked_client.get("/api/v1/auth/session").status_code == 401
    response = client.post("/api/v1/auth/login", json={"email": "camille@example.com", "password": "correct-horse-2026!"})
    assert response.status_code == 200
    assert client.get("/api/v1/auth/session").status_code == 200
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/auth/session").status_code == 401


def test_csv_import_persists_rows_and_scopes_them_to_organization(client: TestClient) -> None:
    session = create_account(client)
    organization_id = session["organizations"][0]["id"]
    response = client.post(
        "/api/v1/datasets",
        headers={"X-Organization-ID": organization_id},
        files={"file": ("revenus.csv", "jour,montant\n2026-01-01,12.5\n2026-01-02,15.0\n", "text/csv")},
    )
    assert response.status_code == 201, response.text
    dataset = response.json()
    assert dataset["row_count"] == 2
    assert dataset["column_count"] == 2
    assert client.get("/api/v1/datasets", headers={"X-Organization-ID": organization_id}).json()[0]["id"] == dataset["id"]
    detail = client.get(f"/api/v1/datasets/{dataset['id']}", headers={"X-Organization-ID": organization_id})
    assert detail.json()["preview"][1] == {"jour": "2026-01-02", "montant": "15.0"}
    profile = client.get(f"/api/v1/datasets/{dataset['id']}/profile", headers={"X-Organization-ID": organization_id})
    amount = next(column for column in profile.json()["columns"] if column["name"] == "montant")
    assert amount["data_type"] == "number"
    assert amount["minimum"] == 12.5 and amount["maximum"] == 15.0
    assert sum(item["count"] for item in amount["distribution"]) == 2


def test_csv_import_rejects_duplicate_columns(client: TestClient) -> None:
    session = create_account(client)
    response = client.post(
        "/api/v1/datasets",
        headers={"X-Organization-ID": session["organizations"][0]["id"]},
        files={"file": ("invalid.csv", "amount,amount\n1,2\n", "text/csv")},
    )
    assert response.status_code == 400
    assert "uniques" in response.json()["detail"]


def test_csv_import_detects_semicolon_delimiter_and_quoted_values(client: TestClient) -> None:
    session = create_account(client)
    response = client.post(
        "/api/v1/datasets",
        headers={"X-Organization-ID": session["organizations"][0]["id"]},
        files={"file": ("candidats.csv", 'NOM;CIRCONSCRIPTION;NOTES\n"Durand, Léa";"Paris;Centre";12\n', "text/csv")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["columns"] == ["NOM", "CIRCONSCRIPTION", "NOTES"]
    detail = client.get(
        f"/api/v1/datasets/{response.json()['id']}",
        headers={"X-Organization-ID": session["organizations"][0]["id"]},
    )
    assert detail.json()["preview"] == [{"NOM": "Durand, Léa", "CIRCONSCRIPTION": "Paris;Centre", "NOTES": "12"}]


def test_dataset_is_not_visible_to_another_organization(client: TestClient) -> None:
    first = create_account(client)
    first_org = first["organizations"][0]["id"]
    uploaded = client.post(
        "/api/v1/datasets",
        headers={"X-Organization-ID": first_org},
        files={"file": ("private.csv", "value\nsecret\n", "text/csv")},
    )
    assert uploaded.status_code == 201
    other_client = TestClient(app)
    second = create_account(other_client, "alex@example.com")
    response = other_client.get("/api/v1/datasets", headers={"X-Organization-ID": first_org})
    assert response.status_code == 403
    assert second["organizations"][0]["id"] != first_org


def test_celery_pipeline_filters_and_creates_a_new_dataset(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from noomin_api.api import pipelines as pipeline_api
    from noomin_api.tasks import execute_pipeline_job

    session = create_account(client)
    organization_id = session["organizations"][0]["id"]
    source_response = client.post(
        "/api/v1/datasets",
        headers={"X-Organization-ID": organization_id},
        files={"file": ("sales.csv", "date,revenue\n2026-01-01,10\n2026-01-02,25\n2026-01-03,50\n", "text/csv")},
    )
    assert source_response.status_code == 201
    source_id = source_response.json()["id"]
    invalid = client.post("/api/v1/pipelines", headers={"X-Organization-ID": organization_id}, json={
        "name": "Filtre invalide",
        "source_dataset_id": source_id,
        "steps": [{"op": "filter_rows", "column": "revenue", "operator": "greater_than", "value": "NaN"}],
    })
    assert invalid.status_code == 422
    created = client.post("/api/v1/pipelines", headers={"X-Organization-ID": organization_id}, json={
        "name": "Ventes importantes",
        "source_dataset_id": source_id,
        "steps": [
            {"op": "filter_rows", "column": "revenue", "operator": "greater_than", "value": "20"},
            {"op": "select_columns", "columns": ["date", "revenue"]},
            {"op": "rename_columns", "mapping": {"revenue": "revenue_selected"}},
        ],
    })
    assert created.status_code == 201, created.text
    pipeline_id = created.json()["id"]
    monkeypatch.setattr(pipeline_api.execute_pipeline, "apply_async", lambda *_args, **_kwargs: None)
    queued = client.post(f"/api/v1/pipelines/{pipeline_id}/runs", headers={"X-Organization-ID": organization_id})
    assert queued.status_code == 202, queued.text
    execute_pipeline_job(queued.json()["id"], session_factory=client.app.state.test_session_factory)
    completed = client.get(f"/api/v1/pipelines/{pipeline_id}", headers={"X-Organization-ID": organization_id}).json()["last_run"]
    assert completed["status"] == "succeeded"
    output = client.get(f"/api/v1/datasets/{completed['output_dataset_id']}", headers={"X-Organization-ID": organization_id})
    assert output.status_code == 200
    assert output.json()["row_count"] == 2
    assert output.json()["columns"] == ["date", "revenue_selected"]
    assert output.json()["preview"][0] == {"date": "2026-01-02", "revenue_selected": "25"}


def test_numeric_analysis_is_saved_and_scoped_to_organization(client: TestClient) -> None:
    session = create_account(client)
    organization_id = session["organizations"][0]["id"]
    uploaded = client.post(
        "/api/v1/datasets",
        headers={"X-Organization-ID": organization_id},
        files={"file": ("costs.csv", "department,cost\nDesign,12\nOperations,18\nSales,30\n", "text/csv")},
    )
    dataset = uploaded.json()
    saved = client.post("/api/v1/analyses", headers={"X-Organization-ID": organization_id}, json={
        "title": "Répartition des coûts",
        "dataset_id": dataset["id"],
        "column_name": "cost",
    })
    assert saved.status_code == 201, saved.text
    result = saved.json()
    assert result["dataset_name"] == "costs"
    assert result["column_profile"]["minimum"] == 12
    assert result["column_profile"]["maximum"] == 30
    assert sum(bin["count"] for bin in result["column_profile"]["distribution"]) == 3
    assert client.get("/api/v1/analyses", headers={"X-Organization-ID": organization_id}).json()[0]["id"] == result["id"]
    text_chart = client.post("/api/v1/analyses", headers={"X-Organization-ID": organization_id}, json={
        "title": "Répartition des services",
        "dataset_id": dataset["id"],
        "column_name": "department",
    })
    assert text_chart.status_code == 422
