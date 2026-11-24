"""Kundeautentifikation: login, logout, me (FR-02, KUN-01, SEC-02..04)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    CurrentCustomer,
    get_client_ip,
    get_current_customer,
    get_db,
    get_request_id,
)
from app.config import settings
from app.core import audit
from app.core.errors import AuthenticationError, RateLimitedError
from app.core.ratelimit import login_rate_limiter
from app.core.security import verify_password
from app.core.sessions import (
    SESSION_COOKIE_NAME,
    create_session,
    get_valid_session,
    revoke_session,
)
from app.models.base_types import utcnow
from app.models.customer import Customer, CustomerUser
from app.models.session import PrincipalType
from app.schemas.customer import CustomerLoginRequest, CustomerMeResponse

router = APIRouter(prefix="/api/v1/customer/auth", tags=["customer-auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,                                   # SEC-02
        secure=settings.session_cookie_secure,           # SEC-02
        samesite=settings.session_cookie_samesite,       # SEC-02
        max_age=settings.session_idle_timeout_minutes * 60,
        path="/",
    )


def _resolve_user(db: Session, identifier: str) -> tuple[CustomerUser, Customer] | None:
    """Find kunde via e-mail eller kundenummer."""
    ident = identifier.strip()
    user = db.execute(
        select(CustomerUser).where(CustomerUser.email == ident.lower())
    ).scalar_one_or_none()
    customer: Customer | None = None
    if user is not None:
        customer = db.execute(
            select(Customer).where(Customer.user_id == user.id)
        ).scalar_one_or_none()
    else:
        customer = db.execute(
            select(Customer).where(Customer.customer_number == ident)
        ).scalar_one_or_none()
        if customer is not None:
            user = db.get(CustomerUser, customer.user_id)
    if user is None or customer is None:
        return None
    return user, customer


@router.post("/login")
def login(
    payload: CustomerLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
    source_ip: str = Depends(get_client_ip),
):
    rl_key = f"cust:{source_ip}:{payload.identifier.lower()}"
    if login_rate_limiter.is_limited(rl_key):
        audit.log_event(
            db, event_type=audit.CUSTOMER_RATE_LIMITED, result=audit.DENIED,
            severity=audit.WARNING, actor_type="CUSTOMER", source_ip=source_ip,
            request_id=request_id, reason="Rate limit overskredet",
        )
        db.commit()
        raise RateLimitedError()

    resolved = _resolve_user(db, payload.identifier)
    # Generisk fejl uanset årsag (SEC-04: afslør ikke om bruger findes).
    if resolved is None:
        audit.log_event(
            db, event_type=audit.CUSTOMER_LOGIN_FAILURE, result=audit.FAILURE,
            severity=audit.WARNING, actor_type="CUSTOMER", source_ip=source_ip,
            request_id=request_id, reason="Ukendt bruger eller forkert kode",
        )
        db.commit()
        raise AuthenticationError("Forkert login eller adgangskode.")

    user, customer = resolved
    if not user.is_active or not verify_password(payload.password, user.password_hash):
        audit.log_event(
            db, event_type=audit.CUSTOMER_LOGIN_FAILURE, result=audit.FAILURE,
            severity=audit.WARNING, actor_type="CUSTOMER", actor_id=customer.id,
            source_ip=source_ip, request_id=request_id,
            reason="Inaktiv konto eller forkert kode",
        )
        db.commit()
        raise AuthenticationError("Forkert login eller adgangskode.")

    # Succes
    login_rate_limiter.reset(rl_key)
    user.last_login_at = utcnow()
    new = create_session(db, principal_type=PrincipalType.CUSTOMER, principal_id=customer.id)
    _set_session_cookie(response, new.token)
    audit.log_event(
        db, event_type=audit.CUSTOMER_LOGIN_SUCCESS, result=audit.SUCCESS,
        actor_type="CUSTOMER", actor_id=customer.id, source_ip=source_ip,
        request_id=request_id,
    )
    db.commit()
    return {
        "csrf_token": new.csrf_token,     # frontend sender denne i X-CSRF-Token
        "customer": CustomerMeResponse(
            customer_id=customer.id,
            customer_number=customer.customer_number,
            first_name=customer.first_name,
            last_name=customer.last_name,
            email=user.email,
        ).model_dump(),
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
    source_ip: str = Depends(get_client_ip),
):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    row = get_valid_session(db, token)
    if row is not None:
        revoke_session(db, row)
        audit.log_event(
            db, event_type=audit.CUSTOMER_LOGOUT, result=audit.SUCCESS,
            actor_type="CUSTOMER", actor_id=row.principal_id, source_ip=source_ip,
            request_id=request_id,
        )
        db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"message": "Du er nu logget ud."}


@router.get("/me", response_model=CustomerMeResponse)
def me(current: CurrentCustomer = Depends(get_current_customer), db: Session = Depends(get_db)):
    user = db.get(CustomerUser, current.customer.user_id)
    return CustomerMeResponse(
        customer_id=current.customer.id,
        customer_number=current.customer.customer_number,
        first_name=current.customer.first_name,
        last_name=current.customer.last_name,
        email=user.email if user else "",
    )
