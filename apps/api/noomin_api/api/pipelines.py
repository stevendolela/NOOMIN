from uuid import UUID
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from noomin_api.api.dependencies import get_current_organization, get_current_user
from noomin_api.db.session import get_db
from noomin_api.models import Dataset, Membership, Organization, Pipeline, PipelineRun, User
from noomin_api.schemas.pipeline import FilterRowsStep, PipelineCreate, PipelineResponse, PipelineRunResponse, RenameColumnsStep, SelectColumnsStep
from noomin_api.tasks import execute_pipeline

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


def _require_editor(db: Session, organization: Organization, user: User) -> None:
    membership = db.scalar(select(Membership).where(Membership.organization_id == organization.id, Membership.user_id == user.id))
    if membership is None or membership.role.value == "viewer":
        raise HTTPException(status_code=403, detail="Votre rôle ne permet pas de modifier les pipelines.")


def _validate_steps(body: PipelineCreate, source: Dataset) -> list[dict]:
    columns = list(source.columns)
    stored_steps = []
    for step in body.steps:
        if isinstance(step, SelectColumnsStep):
            if len(set(step.columns)) != len(step.columns) or not set(step.columns).issubset(columns):
                raise HTTPException(status_code=422, detail="La sélection contient une colonne inconnue ou répétée.")
            columns = list(step.columns)
        elif isinstance(step, RenameColumnsStep):
            if not set(step.mapping).issubset(columns) or any(not value.strip() or len(value.strip()) > 160 for value in step.mapping.values()):
                raise HTTPException(status_code=422, detail="Le renommage contient une colonne inconnue ou un nom vide.")
            updated = [step.mapping.get(column, column).strip() for column in columns]
            if len(set(updated)) != len(updated):
                raise HTTPException(status_code=422, detail="Les noms de colonnes après renommage doivent être uniques.")
            columns = updated
        elif isinstance(step, FilterRowsStep):
            if step.column not in columns:
                raise HTTPException(status_code=422, detail=f"La colonne « {step.column} » n’existe pas à cette étape.")
            if step.operator not in {"is_empty", "is_not_empty"} and step.value is None:
                raise HTTPException(status_code=422, detail="Cette condition nécessite une valeur de comparaison.")
            if step.operator in {"greater_than", "less_than"}:
                try:
                    target = Decimal(step.value or "")
                except InvalidOperation as exc:
                    raise HTTPException(status_code=422, detail="Les comparaisons numériques nécessitent une valeur numérique.") from exc
                if not target.is_finite():
                    raise HTTPException(status_code=422, detail="La valeur de comparaison doit être un nombre fini.")
        stored_steps.append(step.model_dump())
    return stored_steps


def _run_response(run: PipelineRun | None) -> PipelineRunResponse | None:
    if run is None:
        return None
    return PipelineRunResponse(
        id=run.id,
        status=run.status,
        output_dataset_id=run.output_dataset_id,
        error_message=run.error_message,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _pipeline_response(db: Session, pipeline: Pipeline) -> PipelineResponse:
    source = db.get(Dataset, pipeline.source_dataset_id)
    if source is None:
        source_name = "Source supprimée"
    else:
        source_name = source.name
    latest = pipeline.runs[0] if pipeline.runs else None
    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        source_dataset_id=pipeline.source_dataset_id,
        source_dataset_name=source_name,
        steps=pipeline.steps,
        created_at=pipeline.created_at,
        last_run=_run_response(latest),
    )


@router.get("", response_model=list[PipelineResponse])
def list_pipelines(organization: Organization = Depends(get_current_organization), db: Session = Depends(get_db)) -> list[PipelineResponse]:
    pipelines = db.scalars(select(Pipeline).where(Pipeline.organization_id == organization.id).order_by(Pipeline.created_at.desc())).all()
    return [_pipeline_response(db, pipeline) for pipeline in pipelines]


@router.post("", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
def create_pipeline(
    body: PipelineCreate,
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PipelineResponse:
    _require_editor(db, organization, user)
    source = db.scalar(select(Dataset).where(Dataset.id == body.source_dataset_id, Dataset.organization_id == organization.id))
    if source is None:
        raise HTTPException(status_code=404, detail="Jeu de données introuvable dans cette organisation.")
    pipeline = Pipeline(
        organization_id=organization.id,
        source_dataset_id=source.id,
        created_by=user.id,
        name=body.name.strip(),
        steps=_validate_steps(body, source),
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    return _pipeline_response(db, pipeline)


@router.get("/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(
    pipeline_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
) -> PipelineResponse:
    pipeline = db.scalar(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.organization_id == organization.id))
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline introuvable.")
    return _pipeline_response(db, pipeline)


@router.post("/{pipeline_id}/runs", response_model=PipelineRunResponse, status_code=status.HTTP_202_ACCEPTED)
def run_pipeline(
    pipeline_id: UUID,
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PipelineRunResponse:
    _require_editor(db, organization, user)
    pipeline = db.scalar(select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.organization_id == organization.id))
    if pipeline is None:
        raise HTTPException(status_code=404, detail="Pipeline introuvable.")
    run = PipelineRun(pipeline_id=pipeline.id, status="queued")
    db.add(run)
    db.commit()
    db.refresh(run)
    queued_response = _run_response(run)
    run_id = str(run.id)
    db.close()
    try:
        execute_pipeline.apply_async(args=[run_id])
    except Exception as exc:
        run = db.get(PipelineRun, UUID(run_id))
        if run is None:
            raise HTTPException(status_code=503, detail="La file de traitements est indisponible. Réessayez plus tard.") from exc
        run.status = "failed"
        run.error_message = "La file de traitements est indisponible. Réessayez plus tard."
        db.commit()
        raise HTTPException(status_code=503, detail=run.error_message) from exc
    return queued_response
