import re
import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import case, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from noomin_api.api.audit import record_audit
from noomin_api.api.dependencies import get_current_user
from noomin_api.core.config import get_settings
from noomin_api.core.security import create_access_token, create_csrf_token, hash_password, verify_password
from noomin_api.db.session import get_db
from noomin_api.models import AuthLoginThrottle, Membership, MembershipRole, Organization, User
from noomin_api.schemas.auth import LoginRequest, OrganizationResponse, RegisterRequest, SessionResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])
COOKIE_NAME = "session"
COOKIE_TTL = 60 * 60 * 12
LOGIN_FAILURE_LIMIT = 10
IP_FAILURE_LIMIT = 60
LOGIN_WINDOW = timedelta(minutes=15)


def _login_bucket(email: str, client_host: str | None) -> str:
    secret = get_settings().jwt_secret_key.encode("utf-8")
    identity = f"account|{email.lower()}|{client_host or 'unknown'}".encode("utf-8")
    return hmac.new(secret, identity, hashlib.sha256).hexdigest()


def _ip_bucket(client_host: str | None) -> str:
    secret = get_settings().jwt_secret_key.encode("utf-8")
    identity = f"ip|{client_host or 'unknown'}".encode("utf-8")
    return hmac.new(secret, identity, hashlib.sha256).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def _check_login_throttle(db: Session, bucket: str, now: datetime) -> None:
    record = db.get(AuthLoginThrottle, bucket)
    if record and record.blocked_until and _as_utc(record.blocked_until) > now:
        retry_after = max(1, int((_as_utc(record.blocked_until) - now).total_seconds()))
        raise HTTPException(status_code=429, detail="Trop de tentatives. Réessayez dans 15 minutes.", headers={"Retry-After": str(retry_after)})
    if record and _as_utc(record.window_started_at) <= now - LOGIN_WINDOW:
        db.delete(record)
        db.commit()


def _record_failed_login(db: Session, bucket: str, now: datetime, failure_limit: int) -> bool:
    reset_window = AuthLoginThrottle.window_started_at <= now - LOGIN_WINDOW
    values = {"bucket_key": bucket, "failures": 1, "window_started_at": now, "blocked_until": None}
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        from sqlalchemy.dialects.sqlite import insert
    else:
        from sqlalchemy.dialects.postgresql import insert
    statement = insert(AuthLoginThrottle).values(**values).on_conflict_do_update(
        index_elements=[AuthLoginThrottle.bucket_key],
        set_={
            "failures": case((reset_window, 1), else_=AuthLoginThrottle.failures + 1),
            "window_started_at": case((reset_window, now), else_=AuthLoginThrottle.window_started_at),
            "blocked_until": case((reset_window, None), else_=AuthLoginThrottle.blocked_until),
        },
    )
    db.execute(statement)
    db.flush()
    db.expire_all()
    record = db.get(AuthLoginThrottle, bucket)
    blocked = bool(record and record.failures >= failure_limit)
    if blocked and record:
        record.blocked_until = now + LOGIN_WINDOW
    db.commit()
    return blocked


def _set_session_cookie(response: Response, user: User) -> None:
    token = create_access_token(user.id, user.session_version)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_TTL,
        httponly=True,
        secure=get_settings().secure_cookies,
        samesite="lax",
        path="/",
    )
    response.set_cookie(key="csrf_token", value=create_csrf_token(token), max_age=COOKIE_TTL, httponly=False, secure=get_settings().secure_cookies, samesite="lax", path="/")


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
        record_audit(db, organization.id, user.id, "organization.created", "organization", organization.id)
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Impossible de créer le compte avec ces informations.") from exc
    _set_session_cookie(response, user)
    return _session_payload(user, db)


@router.post("/login", response_model=SessionResponse)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> SessionResponse:
    email = str(body.email).strip().lower()
    now = datetime.now(UTC)
    db.execute(delete(AuthLoginThrottle).where(AuthLoginThrottle.window_started_at < now - timedelta(days=1)))
    client_host = request.client.host if request.client else None
    bucket = _login_bucket(email, client_host)
    ip_bucket = _ip_bucket(client_host)
    _check_login_throttle(db, bucket, now)
    _check_login_throttle(db, ip_bucket, now)
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        blocked = _record_failed_login(db, bucket, now, LOGIN_FAILURE_LIMIT)
        blocked = _record_failed_login(db, ip_bucket, now, IP_FAILURE_LIMIT) or blocked
        if blocked:
            raise HTTPException(status_code=429, detail="Trop de tentatives. Réessayez dans 15 minutes.", headers={"Retry-After": str(int(LOGIN_WINDOW.total_seconds()))})
        raise HTTPException(status_code=401, detail="Adresse e-mail ou mot de passe incorrect.")
    db.execute(delete(AuthLoginThrottle).where(AuthLoginThrottle.bucket_key == bucket))
    db.commit()
    _set_session_cookie(response, user)
    return _session_payload(user, db)


@router.get("/session", response_model=SessionResponse)
def current_session(request: Request, response: Response, db: Session = Depends(get_db)) -> SessionResponse:
    token = request.cookies.get(COOKIE_NAME)
    from noomin_api.core.security import read_access_token

    token_data = read_access_token(token) if token else None
    user_id, token_version = token_data if token_data else (None, None)
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.is_active or user.session_version != token_version:
        raise HTTPException(status_code=401, detail="Session invalide ou expirée.")
    if token:
        response.set_cookie(key="csrf_token", value=create_csrf_token(token), max_age=COOKIE_TTL, httponly=False, secure=get_settings().secure_cookies, samesite="lax", path="/")
    return _session_payload(user, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    user.session_version += 1
    db.commit()
    response.delete_cookie(key=COOKIE_NAME, path="/", httponly=True, secure=get_settings().secure_cookies, samesite="lax")
    response.delete_cookie(key="csrf_token", path="/", httponly=False, secure=get_settings().secure_cookies, samesite="lax")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
