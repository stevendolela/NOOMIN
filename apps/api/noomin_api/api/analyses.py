from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from noomin_api.api.dependencies import get_current_organization, get_current_user
from noomin_api.db.session import get_db
from noomin_api.models import Dataset, DatasetRow, Membership, Organization, SavedAnalysis, User
from noomin_api.schemas.analysis import AnalysisCreate, AnalysisResponse
from noomin_api.schemas.profile import ColumnProfile
from noomin_api.services.profiling import profile_columns

router = APIRouter(prefix="/analyses", tags=["analyses"])


def _response(db: Session, analysis: SavedAnalysis) -> AnalysisResponse:
    dataset = db.get(Dataset, analysis.dataset_id)
    return AnalysisResponse(
        id=analysis.id,
        title=analysis.title,
        dataset_id=analysis.dataset_id,
        dataset_name=dataset.name if dataset else "Jeu de données supprimé",
        column_profile=ColumnProfile.model_validate(analysis.profile),
        created_at=analysis.created_at,
    )


@router.get("", response_model=list[AnalysisResponse])
def list_analyses(organization: Organization = Depends(get_current_organization), db: Session = Depends(get_db)) -> list[AnalysisResponse]:
    analyses = db.scalars(select(SavedAnalysis).where(SavedAnalysis.organization_id == organization.id).order_by(SavedAnalysis.created_at.desc())).all()
    return [_response(db, analysis) for analysis in analyses]


@router.post("", response_model=AnalysisResponse, status_code=201)
def create_analysis(
    body: AnalysisCreate,
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisResponse:
    membership = db.scalar(select(Membership).where(Membership.organization_id == organization.id, Membership.user_id == user.id))
    if membership is None or membership.role.value == "viewer":
        raise HTTPException(status_code=403, detail="Votre rôle ne permet pas d’enregistrer des analyses.")
    dataset = db.scalar(select(Dataset).where(Dataset.id == body.dataset_id, Dataset.organization_id == organization.id))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Jeu de données introuvable dans cette organisation.")
    if body.column_name not in dataset.columns:
        raise HTTPException(status_code=422, detail="La colonne indiquée ne fait pas partie de ce jeu de données.")
    rows = db.scalars(select(DatasetRow).where(DatasetRow.dataset_id == dataset.id).order_by(DatasetRow.row_number)).all()
    profile = next(item for item in profile_columns(dataset.columns, [row.values for row in rows]) if item.name == body.column_name)
    if profile.data_type != "number":
        raise HTTPException(status_code=422, detail="Les graphiques de distribution nécessitent une colonne numérique.")
    analysis = SavedAnalysis(
        organization_id=organization.id,
        dataset_id=dataset.id,
        created_by=user.id,
        title=body.title.strip(),
        column_name=body.column_name,
        profile=profile.model_dump(mode="json"),
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return _response(db, analysis)
