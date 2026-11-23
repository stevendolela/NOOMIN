from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


APIScope = Literal["datasets:read", "profiles:read"]


class APIKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    scopes: list[APIScope] = Field(min_length=1, max_length=2)
    expires_in_days: int | None = Field(default=90, ge=1, le=365)


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None


class APIKeyCreated(APIKeyResponse):
    secret: str


class DatasetRowsResponse(BaseModel):
    dataset_id: UUID
    columns: list[str]
    items: list[dict[str, str | None]]
    total: int
    limit: int
    offset: int
