"""Kundesøgning og -opslag for Kundeservice og Investering (FR-17). Skrivebeskyttet kundedata."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentEmployee, get_db, require_permission
from app.core import audit
from app.core.errors import NotFoundError
from app.core.rbac import Permission
from app.models.account import Account
from app.models.customer import Customer, CustomerUser
from app.schemas.internal import AccountAdminView, CustomerSearchResult

router = APIRouter(prefix="/api/v1/internal/customers", tags=["internal-customers"])


@router.get("", response_model=list[CustomerSearchResult])
def search_customers(
    q: str = Query(min_length=1, max_length=100),
    db: Session = Depends(get_db),
    current: CurrentEmployee = Depends(require_permission(Permission.CUSTOMER_LOOKUP)),
):
    term = f"%{q.strip()}%"
    stmt = (
        select(Customer, CustomerUser)
        .join(CustomerUser, Customer.user_id == CustomerUser.id)
        .where(or_(
            Customer.customer_number.ilike(term),
            Customer.first_name.ilike(term),
            Customer.last_name.ilike(term),
            CustomerUser.email.ilike(term),
        ))
        .limit(25)
    )
    results = db.execute(stmt).all()
    audit.log_event(
        db, event_type=audit.CUSTOMER_LOOKUP, result=audit.SUCCESS,
        actor_type="EMPLOYEE", actor_id=current.employee.ad_object_guid,
        source_ip=current.source_ip, request_id=current.request_id,
        reason=f"Søgning ({len(results)} resultater)",
    )
    db.commit()
    return [
        CustomerSearchResult(
            customer_id=c.id, customer_number=c.customer_number,
            full_name=c.full_name, email=u.email,
        ) for c, u in results
    ]


@router.get("/{customer_id}/accounts", response_model=list[AccountAdminView])
def customer_accounts(
    customer_id: str,
    db: Session = Depends(get_db),
    current: CurrentEmployee = Depends(require_permission(Permission.CUSTOMER_LOOKUP)),
):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise NotFoundError("Kunden blev ikke fundet.")
    rows = db.execute(
        select(Account).where(Account.customer_id == customer_id).order_by(Account.created_at)
    ).scalars().all()
    audit.log_event(
        db, event_type=audit.CUSTOMER_LOOKUP, result=audit.SUCCESS,
        actor_type="EMPLOYEE", actor_id=current.employee.ad_object_guid,
        source_ip=current.source_ip, request_id=current.request_id,
        target_type="customer", target_id=customer_id, reason="Kontoopslag",
    )
    db.commit()
    return [
        AccountAdminView(
            id=a.id, account_number=a.account_number, account_type=a.account_type,
            balance=a.balance, currency=a.currency, status=a.status,
        ) for a in rows
    ]
