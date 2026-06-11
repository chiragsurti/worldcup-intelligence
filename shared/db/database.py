"""Database engine factory and session management."""

import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from shared.db.models import Base

_engine = None
_SessionLocal = None


def get_engine(database_url: str | None = None):
    """Create or return the singleton engine."""
    global _engine
    if _engine is None:
        url = database_url or os.environ.get("DATABASE_URL", "sqlite:///./data/worldcup.db")
        # Ensure directory exists for SQLite
        if url.startswith("sqlite"):
            db_path = url.replace("sqlite:///", "").replace("sqlite:////", "/")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        _engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})

        # Set journal_mode=DELETE for Azure Files compatibility
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=DELETE")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

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
