"""
Database configuration and session management using SQLAlchemy and MySQL.
Includes lightweight startup schema compatibility upgrades.
"""

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL configuration
DATABASE_USER = os.getenv("DB_USER", "root")
DATABASE_PASSWORD = os.getenv("DB_PASSWORD", "password")
DATABASE_HOST = os.getenv("DB_HOST", "localhost")
DATABASE_PORT = os.getenv("DB_PORT", "3306")
DATABASE_NAME = os.getenv("DB_NAME", "timetable_db")

SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"

# Create engine with connection pooling
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting a database session in FastAPI.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database - create all tables.
    """
    from app.models.models import Base
    Base.metadata.create_all(bind=engine)
    _ensure_legacy_schema_compatibility()


def _ensure_legacy_schema_compatibility() -> None:
    """
    Best-effort compatibility patching for databases created by older code versions.
    This avoids runtime 500s when new columns/enums are referenced by the API.
    """
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as conn:
        if "timetable_entries" in table_names:
            columns = {col["name"] for col in inspector.get_columns("timetable_entries")}
            if "version_id" not in columns:
                conn.execute(text("ALTER TABLE timetable_entries ADD COLUMN version_id INTEGER NULL"))

            index_names = {idx["name"] for idx in inspector.get_indexes("timetable_entries")}
            if "ix_timetable_version" not in index_names:
                conn.execute(text("CREATE INDEX ix_timetable_version ON timetable_entries (version_id)"))

            # Expand enum values for session_type if needed.
            session_col = None
            for col in inspector.get_columns("timetable_entries"):
                if col.get("name") == "session_type":
                    session_col = col
                    break

            required_session_values = {
                "LECTURE", "TUTORIAL", "LAB", "SEMINAR", "CLUB", "BREAK", "EXTRACURRICULAR"
            }
            if session_col is not None:
                current_values = set(getattr(session_col.get("type"), "enums", []) or [])
                if current_values and not required_session_values.issubset(current_values):
                    conn.execute(text(
                        "ALTER TABLE timetable_entries MODIFY COLUMN session_type "
                        "ENUM('LECTURE','TUTORIAL','LAB','SEMINAR','CLUB','BREAK','EXTRACURRICULAR') NOT NULL"
                    ))

        if "constraint_configs" in table_names:
            cfg_columns = {col["name"] for col in inspector.get_columns("constraint_configs")}
            if "tea_break_2_after_period" not in cfg_columns:
                conn.execute(text(
                    "ALTER TABLE constraint_configs ADD COLUMN tea_break_2_after_period INTEGER DEFAULT 6"
                ))
            if "tea_break_2_duration" not in cfg_columns:
                conn.execute(text(
                    "ALTER TABLE constraint_configs ADD COLUMN tea_break_2_duration INTEGER DEFAULT 15"
                ))


def drop_db():
    """
    Drop all tables. Use with caution in production!
    """
    from app.models.models import Base
    Base.metadata.drop_all(bind=engine)


def close_db():
    """Close database connection pool."""
    engine.dispose()
