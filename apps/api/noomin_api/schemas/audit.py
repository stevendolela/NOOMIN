from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: UUID
    actor_name: str
    actor_email: str | None
    action: str
    entity_type: str
    entity_id: str | None
    metadata: dict
    created_at: datetime


class AuditLogResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
