from datetime import UTC, datetime
import hashlib
import threading
import time
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from redis import Redis
from redis.exceptions import RedisError

from noomin_api.core.config import get_settings
from noomin_api.core.security import read_access_token
from noomin_api.db.session import get_db
from noomin_api.models import Membership, Organization, OrganizationAPIKey, User

API_KEY_RATE_LIMIT = 120
API_KEY_RATE_WINDOW_SECONDS = 60
_local_rate_lock = threading.Lock()
_local_rate_buckets: dict[str, tuple[int, int]] = {}


def _consume_local_rate_limit(api_key_id: UUID, now: float | None = None) -> tuple[int, int]:
    current = time.time() if now is None else now
    bucket = int(current // API_KEY_RATE_WINDOW_SECONDS)
    reset_at = (bucket + 1) * API_KEY_RATE_WINDOW_SECONDS
    key = str(api_key_id)
    with _local_rate_lock:
        count, previous_bucket = _local_rate_buckets.get(key, (0, bucket))
        count = count + 1 if previous_bucket == bucket else 1
        _local_rate_buckets[key] = (count, bucket)
        if len(_local_rate_buckets) > 10_000:
            expired_keys = [stored_key for stored_key, (_, stored_bucket) in _local_rate_buckets.items() if stored_bucket < bucket - 1]
            for stored_key in expired_keys:
                _local_rate_buckets.pop(stored_key, None)
    return count, reset_at


def _consume_api_key_rate_limit(api_key_id: UUID) -> tuple[int, int]:
    settings = get_settings()
    # SQLite preview and tests have no shared Redis process; this fallback is deliberately local.
    if settings.environment.lower() in {"development", "dev", "local", "test"} and settings.database_url.startswith("sqlite"):
        return _consume_local_rate_limit(api_key_id)

    redis_client = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
    try:
        count, ttl = redis_client.eval(
            "local n = redis.call('INCR', KEYS[1]); if n == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]); end; return {n, redis.call('TTL', KEYS[1])}",
            1,
            f"noomin:api-key-rate:{api_key_id}",
            API_KEY_RATE_WINDOW_SECONDS,
        )
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Le contrôle de débit est temporairement indisponible.") from exc
    finally:
        redis_client.close()
    return int(count), int(time.time()) + max(0, int(ttl))


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
        try:
            request_count, reset_at = _consume_api_key_rate_limit(api_key.id)
        except HTTPException:
            raise
        response.headers["X-RateLimit-Limit"] = str(API_KEY_RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(max(0, API_KEY_RATE_LIMIT - request_count))
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        if request_count > API_KEY_RATE_LIMIT:
            retry_after = max(1, reset_at - int(time.time()))
            response.headers["Retry-After"] = str(retry_after)
            raise HTTPException(status_code=429, detail="Quota API atteint. Réessayez après la fenêtre indiquée.", headers={"Retry-After": str(retry_after)})
        api_key.last_used_at = now
        db.commit()
        return api_key

    return dependency
