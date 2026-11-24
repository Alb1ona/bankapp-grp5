"""Små forespørgselshjælpere til ledger (bruges af API og tests)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transfer import LedgerEntry


def ledger_sum_for_transfer(db: Session, transfer_id: str) -> Decimal:
    """FR-11: summen af en overførsels ledger-poster skal være nul."""
    rows = db.execute(
        select(LedgerEntry.signed_amount).where(LedgerEntry.transfer_id == transfer_id)
    ).scalars().all()
    return sum((Decimal(x) for x in rows), Decimal("0.00"))
