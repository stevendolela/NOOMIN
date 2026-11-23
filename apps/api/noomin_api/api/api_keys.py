from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from noomin_api.api.audit import record_audit
from noomin_api.api.dependencies import get_current_organization, get_current_user, require_api_scope
from noomin_api.api.permissions import Permission, require_permission
from noomin_api.db.session import get_db
from noomin_api.models import Dataset, DatasetRow, Membership, Organization, OrganizationAPIKey, User
from noomin_api.schemas.api_keys import APIKeyCreate, APIKeyCreated, APIKeyResponse, DatasetRowsResponse
from noomin_api.schemas.dataset import DatasetDetail, DatasetSummary
from noomin_api.schemas.profile import DatasetProfile
from noomin_api.services.profiling import profile_columns

management_router = APIRouter(prefix="/api-keys", tags=["API keys"])
customer_router = APIRouter(prefix="/client/v1/datasets", tags=["Customer API v1"])
MAX_ACTIVE_KEYS = 20
MAX_PAGE_SIZE = 1000


def _require_owner(db: Session, organization: Organization, user: User) -> None:
    membership = db.scalar(select(Membership).where(Membership.organization_id == organization.id, Membership.user_id == user.id))
    if membership is None:
        raise HTTPException(status_code=403, detail="Vous n’avez pas accès à cette organisation.")
    require_permission(membership.role, Permission.MANAGE_WORKSPACE, "Seul le propriétaire peut gérer les clés API.")


def _key_response(api_key: OrganizationAPIKey) -> APIKeyResponse:
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        scopes=api_key.scopes,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        revoked_at=api_key.revoked_at,
    )


@management_router.get("", response_model=list[APIKeyResponse])
def list_api_keys(
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[APIKeyResponse]:
    _require_owner(db, organization, user)
    keys = db.scalars(select(OrganizationAPIKey).where(OrganizationAPIKey.organization_id == organization.id).order_by(OrganizationAPIKey.created_at.desc())).all()
    return [_key_response(api_key) for api_key in keys]


@management_router.post("", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    body: APIKeyCreate,
    response: Response,
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIKeyCreated:
    response.headers["Cache-Control"] = "no-store"
    _require_owner(db, organization, user)
    clean_name = body.name.strip()
    if len(clean_name) < 2:
        raise HTTPException(status_code=422, detail="Le nom doit contenir au moins deux caractères.")
    now = datetime.now(UTC)
    active_count = db.scalar(select(func.count()).select_from(OrganizationAPIKey).where(
        OrganizationAPIKey.organization_id == organization.id,
        OrganizationAPIKey.revoked_at.is_(None),
        or_(OrganizationAPIKey.expires_at.is_(None), OrganizationAPIKey.expires_at > now),
    )) or 0
    if active_count >= MAX_ACTIVE_KEYS:
        raise HTTPException(status_code=409, detail=f"Une organisation ne peut pas avoir plus de {MAX_ACTIVE_KEYS} clés API actives.")
    scopes = sorted(set(body.scopes))
    secret = f"noomin_live_{secrets.token_urlsafe(36)}"
    api_key = OrganizationAPIKey(
        organization_id=organization.id,
        created_by=user.id,
        name=clean_name,
        key_prefix=secret[:20],
        key_hash=hashlib.sha256(secret.encode("utf-8")).hexdigest(),
        scopes=scopes,
        expires_at=now + timedelta(days=body.expires_in_days) if body.expires_in_days is not None else None,
    )
    db.add(api_key)
    db.flush()
    record_audit(db, organization.id, user.id, "api_key.created", "api_key", api_key.id, {"name": clean_name, "scopes": scopes})
    db.commit()
    db.refresh(api_key)
    return APIKeyCreated(**_key_response(api_key).model_dump(), secret=secret)


@management_router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    api_key_id: UUID,
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    _require_owner(db, organization, user)
    api_key = db.scalar(select(OrganizationAPIKey).where(OrganizationAPIKey.id == api_key_id, OrganizationAPIKey.organization_id == organization.id))
    if api_key is None:
        raise HTTPException(status_code=404, detail="Clé API introuvable.")
    if api_key.revoked_at is None:
        api_key.revoked_at = datetime.now(UTC)
        record_audit(db, organization.id, user.id, "api_key.revoked", "api_key", api_key.id, {"name": api_key.name})
        db.commit()


@customer_router.get("", response_model=list[DatasetSummary], summary="Lister les jeux de données de l’organisation liée à la clé")
def customer_list_datasets(
    api_key: OrganizationAPIKey = Depends(require_api_scope("datasets:read")),
    db: Session = Depends(get_db),
) -> list[DatasetSummary]:
    datasets = db.scalars(select(Dataset).where(Dataset.organization_id == api_key.organization_id).order_by(Dataset.created_at.desc())).all()
    return [DatasetSummary.model_validate(dataset) for dataset in datasets]


@customer_router.get("/{dataset_id}", response_model=DatasetDetail, summary="Consulter un jeu de données")
def customer_get_dataset(
    dataset_id: UUID,
    api_key: OrganizationAPIKey = Depends(require_api_scope("datasets:read")),
    db: Session = Depends(get_db),
) -> DatasetDetail:
    dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == api_key.organization_id))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Jeu de données introuvable.")
    rows = db.scalars(select(DatasetRow).where(DatasetRow.dataset_id == dataset.id).order_by(DatasetRow.row_number).limit(100)).all()
    return DatasetDetail(**DatasetSummary.model_validate(dataset).model_dump(), preview=[row.values for row in rows])


@customer_router.get("/{dataset_id}/rows", response_model=DatasetRowsResponse, summary="Lire une page de lignes")
def customer_get_dataset_rows(
    dataset_id: UUID,
    limit: int = 100,
    offset: int = 0,
    api_key: OrganizationAPIKey = Depends(require_api_scope("datasets:read")),
    db: Session = Depends(get_db),
) -> DatasetRowsResponse:
    if limit < 1 or limit > MAX_PAGE_SIZE or offset < 0:
        raise HTTPException(status_code=422, detail=f"limit doit être entre 1 et {MAX_PAGE_SIZE} et offset doit être positif.")
    dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == api_key.organization_id))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Jeu de données introuvable.")
    total = db.scalar(select(func.count()).select_from(DatasetRow).where(DatasetRow.dataset_id == dataset.id)) or 0
    rows = db.scalars(select(DatasetRow).where(DatasetRow.dataset_id == dataset.id).order_by(DatasetRow.row_number).offset(offset).limit(limit)).all()
    return DatasetRowsResponse(dataset_id=dataset.id, columns=dataset.columns, items=[row.values for row in rows], total=total, limit=limit, offset=offset)


@customer_router.get("/{dataset_id}/profile", response_model=DatasetProfile, summary="Consulter le profil des colonnes")
def customer_profile_dataset(
    dataset_id: UUID,
    api_key: OrganizationAPIKey = Depends(require_api_scope("profiles:read")),
    db: Session = Depends(get_db),
) -> DatasetProfile:
    dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == api_key.organization_id))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Jeu de données introuvable.")
    rows = db.scalars(select(DatasetRow).where(DatasetRow.dataset_id == dataset.id).order_by(DatasetRow.row_number)).all()
    profiles = profile_columns(dataset.columns, [row.values for row in rows])
    return DatasetProfile(dataset_id=str(dataset.id), row_count=dataset.row_count, columns=profiles)
