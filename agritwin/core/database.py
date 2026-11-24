"""
Database Engine & Session Management for AgriTwin Pakistan.
Supports PostgreSQL (production) and SQLite (development/tests) seamlessly.
"""

from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from agritwin.core.config import settings
from agritwin.core.models import Base


def create_db_engine(database_url: str = settings.database_url) -> Engine:
    """Create SQLAlchemy engine with appropriate dialect arguments."""
    is_sqlite = database_url.startswith("sqlite")
    connect_args = {}

    if is_sqlite:
        connect_args["check_same_thread"] = False

    engine = create_engine(
        database_url,
        connect_args=connect_args,
        echo=False,
        future=True
    )

    # Enable foreign key enforcement for SQLite
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Global engine and session factory
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(target_engine: Engine = engine) -> None:
    """Create all tables in the database if they do not already exist."""
    Base.metadata.create_all(bind=target_engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency injection helper yielding an active database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
