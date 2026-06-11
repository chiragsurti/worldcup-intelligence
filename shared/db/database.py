"""Database engine factory and session management."""

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.db.models import Base

_engine = None
_SessionLocal = None


def get_engine(database_url: str | None = None):
    """Create or return the singleton engine."""
    global _engine
    if _engine is None:
        url = database_url or os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/worldcup"
        )
        _engine = create_engine(url, echo=False, pool_pre_ping=True)

    return _engine


def get_session_factory(database_url: str | None = None) -> sessionmaker:
    """Get a session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine(database_url)
        _SessionLocal = sessionmaker(bind=engine)
    return _SessionLocal


@contextmanager
def get_session(database_url: str | None = None):
    """Context manager yielding a SQLAlchemy session with auto-commit/rollback."""
    factory = get_session_factory(database_url)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(database_url: str | None = None):
    """Create all tables if they don't exist."""
    engine = get_engine(database_url)
    Base.metadata.create_all(bind=engine)
