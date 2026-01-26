from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


def _create_engine() -> Engine:
    url = settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        # Needed for SQLite when used in multi-threaded contexts (e.g. tests)
        connect_args["check_same_thread"] = False
    return create_engine(url, echo=False, future=True, pool_pre_ping=True, connect_args=connect_args)


engine: Engine = _create_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
)