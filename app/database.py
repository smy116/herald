"""Database engine, session, and dependency injection."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

# Ensure data directory exists for SQLite
db_path = settings.DATABASE_URL.replace("sqlite:///", "")
db_dir = os.path.dirname(db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},  # SQLite only
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    """Create all tables and apply lightweight migrations."""
    from app import models  # noqa: F401 – ensure models are registered
    Base.metadata.create_all(bind=engine)

    # Auto-migrate: add missing columns to existing tables
    _migrate_add_columns()


def _migrate_add_columns():
    """Add any new columns that don't exist in the current schema."""
    migrations = [
        ("message_logs", "retry_count", "INTEGER DEFAULT 0"),
    ]
    with engine.connect() as conn:
        for table, column, col_type in migrations:
            try:
                conn.execute(
                    __import__("sqlalchemy").text(
                        f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
                    )
                )
                conn.commit()
            except Exception:
                # Column already exists — ignore
                conn.rollback()


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
