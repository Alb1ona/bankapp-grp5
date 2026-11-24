"""Medarbejder (tabel: employees). AD-02/AD-04: ingen passwords, objectGUID er stabil id."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base_types import GUID, new_uuid, utcnow


class Employee(Base):
    """
    Lokal spejling af en AD-medarbejder - bruges kun til stabile audit-referencer.
    Roller/grupper gemmes IKKE autoritativt her; de kommer altid fra AD ved login
    (AD-03/AD-06). Ingen adgangskoder gemmes (AD-02).
    """

    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    ad_object_guid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    ad_username: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
