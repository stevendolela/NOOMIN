from enum import StrEnum

from fastapi import HTTPException, status

from noomin_api.models import MembershipRole


class Permission(StrEnum):
    READ_DATA = "read_data"
    EDIT_DATA = "edit_data"
    MANAGE_MEMBERS = "manage_members"
    MANAGE_WORKSPACE = "manage_workspace"


ROLE_PERMISSIONS: dict[MembershipRole, frozenset[Permission]] = {
    MembershipRole.OWNER: frozenset(Permission),
    MembershipRole.ADMIN: frozenset({Permission.READ_DATA, Permission.EDIT_DATA, Permission.MANAGE_MEMBERS}),
    # `member` remains the stored role for backward compatibility; product-facing name is Analyst.
    MembershipRole.MEMBER: frozenset({Permission.READ_DATA, Permission.EDIT_DATA}),
    MembershipRole.VIEWER: frozenset({Permission.READ_DATA}),
}


def has_permission(role: MembershipRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]


def require_permission(role: MembershipRole, permission: Permission, detail: str) -> None:
    if not has_permission(role, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
