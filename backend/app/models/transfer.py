"""
Overførsler og dobbelt bogføring (tabeller: transfers, ledger_entries).

FR-09/FR-11: hver overførsel giver to modsatrettede ledger-posteringer,
hvis sum er nul. DB-02: NUMERIC(18,2).
"""
from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base_types import GUID, new_uuid, utcnow


class TransferStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class LedgerEntryType(str, enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    OPENING_BALANCE = "OPENING_BALANCE"   # DB-07: markeret åbningssaldo


class Transfer(Base):
    __tablename__ = "transfers"
    # DB-04: idempotency key unik inden for den initierende kunde.
    __table_args__ = (
        UniqueConstraint("initiated_by_customer_id", "idempotency_key",
                         name="uq_transfer_idempotency"),
    )

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    sender_account_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("accounts.id"), nullable=True)
    receiver_account_id: Mapped[str] = mapped_column(GUID, ForeignKey("accounts.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[TransferStatus] = mapped_column(String(10), nullable=False, default=TransferStatus.PENDING)
    description: Mapped[str | None] = mapped_column(String(140), nullable=True)
    initiated_by_customer_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("customers.id"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ledger_entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="transfer")


class LedgerEntry(Base):
    """
    Én bogføringspost. signed_amount er negativ for debet, positiv for kredit.
    FR-11: summen af de to posteringer i én overførsel er nul.
    """

    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    transfer_id: Mapped[str | None] = mapped_column(GUID, ForeignKey("transfers.id"), nullable=True, index=True)
    account_id: Mapped[str] = mapped_column(GUID, ForeignKey("accounts.id"), nullable=False, index=True)
    signed_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    entry_type: Mapped[LedgerEntryType] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    transfer: Mapped["Transfer | None"] = relationship(back_populates="ledger_entries")
