from datetime import UTC, datetime, timedelta
import hmac
from uuid import UUID

import jwt
from pwdlib import PasswordHash

from noomin_api.core.config import get_settings

password_hash = PasswordHash.recommended()
ALGORITHM = "HS256"
TOKEN_TTL = timedelta(hours=12)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(user_id: UUID, session_version: int = 0) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "ver": session_version, "iat": now, "exp": now + TOKEN_TTL}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_csrf_token(session_token: str) -> str:
    secret = get_settings().jwt_secret_key.encode("utf-8")
    return hmac.digest(secret, f"csrf:{session_token}".encode("utf-8"), "sha256").hex()


def read_access_token(token: str) -> tuple[UUID, int] | None:
    try:
        payload = jwt.decode(token, get_settings().jwt_secret_key, algorithms=[ALGORITHM])
        return UUID(payload["sub"]), int(payload.get("ver", 0))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
