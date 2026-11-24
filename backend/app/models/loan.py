"""Låneansøgninger (tabel: loan_applications)."""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base_types import GUID, new_uuid, utcnow


class LoanStatus(str, enum.Enum):
    AFVENTER = "AFVENTER"       # Afventer
    GODKENDT = "GODKENDT"       # Godkendt
    AFVIST = "AFVIST"           # Afvist


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(GUID, ForeignKey("customers.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    loan_type: Mapped[str] = mapped_column(String(40), nullable=False)
    duration_months: Mapped[int] = mapped_column(nullable=False)
    purpose: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[LoanStatus] = mapped_column(String(10), nullable=False, default=LoanStatus.AFVENTER)
    # FR-18: medarbejder og begrundelse gemmes ved afgørelse.
    reviewed_by_employee_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("employees.id"), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
