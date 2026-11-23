from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from noomin_api.models import MembershipRole


class MemberResponse(BaseModel):
    user_id: UUID
    email: EmailStr
    full_name: str
    role: MembershipRole
    joined_at: datetime


class MemberRoleUpdate(BaseModel):
    role: MembershipRole
