"""Real Celery jobs for tenant data transformations."""
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from noomin_api.db.session import SessionLocal
from noomin_api.models import Dataset, DatasetRow, Pipeline, PipelineRun
from noomin_api.worker import celery_app

logger = logging.getLogger(__name__)


def _matches(value: str | None, step: dict) -> bool:
    operator = step["operator"]
    target = step.get("value")
    if operator == "is_empty":
        return value is None or value == ""
    if operator == "is_not_empty":
        return value is not None and value != ""
    if value is None or target is None:
        return False
    if operator == "equals":
        return value == target
    if operator == "not_equals":
        return value != target
    if operator == "contains":
        return target in value
    if operator in {"greater_than", "less_than"}:
        try:
            current_number, target_number = Decimal(value), Decimal(target)
        except InvalidOperation:
            return False
        if not current_number.is_finite() or not target_number.is_finite():
            return False
        return current_number > target_number if operator == "greater_than" else current_number < target_number
    return False


def _transform(columns: list[str], records: list[dict[str, str | None]], steps: list[dict]) -> tuple[list[str], list[dict[str, str | None]]]:
    current_columns = list(columns)
    current_records = [dict(record) for record in records]
    for step in steps:
        if step["op"] == "select_columns":
            current_columns = list(step["columns"])
            current_records = [{column: record.get(column) for column in current_columns} for record in current_records]
        elif step["op"] == "rename_columns":
            mapping = step["mapping"]
            renamed = [mapping.get(column, column) for column in current_columns]
            current_records = [{mapping.get(column, column): record.get(column) for column in current_columns} for record in current_records]
            current_columns = renamed
        elif step["op"] == "filter_rows":
            current_records = [record for record in current_records if _matches(record.get(step["column"]), step)]
    return current_columns, current_records


def execute_pipeline_job(run_id: str, session_factory=SessionLocal) -> None:
    db: Session = session_factory()
    try:
        run = db.scalar(select(PipelineRun).where(PipelineRun.id == UUID(run_id)).with_for_update())
        if run is None or run.status in {"succeeded", "running"}:
            return
        run.status = "running"
        run.started_at = datetime.now(UTC)
        run.error_message = None
        db.commit()
        pipeline = db.get(Pipeline, run.pipeline_id)
        source = db.get(Dataset, pipeline.source_dataset_id) if pipeline else None
        if pipeline is None or source is None:
            raise RuntimeError("Pipeline source is no longer available")
        source_rows = db.scalars(select(DatasetRow).where(DatasetRow.dataset_id == source.id).order_by(DatasetRow.row_number)).all()
        columns, output_rows = _transform(source.columns, [row.values for row in source_rows], pipeline.steps)
        output = Dataset(
            organization_id=pipeline.organization_id,
            created_by=pipeline.created_by,
            name=f"{pipeline.name} · résultat"[:160],
            original_filename=f"pipeline-{pipeline.id}.csv",
            source_type="pipeline_output",
            row_count=len(output_rows),
            column_count=len(columns),
            byte_size=0,
            columns=columns,
        )
        db.add(output)
        db.flush()
        db.add_all([DatasetRow(dataset_id=output.id, row_number=index, values=record) for index, record in enumerate(output_rows, 1)])
        run.status = "succeeded"
        run.output_dataset_id = output.id
        run.finished_at = datetime.now(UTC)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Pipeline execution failed for run %s", run_id)
        run = db.get(PipelineRun, UUID(run_id))
        if run is not None:
            run.status = "failed"
            run.error_message = "Le traitement a échoué. Vérifiez la source et les étapes du pipeline."
            run.finished_at = datetime.now(UTC)
            db.commit()
    finally:
        db.close()


@celery_app.task(name="noomin.execute_pipeline", bind=True)
def execute_pipeline(self, run_id: str) -> None:
    execute_pipeline_job(run_id)
