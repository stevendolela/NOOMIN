import csv
import io
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from noomin_api.api.dependencies import get_current_organization, get_current_user
from noomin_api.db.session import get_db
from noomin_api.models import Dataset, DatasetRow, Membership, Organization, User
from noomin_api.schemas.dataset import DatasetDetail, DatasetSummary
from noomin_api.schemas.profile import DatasetProfile
from noomin_api.services.profiling import profile_columns

router = APIRouter(prefix="/datasets", tags=["datasets"])
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_DATA_ROWS = 20_000
MAX_COLUMNS = 200
PREVIEW_LIMIT = 100


def _summary(dataset: Dataset) -> DatasetSummary:
    return DatasetSummary(
        id=dataset.id,
        name=dataset.name,
        original_filename=dataset.original_filename,
        source_type=dataset.source_type,
        row_count=dataset.row_count,
        column_count=dataset.column_count,
        byte_size=dataset.byte_size,
        columns=dataset.columns,
        created_at=dataset.created_at,
    )


def _read_csv(payload: bytes) -> tuple[list[str], list[dict[str, str | None]]]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Le CSV doit être encodé en UTF-8.") from exc
    sample = text[:64 * 1024]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text, newline=""), dialect=dialect)
    headers = reader.fieldnames
    if not headers or not any((header or "").strip() for header in headers):
        raise HTTPException(status_code=400, detail="Le fichier ne contient pas de ligne d’en-tête valide.")
    columns = [header.strip() for header in headers if header is not None]
    if len(columns) != len(headers) or any(not column for column in columns):
        raise HTTPException(status_code=400, detail="Les noms de colonnes ne peuvent pas être vides.")
    if len(set(columns)) != len(columns):
        raise HTTPException(status_code=400, detail="Les noms de colonnes doivent être uniques.")
    if len(columns) > MAX_COLUMNS:
        raise HTTPException(status_code=400, detail=f"Le CSV ne peut pas dépasser {MAX_COLUMNS} colonnes.")
    rows: list[dict[str, str | None]] = []
    for row in reader:
        if None in row:
            raise HTTPException(status_code=400, detail="Une ligne contient plus de valeurs que l’en-tête.")
        if len(rows) >= MAX_DATA_ROWS:
            raise HTTPException(status_code=413, detail=f"Le CSV ne peut pas dépasser {MAX_DATA_ROWS} lignes.")
        rows.append({column: (row.get(header) or None) for header, column in zip(headers, columns, strict=True)})
    return columns, rows


@router.post("", response_model=DatasetSummary, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str | None = Form(default=None, max_length=160),
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DatasetSummary:
    filename = (file.filename or "").replace("\\", "/").split("/")[-1]
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Seuls les fichiers CSV sont acceptés pour le moment.")
    payload = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Le fichier ne peut pas dépasser 10 Mo.")
    if not payload:
        raise HTTPException(status_code=400, detail="Le fichier est vide.")
    columns, rows = _read_csv(payload)
    membership = db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.organization_id == organization.id))
    if membership is None or membership.role.value == "viewer":
        raise HTTPException(status_code=403, detail="Votre rôle ne permet pas d’importer des données.")
    clean_name = (name or filename[:-4]).strip() or "Jeu de données"
    dataset = Dataset(
        organization_id=organization.id,
        created_by=user.id,
        name=clean_name[:160],
        original_filename=filename[:255],
        row_count=len(rows),
        column_count=len(columns),
        byte_size=len(payload),
        columns=columns,
    )
    db.add(dataset)
    db.flush()
    db.add_all([DatasetRow(dataset_id=dataset.id, row_number=i, values=row) for i, row in enumerate(rows, start=1)])
    db.commit()
    db.refresh(dataset)
    return _summary(dataset)


@router.get("", response_model=list[DatasetSummary])
def list_datasets(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
) -> list[DatasetSummary]:
    datasets = db.scalars(select(Dataset).where(Dataset.organization_id == organization.id).order_by(Dataset.created_at.desc())).all()
    return [_summary(dataset) for dataset in datasets]


@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset(
    dataset_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
) -> DatasetDetail:
    dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == organization.id))
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jeu de données introuvable.")
    rows = db.scalars(select(DatasetRow).where(DatasetRow.dataset_id == dataset.id).order_by(DatasetRow.row_number).limit(PREVIEW_LIMIT)).all()
    return DatasetDetail(**_summary(dataset).model_dump(), preview=[row.values for row in rows])


@router.get("/{dataset_id}/profile", response_model=DatasetProfile)
def profile_dataset(
    dataset_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
) -> DatasetProfile:
    dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.organization_id == organization.id))
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Jeu de données introuvable.")
    rows = db.scalars(select(DatasetRow).where(DatasetRow.dataset_id == dataset.id).order_by(DatasetRow.row_number)).all()
    profiles = profile_columns(dataset.columns, [row.values for row in rows])
    return DatasetProfile(dataset_id=str(dataset.id), row_count=dataset.row_count, columns=profiles)
