from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from noomin_api.schemas.profile import ColumnProfile


class AnalysisCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    dataset_id: UUID
    column_name: str = Field(min_length=1, max_length=160)


class AnalysisResponse(BaseModel):
    id: UUID
    title: str
    dataset_id: UUID
    dataset_name: str
    column_profile: ColumnProfile
    created_at: datetime
