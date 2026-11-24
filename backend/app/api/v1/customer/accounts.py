"""Kundens konti og transaktioner (FR-04, FR-05, KUN-02, SEC-06)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentCustomer, get_current_customer, get_db
from app.core import audit
from app.core.errors import NotFoundError
from app.models.account import Account
from app.models.transfer import LedgerEntry, Transfer
from app.schemas.customer import AccountResponse, TransactionResponse

router = APIRouter(prefix="/api/v1/customer/accounts", tags=["customer-accounts"])


@router.get("", response_model=list[AccountResponse])
def list_accounts(
    current: CurrentCustomer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(Account).where(Account.customer_id == current.customer.id)
        .order_by(Account.created_at)
    ).scalars().all()
    return [
        AccountResponse(
            id=a.id, account_number=a.account_number, account_type=a.account_type,
            balance=a.balance, currency=a.currency, status=a.status,
        ) for a in rows
    ]


@router.get("/{account_id}/transactions", response_model=list[TransactionResponse])
def account_transactions(
    account_id: str,
    current: CurrentCustomer = Depends(get_current_customer),
    db: Session = Depends(get_db),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    acc = db.get(Account, account_id)
    if acc is None:
        raise NotFoundError("Kontoen blev ikke fundet.")
    # SEC-06 / KUN-02: eksisterer kontoen men tilhører en anden kunde?
    # -> log sikkerhedshændelse (T06) og returnér 404 (skjul eksistens).
    if acc.customer_id != current.customer.id:
        audit.log_event(
            db, event_type=audit.CROSS_ACCOUNT_ACCESS_DENIED, result=audit.DENIED,
            severity=audit.WARNING, actor_type="CUSTOMER", actor_id=current.customer.id,
            source_ip=current.source_ip, request_id=current.request_id,
            target_type="account", target_id=account_id,
            reason="Forsøg på adgang til fremmed konto",
        )
        db.commit()
        raise NotFoundError("Kontoen blev ikke fundet.")

    stmt = (
        select(LedgerEntry, Transfer)
        .join(Transfer, LedgerEntry.transfer_id == Transfer.id, isouter=True)
        .where(LedgerEntry.account_id == acc.id)
        .order_by(LedgerEntry.created_at.desc())
        .limit(limit).offset(offset)
    )
    out: list[TransactionResponse] = []
    for entry, transfer in db.execute(stmt).all():
        counterpart = None
        if transfer is not None:
            other_id = (
                transfer.receiver_account_id
                if entry.account_id == transfer.sender_account_id
                else transfer.sender_account_id
            )
            if other_id:
                other = db.get(Account, other_id)
                counterpart = other.masked_account_number if other else None
        out.append(TransactionResponse(
            transfer_id=entry.transfer_id or entry.id,
            created_at=entry.created_at,
            description=transfer.description if transfer else "Åbningssaldo",
            signed_amount=entry.signed_amount,
            entry_type=entry.entry_type,
            counterpart_account=counterpart,
        ))
    return out
