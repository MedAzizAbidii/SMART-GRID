"""Database connection and session management."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://admin:admin123@localhost:5432/smartgrid"
)

_connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {"connect_timeout": 2}

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,
    echo=False,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Export SessionLocal for direct use
__all__ = ['engine', 'SessionLocal', 'get_db']


def get_db() -> Session:
    """Dependency for FastAPI to inject database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
