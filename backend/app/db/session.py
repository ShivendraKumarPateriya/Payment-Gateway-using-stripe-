"""Database engine/session utilities and FastAPI dependency provider."""

from __future__ import annotations

from functools import lru_cache
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create and cache SQLAlchemy engine from configured database URL."""

    settings = get_settings()
    database_url = settings.database_url

    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Create and cache sessionmaker factory bound to project engine."""

    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request."""

    session_factory = get_session_factory()
    db_session = session_factory()

    try:
        yield db_session
    finally:
        db_session.close()
