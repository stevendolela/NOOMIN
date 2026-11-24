"""Database URL helpers shared by the API and Alembic."""


def normalize_database_url(database_url: str) -> str:
    """Use the psycopg 3 SQLAlchemy dialect for standard PostgreSQL URLs."""
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgres://")
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    return database_url
