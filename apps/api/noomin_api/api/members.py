from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from noomin_api.api.dependencies import get_current_organization, get_current_user
from noomin_api.api.permissions import Permission, require_permission
from noomin_api.db.session import get_db
from noomin_api.models import Membership, MembershipRole, Organization, User
from noomin_api.schemas.members import MemberResponse, MemberRoleUpdate

router = APIRouter(prefix="/members", tags=["members"])


def _require_manager(db: Session, organization: Organization, user: User) -> Membership:
    membership = db.scalar(select(Membership).where(Membership.organization_id == organization.id, Membership.user_id == user.id))
    if membership is None:
        raise HTTPException(status_code=403, detail="Vous n’avez pas accès à cette organisation.")
    require_permission(membership.role, Permission.MANAGE_MEMBERS, "Votre rôle ne permet pas de gérer les membres.")
    return membership


def _member_response(membership: Membership) -> MemberResponse:
    return MemberResponse(user_id=membership.user.id, email=membership.user.email, full_name=membership.user.full_name, role=membership.role, joined_at=membership.created_at)


@router.get("", response_model=list[MemberResponse])
def list_members(
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MemberResponse]:
    _require_manager(db, organization, user)
    memberships = db.scalars(select(Membership).where(Membership.organization_id == organization.id).order_by(Membership.created_at, Membership.id)).all()
    return [_member_response(membership) for membership in memberships]


@router.patch("/{user_id}", response_model=MemberResponse)
def update_member_role(
    user_id: UUID,
    body: MemberRoleUpdate,
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberResponse:
    actor = _require_manager(db, organization, user)
    target = db.scalar(select(Membership).where(Membership.organization_id == organization.id, Membership.user_id == user_id))
    if target is None:
        raise HTTPException(status_code=404, detail="Membre introuvable.")
    if actor.role != MembershipRole.OWNER and (target.role in {MembershipRole.OWNER, MembershipRole.ADMIN} or body.role in {MembershipRole.OWNER, MembershipRole.ADMIN}):
        raise HTTPException(status_code=403, detail="Seul le propriétaire peut gérer les rôles administrateur et propriétaire.")
    if target.role == MembershipRole.OWNER and body.role != MembershipRole.OWNER:
        owners = db.scalar(select(func.count()).select_from(Membership).where(Membership.organization_id == organization.id, Membership.role == MembershipRole.OWNER)) or 0
        if owners <= 1:
            raise HTTPException(status_code=409, detail="L’organisation doit conserver au moins un propriétaire.")
    target.role = body.role
    db.commit()
    db.refresh(target)
    return _member_response(target)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: UUID,
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    actor = _require_manager(db, organization, user)
    target = db.scalar(select(Membership).where(Membership.organization_id == organization.id, Membership.user_id == user_id))
    if target is None:
        raise HTTPException(status_code=404, detail="Membre introuvable.")
    if actor.role != MembershipRole.OWNER and target.role in {MembershipRole.OWNER, MembershipRole.ADMIN}:
        raise HTTPException(status_code=403, detail="Seul le propriétaire peut retirer un administrateur ou un propriétaire.")
    if target.role == MembershipRole.OWNER:
        owners = db.scalar(select(func.count()).select_from(Membership).where(Membership.organization_id == organization.id, Membership.role == MembershipRole.OWNER)) or 0
        if owners <= 1:
            raise HTTPException(status_code=409, detail="L’organisation doit conserver au moins un propriétaire.")
    db.delete(target)
    db.commit()
