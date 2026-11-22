from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DatasetSummary(BaseModel):
    id: UUID
    name: str
    original_filename: str
    source_type: str
    row_count: int
    column_count: int
    byte_size: int
    columns: list[str]
    created_at: datetime


class DatasetDetail(DatasetSummary):
    preview: list[dict[str, str | None]]
