"""
Database-opsætning (DB-06).

SQLAlchemy engine + session. Forbindelsen konfigureres via DATABASE_URL og
understøtter TLS-verifikation (sslmode/sslrootcert) i produktion.

Til lokal udvikling UDEN PostgreSQL kan man sætte
    DATABASE_URL=sqlite+pysqlite:///./bankapp_dev.db
men bemærk: række-låsning (DB-03) og NUMERIC-præcision testes bedst mod
rigtig PostgreSQL, som specen foreskriver.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.config import settings


class Base(DeclarativeBase):
    """Fælles base for alle ORM-modeller."""
    pass


def _build_connect_args() -> dict:
    url = settings.database_url
    if url.startswith("postgresql"):
        args: dict = {"sslmode": settings.database_sslmode}
        if settings.database_sslrootcert:
            args["sslrootcert"] = settings.database_sslrootcert
        return args
    if url.startswith("sqlite"):
        # SQLite kræver denne flag for brug på tværs af tråde i test.
        return {"check_same_thread": False}
    return {}


engine = create_engine(
    settings.database_url,
    connect_args=_build_connect_args(),
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, future=True
)


def get_db() -> Iterator[Session]:
    """FastAPI-dependency: giver en DB-session pr. request og lukker den igen."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
