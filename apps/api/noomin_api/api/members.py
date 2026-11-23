from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from noomin_api.api.dependencies import get_current_organization, get_current_user
from noomin_api.api.permissions import Permission, require_permission
from noomin_api.db.session import get_db
from noomin_api.core.security import create_access_token, hash_password, read_access_token
from noomin_api.core.config import get_settings
from noomin_api.models import Membership, MembershipRole, Organization, OrganizationInvitation, User
from noomin_api.schemas.auth import OrganizationResponse, SessionResponse, UserResponse
from noomin_api.schemas.invitations import InvitationAcceptance, InvitationCreate, InvitationCreated, InvitationDetails, InvitationResponse
from noomin_api.schemas.members import MemberResponse, MemberRoleUpdate

router = APIRouter(prefix="/members", tags=["members"])
invitations_router = APIRouter(prefix="/invitations", tags=["invitations"])


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _expired(value: datetime) -> bool:
    return (value.replace(tzinfo=UTC) if value.tzinfo is None else value) <= _now()


def _invitation_response(invitation: OrganizationInvitation) -> InvitationResponse:
    return InvitationResponse(id=invitation.id, email=invitation.email, role=invitation.role, expires_at=invitation.expires_at, created_at=invitation.created_at)


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


@router.get("/invitations", response_model=list[InvitationResponse])
def list_invitations(
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InvitationResponse]:
    _require_manager(db, organization, user)
    invitations = db.scalars(select(OrganizationInvitation).where(OrganizationInvitation.organization_id == organization.id, OrganizationInvitation.accepted_at.is_(None)).order_by(OrganizationInvitation.created_at.desc())).all()
    return [_invitation_response(invitation) for invitation in invitations if not _expired(invitation.expires_at)]


@router.post("/invitations", response_model=InvitationCreated, status_code=status.HTTP_201_CREATED)
def create_invitation(
    body: InvitationCreate,
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvitationCreated:
    actor = _require_manager(db, organization, user)
    email = str(body.email).strip().lower()
    if body.role == MembershipRole.OWNER or (actor.role != MembershipRole.OWNER and body.role == MembershipRole.ADMIN):
        raise HTTPException(status_code=403, detail="Votre rôle ne permet pas d’inviter un membre avec ce niveau d’accès.")
    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user and db.scalar(select(Membership.id).where(Membership.organization_id == organization.id, Membership.user_id == existing_user.id)):
        raise HTTPException(status_code=409, detail="Cette personne est déjà membre de l’organisation.")
    pending = db.scalar(select(OrganizationInvitation.id).where(OrganizationInvitation.organization_id == organization.id, OrganizationInvitation.email == email, OrganizationInvitation.accepted_at.is_(None), OrganizationInvitation.expires_at > _now()))
    if pending:
        raise HTTPException(status_code=409, detail="Une invitation est déjà en attente pour cette adresse.")
    token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation(organization_id=organization.id, created_by=user.id, email=email, role=body.role, token_hash=_token_digest(token), expires_at=_now() + timedelta(days=7))
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return InvitationCreated(id=invitation.id, email=invitation.email, role=invitation.role, token=token, expires_at=invitation.expires_at, created_at=invitation.created_at)


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    invitation_id: UUID,
    organization: Organization = Depends(get_current_organization),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    _require_manager(db, organization, user)
    invitation = db.scalar(select(OrganizationInvitation).where(OrganizationInvitation.id == invitation_id, OrganizationInvitation.organization_id == organization.id, OrganizationInvitation.accepted_at.is_(None)))
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation introuvable.")
    db.delete(invitation)
    db.commit()


@invitations_router.get("/{token}", response_model=InvitationDetails)
def get_invitation(token: str, response: Response, db: Session = Depends(get_db)) -> InvitationDetails:
    response.headers["Cache-Control"] = "no-store"
    invitation = db.scalar(select(OrganizationInvitation).where(OrganizationInvitation.token_hash == _token_digest(token), OrganizationInvitation.accepted_at.is_(None)))
    if invitation is None or _expired(invitation.expires_at):
        raise HTTPException(status_code=404, detail="Cette invitation est invalide ou a expiré.")
    organization = db.get(Organization, invitation.organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Cette invitation est invalide ou a expiré.")
    return InvitationDetails(email=invitation.email, role=invitation.role, organization_name=organization.name, expires_at=invitation.expires_at)


@invitations_router.post("/{token}/accept", response_model=SessionResponse)
def accept_invitation(
    token: str,
    body: InvitationAcceptance,
    response: Response,
    session_cookie: str | None = Cookie(default=None, alias="session"),
    db: Session = Depends(get_db),
) -> SessionResponse:
    response.headers["Cache-Control"] = "no-store"
    invitation = db.scalar(select(OrganizationInvitation).where(OrganizationInvitation.token_hash == _token_digest(token), OrganizationInvitation.accepted_at.is_(None)).with_for_update())
    if invitation is None or _expired(invitation.expires_at):
        raise HTTPException(status_code=404, detail="Cette invitation est invalide, déjà utilisée ou expirée.")
    token_data = read_access_token(session_cookie) if session_cookie else None
    session_user = db.get(User, token_data[0]) if token_data else None
    if session_user and (not session_user.is_active or session_user.session_version != token_data[1] or session_user.email != invitation.email):
        raise HTTPException(status_code=403, detail="Connectez-vous avec l’adresse e-mail de l’invitation.")
    existing = db.scalar(select(User).where(User.email == invitation.email))
    if existing:
        if session_user is None or not session_user.is_active or session_user.session_version != token_data[1]:
            raise HTTPException(status_code=401, detail="Connectez-vous au compte invité avant d’accepter cette invitation.")
        if session_user.id != existing.id:
            raise HTTPException(status_code=403, detail="Cette invitation est destinée à une autre adresse e-mail.")
        user = existing
    else:
        if not body.full_name or not body.password:
            raise HTTPException(status_code=422, detail="Votre nom et un mot de passe d’au moins 12 caractères sont requis.")
        user = User(email=invitation.email, full_name=body.full_name.strip(), password_hash=hash_password(body.password))
        db.add(user)
        db.flush()
    if db.scalar(select(Membership.id).where(Membership.organization_id == invitation.organization_id, Membership.user_id == user.id)):
        raise HTTPException(status_code=409, detail="Ce compte est déjà membre de l’organisation.")
    db.add(Membership(organization_id=invitation.organization_id, user_id=user.id, role=invitation.role))
    invitation.accepted_at = _now()
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cette invitation a déjà été utilisée.")
    db.refresh(user)
    response.set_cookie(key="session", value=create_access_token(user.id, user.session_version), max_age=60 * 60 * 12, httponly=True, secure=get_settings().secure_cookies, samesite="lax", path="/")
    memberships = db.scalars(select(Membership).where(Membership.user_id == user.id).order_by(Membership.created_at)).all()
    organizations = []
    for membership in memberships:
        organization = db.get(Organization, membership.organization_id)
        if organization:
            organizations.append(OrganizationResponse(id=organization.id, name=organization.name, slug=organization.slug, role=membership.role.value))
    return SessionResponse(user=UserResponse(id=user.id, email=user.email, full_name=user.full_name), organizations=organizations)
