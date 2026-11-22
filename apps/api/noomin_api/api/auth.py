import re
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from noomin_api.api.dependencies import get_current_user
from noomin_api.core.config import get_settings
from noomin_api.core.security import create_access_token, hash_password, verify_password
from noomin_api.db.session import get_db
from noomin_api.models import Membership, MembershipRole, Organization, User
from noomin_api.schemas.auth import LoginRequest, OrganizationResponse, RegisterRequest, SessionResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])
COOKIE_NAME = "session"
COOKIE_TTL = 60 * 60 * 12


def _set_session_cookie(response: Response, user_id) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_access_token(user_id),
        max_age=COOKIE_TTL,
        httponly=True,
        secure=get_settings().secure_cookies,
        samesite="lax",
        path="/",
    )


def _session_payload(user: User, db: Session) -> SessionResponse:
    memberships = db.scalars(select(Membership).where(Membership.user_id == user.id).order_by(Membership.created_at)).all()
    organizations = []
    for membership in memberships:
        organization = db.get(Organization, membership.organization_id)
        if organization:
            organizations.append(OrganizationResponse(id=organization.id, name=organization.name, slug=organization.slug, role=membership.role.value))
    return SessionResponse(user=UserResponse(id=user.id, email=user.email, full_name=user.full_name), organizations=organizations)


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> SessionResponse:
    email = str(body.email).strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Cette adresse e-mail est déjà utilisée.")
    slug_base = re.sub(r"[^a-z0-9]+", "-", body.organization_name.lower()).strip("-")[:60] or "organisation"
    organization = Organization(name=body.organization_name.strip(), slug=f"{slug_base}-{uuid4().hex[:8]}")
    user = User(email=email, full_name=body.full_name.strip(), password_hash=hash_password(body.password))
    db.add_all([organization, user])
    try:
        db.flush()
        db.add(Membership(organization_id=organization.id, user_id=user.id, role=MembershipRole.OWNER))
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Impossible de créer le compte avec ces informations.") from exc
    _set_session_cookie(response, user.id)
    return _session_payload(user, db)


@router.post("/login", response_model=SessionResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)) -> SessionResponse:
    email = str(body.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Adresse e-mail ou mot de passe incorrect.")
    _set_session_cookie(response, user.id)
    return _session_payload(user, db)


@router.get("/session", response_model=SessionResponse)
def current_session(request: Request, db: Session = Depends(get_db)) -> SessionResponse:
    token = request.cookies.get(COOKIE_NAME)
    from noomin_api.core.security import read_access_token

    user_id = read_access_token(token) if token else None
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée.")
    return _session_payload(user, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, user: User = Depends(get_current_user)) -> Response:
    response.delete_cookie(key=COOKIE_NAME, path="/", httponly=True, secure=get_settings().secure_cookies, samesite="lax")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
