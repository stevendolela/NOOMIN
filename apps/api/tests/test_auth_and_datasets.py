import pytest
from uuid import UUID
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from noomin_api.db.base import Base
from noomin_api.api.permissions import Permission, has_permission
from noomin_api.db.session import get_db
from noomin_api.main import app
from noomin_api.models import MembershipRole


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


def test_role_permission_matrix_matches_product_roles() -> None:
    assert has_permission(MembershipRole.OWNER, Permission.MANAGE_WORKSPACE)
    assert has_permission(MembershipRole.ADMIN, Permission.MANAGE_MEMBERS)
    assert not has_permission(MembershipRole.ADMIN, Permission.MANAGE_WORKSPACE)
    assert has_permission(MembershipRole.MEMBER, Permission.EDIT_DATA)
    assert not has_permission(MembershipRole.MEMBER, Permission.MANAGE_MEMBERS)
    assert has_permission(MembershipRole.VIEWER, Permission.READ_DATA)
    assert not has_permission(MembershipRole.VIEWER, Permission.EDIT_DATA)


def test_owner_can_manage_members_but_cannot_remove_last_owner(client: TestClient) -> None:
    session = create_account(client)
    organization_id = session["organizations"][0]["id"]
    owner_headers = {"X-Organization-ID": organization_id}
    owner_id = session["user"]["id"]
    listed = client.get("/api/v1/members", headers=owner_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["role"] == "owner"
    blocked = client.delete(f"/api/v1/members/{owner_id}", headers=owner_headers)
    assert blocked.status_code == 409

    invited = create_account(TestClient(client.app), "analyst@example.com")
    analyst_id = invited["user"]["id"]
    with client.app.state.test_session_factory() as db:
        from noomin_api.models import Membership, MembershipRole
        db.add(Membership(organization_id=UUID(organization_id), user_id=UUID(analyst_id), role=MembershipRole.MEMBER))
        db.commit()
    changed = client.patch(f"/api/v1/members/{analyst_id}", headers=owner_headers, json={"role": "viewer"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["role"] == "viewer"
    removed = client.delete(f"/api/v1/members/{analyst_id}", headers=owner_headers)
    assert removed.status_code == 204
    hidden = client.get("/api/v1/members", headers={"X-Organization-ID": invited["organizations"][0]["id"]})
    assert hidden.status_code == 403


def test_invitation_is_single_use_expires_and_creates_member(client: TestClient) -> None:
    owner = create_account(client)
    org_id = owner["organizations"][0]["id"]
    headers = {"X-Organization-ID": org_id}
    created = client.post("/api/v1/members/invitations", headers=headers, json={"email": "new.person@example.com", "role": "member"})
    assert created.status_code == 201, created.text
    data = created.json()
    assert "token" in data
    assert data["email"] == "new.person@example.com"
    invite_token = data["token"]
    detail = client.get(f"/api/v1/invitations/{invite_token}")
    assert detail.status_code == 200
    assert detail.json()["organization_name"] == owner["organizations"][0]["name"]
    pending = client.get("/api/v1/members/invitations", headers=headers)
    assert pending.status_code == 200
    assert pending.json()[0]["email"] == "new.person@example.com"
    invitee_client = TestClient(client.app)
    accepted = invitee_client.post(f"/api/v1/invitations/{invite_token}/accept", json={"full_name": "New Person", "password": "valid-password-2026!"})
    assert accepted.status_code == 200, accepted.text
    invited_org = next(item for item in accepted.json()["organizations"] if item["id"] == org_id)
    assert invited_org["role"] == "member"
    used = invitee_client.post(f"/api/v1/invitations/{invite_token}/accept", json={"full_name": "New Person", "password": "valid-password-2026!"})
    assert used.status_code == 404
    assert client.get(f"/api/v1/invitations/{invite_token}").status_code == 404


def test_admin_cannot_invite_admin_or_owner(client: TestClient) -> None:
    owner = create_account(client)
    org_id = owner["organizations"][0]["id"]
    with client.app.state.test_session_factory() as db:
        from sqlalchemy import select
        from noomin_api.models import Membership, MembershipRole
        membership = db.scalar(select(Membership).where(Membership.organization_id == UUID(org_id), Membership.user_id == UUID(owner["user"]["id"])))
        membership.role = MembershipRole.ADMIN
        db.commit()
    denied = client.post("/api/v1/members/invitations", headers={"X-Organization-ID": org_id}, json={"email": "admin@example.com", "role": "admin"})
    assert denied.status_code == 403


def test_expired_invitation_is_not_revealed_or_accepted(client: TestClient) -> None:
    from datetime import UTC, datetime, timedelta
    from sqlalchemy import select
    from noomin_api.models import OrganizationInvitation

    owner = create_account(client)
    org_id = owner["organizations"][0]["id"]
    created = client.post("/api/v1/members/invitations", headers={"X-Organization-ID": org_id}, json={"email": "expired@example.com"})
    token = created.json()["token"]
    with client.app.state.test_session_factory() as db:
        invitation = db.scalar(select(OrganizationInvitation).where(OrganizationInvitation.email == "expired@example.com"))
        invitation.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    assert client.get(f"/api/v1/invitations/{token}").status_code == 404
    expired = client.post(f"/api/v1/invitations/{token}/accept", json={"full_name": "Expired User", "password": "valid-password-2026!"})
    assert expired.status_code == 404


def test_login_throttle_blocks_repeated_failures_and_resets_after_window(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import UTC, datetime, timedelta
    from sqlalchemy import select
    from noomin_api.api import auth
    from noomin_api.models import AuthLoginThrottle

    create_account(client, "throttle@example.com")
    monkeypatch.setattr(auth, "LOGIN_FAILURE_LIMIT", 2)
    first = client.post("/api/v1/auth/login", json={"email": "throttle@example.com", "password": "wrong-password"})
    second = client.post("/api/v1/auth/login", json={"email": "throttle@example.com", "password": "wrong-password"})
    assert first.status_code == 401
    assert second.status_code == 429
    blocked = client.post("/api/v1/auth/login", json={"email": "throttle@example.com", "password": "correct-horse-2026!"})
    assert blocked.status_code == 429
    with client.app.state.test_session_factory() as db:
        throttle = db.get(AuthLoginThrottle, auth._login_bucket("throttle@example.com", "testclient"))
        throttle.blocked_until = datetime.now(UTC) - timedelta(seconds=1)
        throttle.window_started_at = datetime.now(UTC) - timedelta(minutes=16)
        db.commit()
    success = client.post("/api/v1/auth/login", json={"email": "throttle@example.com", "password": "correct-horse-2026!"})
    assert success.status_code == 200


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
    date = next(column for column in profile.json()["columns"] if column["name"] == "jour")
    assert date["data_type"] == "text"
    assert date["category_counts"] == [{"value": "2026-01-01", "count": 1}, {"value": "2026-01-02", "count": 1}]


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


def test_dataset_owner_can_delete_import_and_viewer_cannot(client: TestClient) -> None:
    owner_session = create_account(client)
    organization_id = owner_session["organizations"][0]["id"]
    uploaded = client.post(
        "/api/v1/datasets",
        headers={"X-Organization-ID": organization_id},
        files={"file": ("sales.csv", "amount\n12\n", "text/csv")},
    )
    dataset_id = uploaded.json()["id"]
    pipeline_response = client.post("/api/v1/pipelines", headers={"X-Organization-ID": organization_id}, json={
        "name": "Pipeline propriétaire",
        "source_dataset_id": dataset_id,
        "steps": [{"op": "select_columns", "columns": ["amount"]}],
    })
    assert pipeline_response.status_code == 201, pipeline_response.text

    other_client = TestClient(app)
    viewer_session = create_account(other_client, "viewer@example.com")
    viewer_id = viewer_session["user"]["id"]
    with client.app.state.test_session_factory() as db:
        from noomin_api.models import Membership, MembershipRole

        db.add(Membership(organization_id=UUID(organization_id), user_id=UUID(viewer_id), role=MembershipRole.VIEWER))
        db.commit()
    viewer_upload = other_client.post(
        "/api/v1/datasets",
        headers={"X-Organization-ID": organization_id},
        files={"file": ("new.csv", "value\n2\n", "text/csv")},
    )
    viewer_analysis = other_client.post("/api/v1/analyses", headers={"X-Organization-ID": organization_id}, json={
        "title": "Analyse interdite", "dataset_id": dataset_id, "column_name": "amount",
    })
    viewer_run = other_client.post(
        f"/api/v1/pipelines/{pipeline_response.json()['id']}/runs",
        headers={"X-Organization-ID": organization_id},
    )
    assert viewer_upload.status_code == 403
    assert viewer_analysis.status_code == 403
    assert viewer_run.status_code == 403
    denied = other_client.delete(f"/api/v1/datasets/{dataset_id}", headers={"X-Organization-ID": organization_id})
    assert denied.status_code == 403

    deleted = client.delete(f"/api/v1/datasets/{dataset_id}", headers={"X-Organization-ID": organization_id})
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/datasets/{dataset_id}", headers={"X-Organization-ID": organization_id}).status_code == 404
    assert client.get("/api/v1/datasets", headers={"X-Organization-ID": organization_id}).json() == []


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
    history = client.get(f"/api/v1/pipelines/{pipeline_id}/runs", headers={"X-Organization-ID": organization_id})
    assert history.status_code == 200, history.text
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["id"] == queued.json()["id"]
    output = client.get(f"/api/v1/datasets/{completed['output_dataset_id']}", headers={"X-Organization-ID": organization_id})
    assert output.status_code == 200
    assert output.json()["row_count"] == 2
    assert output.json()["columns"] == ["date", "revenue_selected"]
    assert output.json()["preview"][0] == {"date": "2026-01-02", "revenue_selected": "25"}
    other_client = TestClient(client.app)
    other = create_account(other_client, "outsider@example.com")
    forbidden_history = other_client.get(f"/api/v1/pipelines/{pipeline_id}/runs", headers={"X-Organization-ID": other["organizations"][0]["id"]})
    assert forbidden_history.status_code == 404


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
