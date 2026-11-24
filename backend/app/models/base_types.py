"""
Genbrugelige kolonnetyper og hjælpere.

GUID: portabel UUID-type (native UUID på PostgreSQL, CHAR(36) ellers),
så vi kan udvikle lokalt og køre mod PostgreSQL i produktion.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    """Tidsstempel i UTC (LOG-01, DB-krav om konsistent tid)."""
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class GUID(TypeDecorator):
    """Platform-uafhængig UUID gemt som streng i Python."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return str(value)
