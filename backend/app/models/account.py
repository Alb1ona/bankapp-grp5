"""Konti (tabel: accounts)."""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base_types import GUID, new_uuid, utcnow


class AccountType(str, enum.Enum):
    LOENKONTO = "LOENKONTO"      # lønkonto
    OPSPARING = "OPSPARING"      # opsparing
    BUDGET = "BUDGET"            # budgetkonto


class AccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"           # spærret (FR-20) - må ikke være afsender (FR-08)
    CLOSED = "CLOSED"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    customer_id: Mapped[str] = mapped_column(GUID, ForeignKey("customers.id"), nullable=False, index=True)
    account_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    account_type: Mapped[AccountType] = mapped_column(String(20), nullable=False)
    # DB-02: beløb som NUMERIC(18,2), aldrig float.
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="DKK")
    status: Mapped[AccountStatus] = mapped_column(String(10), nullable=False, default=AccountStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    customer: Mapped["Customer"] = relationship(back_populates="accounts")

    @property
    def masked_account_number(self) -> str:
        """LOG-03: aldrig fuldt kontonummer i logs - vis kun sidste 4 cifre."""
        n = self.account_number
        return f"****{n[-4:]}" if len(n) >= 4 else "****"
