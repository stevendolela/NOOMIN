from noomin_api.db.url import normalize_database_url


def test_normalizes_supabase_postgresql_url_to_psycopg_driver() -> None:
    url = "postgresql://postgres.project-ref:secret@pooler.example:5432/postgres?sslmode=require"

    assert normalize_database_url(url) == "postgresql+psycopg://postgres.project-ref:secret@pooler.example:5432/postgres?sslmode=require"


def test_normalizes_legacy_postgres_scheme() -> None:
    assert normalize_database_url("postgres://user:secret@host/database") == "postgresql+psycopg://user:secret@host/database"


def test_preserves_existing_driver_and_sqlite_urls() -> None:
    assert normalize_database_url("postgresql+psycopg://user:secret@host/database") == "postgresql+psycopg://user:secret@host/database"
    assert normalize_database_url("sqlite:///./noomin.db") == "sqlite:///./noomin.db"
