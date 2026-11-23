from datetime import UTC, datetime
import hashlib
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from noomin_api.core.security import read_access_token
from noomin_api.db.session import get_db
from noomin_api.models import Membership, Organization, OrganizationAPIKey, User


def get_current_user(session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User:
    token_data = read_access_token(session) if session else None
    if token_data is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée.")
    user_id, token_version = token_data
    user = db.get(User, user_id)
    if user is None or not user.is_active or user.session_version != token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte indisponible.")
    return user


def get_current_organization(
    organization_id: UUID = Header(alias="X-Organization-ID"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    membership = db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.organization_id == organization_id))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Vous n’avez pas accès à cette organisation.")
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation introuvable.")
    return organization


def require_api_scope(scope: str):
    def dependency(
        response: Response,
        authorization: str | None = Header(default=None),
        db: Session = Depends(get_db),
    ) -> OrganizationAPIKey:
        response.headers["Cache-Control"] = "no-store"
        scheme, _, secret = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not secret.startswith("noomin_live_"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clé API invalide ou manquante.", headers={"WWW-Authenticate": "Bearer"})
        key_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        api_key = db.scalar(select(OrganizationAPIKey).where(OrganizationAPIKey.key_hash == key_hash))
        now = datetime.now(UTC)
        expires_at = api_key.expires_at if api_key else None
        if api_key is None or api_key.revoked_at is not None or (expires_at is not None and (expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at) <= now):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Clé API invalide, expirée ou révoquée.", headers={"WWW-Authenticate": "Bearer"})
        if scope not in api_key.scopes:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette clé API ne possède pas l’autorisation requise.")
        api_key.last_used_at = now
        db.commit()
        return api_key

    return dependency
