"""Database connection and session management for CustomerVoice AI.

Configures SQLAlchemy engine, session factory, and base model declarative class.
Reads connection parameters exclusively from environment variables via Settings.
"""

from contextlib import contextmanager
import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from src.config import settings

logger = logging.getLogger(__name__)

# Base class for all SQLAlchemy ORM models
Base = declarative_base()

def normalize_database_url(url: str) -> str:
    """Normalize database connection URL to ensure compatibility with psycopg2 driver.
    
    Transforms postgresql:// or postgres:// to postgresql+psycopg2://.
    Leaves other dialects (e.g., sqlite://, postgresql+psycopg2://) unchanged.
    """
    if not url:
        return url
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def mask_database_url(url: str) -> str:
    """Safely mask password credentials in a database URL for logging or display."""
    if not url:
        return ""
    try:
        from sqlalchemy.engine.url import make_url
        norm = normalize_database_url(url)
        return make_url(norm).render_as_string(hide_password=True)
    except Exception:
        import re
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)


# Configure engine with connection pooling
# Never hardcode database credentials; pull strictly from settings
DATABASE_URL = normalize_database_url(settings.DATABASE_URL)

# For SQLite (in testing), check_same_thread needs to be False
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session lifecycle management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager for standalone script session handling with rollback safety."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Create all configured tables in target database."""
    Base.metadata.create_all(bind=engine)
    logger.info("Initialized database tables with bind: %s", engine.url)
