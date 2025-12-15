"""
RyxHub Exam System - Database Connection Management
Version: 1.0.0
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .models import Base


# ============================================================================
# Configuration
# ============================================================================

# Database URL from environment or default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/ryxhub"
)

# For SQLite fallback (development without PostgreSQL)
SQLITE_URL = os.getenv(
    "SQLITE_URL",
    "sqlite:///./ryxhub_exam.db"
)

# Use SQLite if PostgreSQL is not available
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"

# Connection pool settings
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))


# ============================================================================
# Engine Creation
# ============================================================================

def create_db_engine():
    """Create SQLAlchemy engine with appropriate settings"""

    if USE_SQLITE:
        # SQLite for development/testing
        engine = create_engine(
            SQLITE_URL,
            connect_args={"check_same_thread": False},
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
        )

        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        # PostgreSQL for production
        engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=POOL_SIZE,
            max_overflow=MAX_OVERFLOW,
            pool_timeout=POOL_TIMEOUT,
            pool_pre_ping=True,  # Verify connections before use
            echo=os.getenv("DB_ECHO", "false").lower() == "true",
        )

    return engine


# Create engine and session factory
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ============================================================================
# Database Initialization
# ============================================================================

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized: {'SQLite' if USE_SQLITE else 'PostgreSQL'}")


def drop_db():
    """Drop all database tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)
    print("All database tables dropped")


# ============================================================================
# Session Management
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions (for non-FastAPI code).

    Usage:
        with get_db_context() as db:
            items = db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================================
# Health Check
# ============================================================================

def check_db_health() -> dict:
    """Check database connection health"""
    try:
        with get_db_context() as db:
            # Execute simple query
            result = db.execute("SELECT 1").scalar()
            return {
                "status": "healthy",
                "database": "SQLite" if USE_SQLITE else "PostgreSQL",
                "connection": "ok",
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "SQLite" if USE_SQLITE else "PostgreSQL",
            "error": str(e),
        }


# ============================================================================
# Utility Functions
# ============================================================================

def get_or_create(db: Session, model, defaults=None, **kwargs):
    """
    Get existing record or create new one.

    Usage:
        user, created = get_or_create(
            db, User,
            defaults={"email": "new@example.com"},
            username="john"
        )
    """
    instance = db.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        params = {**kwargs, **(defaults or {})}
        instance = model(**params)
        db.add(instance)
        db.commit()
        db.refresh(instance)
        return instance, True
