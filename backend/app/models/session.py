"""
Server-side sessioner (tabel: sessions).

SEC-02: tilfældige tokens gemmes KUN som hash server-side. Selve token-værdien
lever i en HttpOnly+Secure cookie hos klienten og gemmes aldrig i klartekst.
"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base_types import GUID, new_uuid, utcnow


class PrincipalType(str, enum.Enum):
    CUSTOMER = "CUSTOMER"
    EMPLOYEE = "EMPLOYEE"


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    principal_type: Mapped[PrincipalType] = mapped_column(String(10), nullable=False)
    principal_id: Mapped[str] = mapped_column(GUID, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # AD-06: tidspunkt for seneste AD-genvalidering (kun medarbejdere).
    last_revalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Cachet rolleliste for medarbejdere (kommasepareret), sat ved login/genvalidering.
    roles_cache: Mapped[str | None] = mapped_column(String(300), nullable=True)
