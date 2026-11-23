from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class SelectColumnsStep(BaseModel):
    op: Literal["select_columns"]
    columns: list[str] = Field(min_length=1, max_length=200)


class RenameColumnsStep(BaseModel):
    op: Literal["rename_columns"]
    mapping: dict[str, str] = Field(min_length=1, max_length=200)


class FilterRowsStep(BaseModel):
    op: Literal["filter_rows"]
    column: str = Field(min_length=1, max_length=160)
    operator: Literal["equals", "not_equals", "contains", "greater_than", "less_than", "is_empty", "is_not_empty"]
    value: str | None = Field(default=None, max_length=500)


PipelineStep = Annotated[SelectColumnsStep | RenameColumnsStep | FilterRowsStep, Field(discriminator="op")]


class PipelineCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    source_dataset_id: UUID
    steps: list[PipelineStep] = Field(min_length=1, max_length=10)


class PipelineRunResponse(BaseModel):
    id: UUID
    status: str
    output_dataset_id: UUID | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class PipelineResponse(BaseModel):
    id: UUID
    name: str
    source_dataset_id: UUID
    source_dataset_name: str
    steps: list[dict]
    created_at: datetime
    last_run: PipelineRunResponse | None = None


class PipelineRunHistoryResponse(BaseModel):
    items: list[PipelineRunResponse]
    total: int
