"""Shared pytest fixtures: an isolated Postgres test database + async HTTP clients.

Global Rule 5 (plan.md): every phase adds tests. Tests run against a real Postgres
database (a separate one from dev, same local server) rather than sqlite, so
dialect-specific behavior added in later phases (JSONB, arrays, etc.) is exercised
the same way it will be in production.
"""

import os
from collections.abc import AsyncIterator

# Point Settings at a separate test database and Redis logical db BEFORE importing
# any app module, so get_settings() picks these up instead of the dev .env values.
# Clearing DATABASE_URL (set as a full URL in .env) falls back to building it from
# the individual POSTGRES_* parts, which we then override just the db name of.
os.environ["DATABASE_URL"] = ""
os.environ["POSTGRES_DB"] = "redirectiq_test"
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5433")
os.environ.setdefault("POSTGRES_USER", "redirectiq")
os.environ.setdefault("POSTGRES_PASSWORD", "redirectiq")
os.environ["REDIS_URL"] = "redis://localhost:6380/15"
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:4321")

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.db import Base, get_db


async def _ensure_test_database_exists(settings: Settings) -> None:
    """CREATE DATABASE has no IF NOT EXISTS in Postgres, so check first."""
    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        # the always-present maintenance db, used only to issue CREATE DATABASE
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", settings.postgres_db
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{settings.postgres_db}"')
    finally:
        await conn.close()


@pytest.fixture
def settings() -> Settings:
    return get_settings()


@pytest.fixture
async def db_session(settings: Settings) -> AsyncIterator[AsyncSession]:
    """One isolated session per test: fresh schema, rolled back on teardown."""
    await _ensure_test_database_exists(settings)
    engine = create_async_engine(settings.sqlalchemy_database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Async HTTP client against the api app, with get_db overridden to the test session."""
    from app.api_main import app

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def redirect_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Async HTTP client against the redirect app."""
    from app.core.db import get_db as redirect_get_db
    from app.redirect_main import app

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[redirect_get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
