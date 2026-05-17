from app.config import database_url_for_alembic, normalize_database_url


def test_normalize_railway_postgres_url() -> None:
    raw = "postgres://user:pass@host:5432/db"
    assert normalize_database_url(raw) == "postgresql+asyncpg://user:pass@host:5432/db"


def test_alembic_sync_postgres_url() -> None:
    async_url = "postgresql+asyncpg://user:pass@host/db"
    assert database_url_for_alembic(async_url) == "postgresql+psycopg2://user:pass@host/db"
