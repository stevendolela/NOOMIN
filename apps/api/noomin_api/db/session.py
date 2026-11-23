from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from noomin_api.core.config import get_settings

database_url = get_settings().database_url
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# The local SQLite preview does not run the PostgreSQL Alembic chain. Create
# only additive feature tables there so existing preview data remains intact.
if database_url.startswith("sqlite"):
    from noomin_api.models import AuditLog, AuthLoginThrottle, OrganizationAPIKey, OrganizationInvitation

    OrganizationInvitation.__table__.create(engine, checkfirst=True)
    AuthLoginThrottle.__table__.create(engine, checkfirst=True)
    AuditLog.__table__.create(engine, checkfirst=True)
    OrganizationAPIKey.__table__.create(engine, checkfirst=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
