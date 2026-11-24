"""
Audit-hændelser i databasen (tabel: audit_events).

DB-05: append-only for normale applikationsroller. Applikationen tilbyder
ingen UPDATE/DELETE på denne tabel; AUDITOR-rollen er skrivebeskyttet (FR-21).
Dette supplerer JSON-filloggen til Wazuh (afsnit 8).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base_types import GUID, new_uuid, utcnow


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="INFO")
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
