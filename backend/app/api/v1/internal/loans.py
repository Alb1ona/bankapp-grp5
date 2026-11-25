"""Lånebehandling for Investering (FR-18, T07, T12)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentEmployee, csrf_protect, get_db, require_permission
from app.core import audit
from app.core.rbac import Permission
from app.models.loan import LoanApplication, LoanStatus
from app.schemas.internal import LoanAdminView, LoanDecisionRequest
from app.services.loan_service import decide_application

router = APIRouter(prefix="/api/v1/internal/loans", tags=["internal-loans"])


@router.get("", response_model=list[LoanAdminView])
def list_loans(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current: CurrentEmployee = Depends(require_permission(Permission.LOAN_DECIDE)),
):
    stmt = select(LoanApplication)
    if status:
        try:
            stmt = stmt.where(LoanApplication.status == LoanStatus(status))
        except ValueError:
            pass
    stmt = stmt.order_by(LoanApplication.created_at.desc()).limit(100)
    rows = db.execute(stmt).scalars().all()
    return [_to_view(a) for a in rows]


@router.patch("/{loan_id}/decision", response_model=LoanAdminView,
              dependencies=[Depends(csrf_protect)])
def decide(
    loan_id: str,
    payload: LoanDecisionRequest,
    db: Session = Depends(get_db),
    current: CurrentEmployee = Depends(require_permission(Permission.LOAN_DECIDE)),
):
    app = decide_application(
        db, loan_id=loan_id, approve=payload.approve,
        employee_id=current.employee.id, decision_note=payload.decision_note,
    )
    event = audit.LOAN_APPROVED if payload.approve else audit.LOAN_REJECTED
    audit.log_event(
        db, event_type=event, result=audit.SUCCESS,
        actor_type="EMPLOYEE", actor_id=current.employee.ad_object_guid,
        source_ip=current.source_ip, request_id=current.request_id,
        target_type="loan_application", target_id=app.id,
    )
    db.commit()
    return _to_view(app)


def _to_view(a: LoanApplication) -> LoanAdminView:
    return LoanAdminView(
        id=a.id, customer_id=a.customer_id, amount=a.amount, loan_type=a.loan_type,
        duration_months=a.duration_months, purpose=a.purpose, status=a.status,
        decision_note=a.decision_note, reviewed_by_employee_id=a.reviewed_by_employee_id,
        created_at=a.created_at, reviewed_at=a.reviewed_at,
    )
