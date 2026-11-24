"""Supportsager (tabeller: support_cases, support_messages) - P1."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base_types import GUID, new_uuid, utcnow


class SupportStatus(str, enum.Enum):
    AABEN = "AABEN"                     # Åben
    UNDER_BEHANDLING = "UNDER_BEHANDLING"
    LUKKET = "LUKKET"


class SupportCase(Base):
    __tablename__ = "support_cases"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(GUID, ForeignKey("customers.id"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[SupportStatus] = mapped_column(String(20), nullable=False, default=SupportStatus.AABEN)
    assigned_employee_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("employees.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    messages: Mapped[list["SupportMessage"]] = relationship(back_populates="case", order_by="SupportMessage.created_at")


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    case_id: Mapped[str] = mapped_column(GUID, ForeignKey("support_cases.id"), nullable=False, index=True)
    # sender_type: 'CUSTOMER' eller 'EMPLOYEE'
    sender_type: Mapped[str] = mapped_column(String(10), nullable=False)
    sender_id: Mapped[str] = mapped_column(GUID, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped[SupportCase] = relationship(back_populates="messages")
