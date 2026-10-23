"""Database engine and session lifecycle.

The only module that knows how to reach Postgres (Supabase). It holds no SQL
and no business logic; every query lives in ``repo.py``.
"""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

def build_engine(url:str) -> Engine:
    """Builds a SQLAlchemy engine."""
    return create_engine(url, pool_pre_ping=True)

def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Builds a SQLAlchemy session factory."""
    return sessionmaker(bind=engine)

engine = build_engine(get_settings().database_url)
SessionLocal = build_session_factory(engine)

def get_session() -> Iterator[Session]:
    """FastAPI dependency: one Session per request, always closed."""
    with SessionLocal() as session:
        yield session