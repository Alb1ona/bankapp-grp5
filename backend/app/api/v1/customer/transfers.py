"""Kundens overførsler (FR-06 .. FR-11)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentCustomer, csrf_protect, get_current_customer, get_db
from app.core import audit
from app.models.account import Account
from app.models.transfer import Transfer
from app.schemas.customer import TransferCreateRequest, TransferResponse
from app.services.transfer_service import execute_transfer

router = APIRouter(prefix="/api/v1/customer/transfers", tags=["customer-transfers"])


@router.post("", response_model=TransferResponse, dependencies=[Depends(csrf_protect)])
def create_transfer(
    payload: TransferCreateRequest,
    current: CurrentCustomer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        transfer = execute_transfer(
            db,
            customer=current.customer,
            sender_account_id=payload.sender_account_id,
            receiver_account_number=payload.receiver_account_number,
            amount=payload.amount,
            description=payload.description,
            idempotency_key=payload.idempotency_key,
        )
    except Exception as exc:  # audit + videregiv (API-laget mapper til HTTP)
        audit.log_event(
            db, event_type=audit.TRANSFER_REJECTED, result=audit.FAILURE,
            severity=audit.WARNING, actor_type="CUSTOMER", actor_id=current.customer.id,
            source_ip=current.source_ip, request_id=current.request_id,
            target_type="account", target_id=payload.sender_account_id,
            reason=type(exc).__name__,
        )
        db.commit()
        raise

    audit.log_event(
        db, event_type=audit.TRANSFER_SUCCESS, result=audit.SUCCESS,
        actor_type="CUSTOMER", actor_id=current.customer.id,
        source_ip=current.source_ip, request_id=current.request_id,
        target_type="transfer", target_id=transfer.id,
        extra={"amount": str(transfer.amount)},
    )
    db.commit()
    return TransferResponse(
        id=transfer.id, sender_account_id=transfer.sender_account_id,
        receiver_account_id=transfer.receiver_account_id, amount=transfer.amount,
        status=transfer.status, description=transfer.description,
        created_at=transfer.created_at,
    )


@router.get("", response_model=list[TransferResponse])
def list_transfers(
    current: CurrentCustomer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    # Kun overførsler initieret af kunden (KUN-02).
    rows = db.execute(
        select(Transfer).where(Transfer.initiated_by_customer_id == current.customer.id)
        .order_by(Transfer.created_at.desc()).limit(100)
    ).scalars().all()
    return [
        TransferResponse(
            id=t.id, sender_account_id=t.sender_account_id,
            receiver_account_id=t.receiver_account_id, amount=t.amount,
            status=t.status, description=t.description, created_at=t.created_at,
        ) for t in rows
    ]
