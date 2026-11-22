from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from noomin_api.core.security import read_access_token
from noomin_api.db.session import get_db
from noomin_api.models import Membership, Organization, User


def get_current_user(session: str | None = Cookie(default=None), db: Session = Depends(get_db)) -> User:
    user_id = read_access_token(session) if session else None
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée.")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
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
