"""Kundens låneansøgninger (FR-12, FR-13)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentCustomer, csrf_protect, get_current_customer, get_db
from app.core import audit
from app.models.loan import LoanApplication
from app.schemas.customer import LoanCreateRequest, LoanResponse
from app.services.loan_service import create_application

router = APIRouter(prefix="/api/v1/customer/loans", tags=["customer-loans"])


@router.post("", response_model=LoanResponse, dependencies=[Depends(csrf_protect)])
def create_loan(
    payload: LoanCreateRequest,
    current: CurrentCustomer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    app = create_application(
        db,
        customer_id=current.customer.id,
        amount=payload.amount,
        loan_type=payload.loan_type,
        duration_months=payload.duration_months,
        purpose=payload.purpose,
    )
    audit.log_event(
        db, event_type=audit.LOAN_CREATED, result=audit.SUCCESS,
        actor_type="CUSTOMER", actor_id=current.customer.id,
        source_ip=current.source_ip, request_id=current.request_id,
        target_type="loan_application", target_id=app.id,
    )
    db.commit()
    return _to_response(app)


@router.get("", response_model=list[LoanResponse])
def list_loans(
    current: CurrentCustomer = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(LoanApplication).where(LoanApplication.customer_id == current.customer.id)
        .order_by(LoanApplication.created_at.desc())
    ).scalars().all()
    return [_to_response(a) for a in rows]


def _to_response(a: LoanApplication) -> LoanResponse:
    return LoanResponse(
        id=a.id, amount=a.amount, loan_type=a.loan_type,
        duration_months=a.duration_months, purpose=a.purpose, status=a.status,
        decision_note=a.decision_note, created_at=a.created_at, reviewed_at=a.reviewed_at,
    )
