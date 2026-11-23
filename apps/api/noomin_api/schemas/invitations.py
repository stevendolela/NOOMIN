from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from noomin_api.models import MembershipRole


class InvitationCreate(BaseModel):
    email: EmailStr
    role: MembershipRole = MembershipRole.MEMBER


class InvitationCreated(BaseModel):
    id: UUID
    email: EmailStr
    role: MembershipRole
    token: str
    expires_at: datetime
    created_at: datetime


class InvitationResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: MembershipRole
    expires_at: datetime
    created_at: datetime


class InvitationDetails(BaseModel):
    email: EmailStr
    role: MembershipRole
    organization_name: str
    expires_at: datetime


class InvitationAcceptance(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    password: str | None = Field(default=None, min_length=12, max_length=128)
