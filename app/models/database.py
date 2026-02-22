"""
Database configuration and session management using SQLAlchemy and MySQL.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

# Database URL configuration
DATABASE_USER = os.getenv("DB_USER", "root")
DATABASE_PASSWORD = os.getenv("DB_PASSWORD", "root@123")
DATABASE_HOST = os.getenv("DB_HOST", "localhost")
DATABASE_PORT = os.getenv("DB_PORT", "3306")
DATABASE_NAME = os.getenv("DB_NAME", "timetable_db1")

# URL-encode the password to handle special characters like '@', '#', etc.
SQLALCHEMY_DATABASE_URL = (
    f"mysql+pymysql://{DATABASE_USER}:{quote_plus(DATABASE_PASSWORD)}"
    f"@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
)

# Create engine with connection pooling
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    future=True,
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


def drop_db():
    """
    Drop all tables. Use with caution in production!
    """
    from app.models.models import Base
    Base.metadata.drop_all(bind=engine)


def close_db():
    """Close database connection pool."""
    engine.dispose()
