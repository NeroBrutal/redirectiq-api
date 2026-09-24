"""Async SQLAlchemy engine, session factory, and declarative base.

One engine per process, created lazily from Settings so importing this module
never opens a connection by itself (important for tests, which override the URL).
"""

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Shared declarative base — every SQLAlchemy model in src/app/models inherits this."""


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False, autoflush=False)


async def check_db_connection() -> bool:
    """Used by /health. Returns False instead of raising — health checks report, not crash."""
    try:
        async with get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: one session per request, committed at the boundary."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
        await session.commit()
