"""
Medarbejderautentifikation via AD/LDAPS (AD-01 .. AD-05, SEC-10).

Ingen skjult lokal fallback: kan AD ikke verificeres sikkert, afvises nye
logins (AD-05). Roller bestemmes alene af AD-gruppemedlemskab.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    CurrentEmployee,
    get_client_ip,
    get_current_employee,
    get_db,
    get_request_id,
)
from app.config import settings
from app.core import audit
from app.core.errors import AuthenticationError, AuthorizationError, RateLimitedError
from app.core.ldap_adapter import AdAuthError, AdConnectionError, get_ldap_adapter
from app.core.ratelimit import login_rate_limiter
from app.core.rbac import permissions_for_roles, roles_from_ad_groups
from app.core.sessions import (
    SESSION_COOKIE_NAME,
    create_session,
    get_valid_session,
    revoke_session,
)
from app.models.base_types import utcnow
from app.models.employee import Employee
from app.models.session import PrincipalType
from app.schemas.internal import EmployeeLoginRequest, EmployeeMeResponse

router = APIRouter(prefix="/api/v1/internal/auth", tags=["internal-auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME, value=token, httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=settings.session_idle_timeout_minutes * 60, path="/",
    )


def _upsert_employee(db: Session, identity) -> Employee:
    """AD-04: ad_object_guid er den stabile nøgle; navn opdateres ved login."""
    emp = db.execute(
        select(Employee).where(Employee.ad_object_guid == identity.object_guid)
    ).scalar_one_or_none()
    if emp is None:
        emp = Employee(
            ad_object_guid=identity.object_guid,
            ad_username=identity.username,
            display_name=identity.display_name,
        )
        db.add(emp)
    else:
        emp.ad_username = identity.username
        emp.display_name = identity.display_name
    emp.last_login_at = utcnow()
    db.flush()
    return emp


@router.post("/login")
def login(
    payload: EmployeeLoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
    source_ip: str = Depends(get_client_ip),
):
    rl_key = f"emp:{source_ip}:{payload.username.lower()}"
    if login_rate_limiter.is_limited(rl_key):
        audit.log_event(
            db, event_type=audit.AD_LOGIN_FAILURE, result=audit.DENIED,
            severity=audit.WARNING, actor_type="EMPLOYEE", source_ip=source_ip,
            request_id=request_id, reason="Rate limit overskredet",
        )
        db.commit()
        raise RateLimitedError()

    adapter = get_ldap_adapter()
    try:
        identity = adapter.authenticate(payload.username, payload.password)
    except AdAuthError:
        login_rate_limiter.is_limited(rl_key)
        audit.log_event(
            db, event_type=audit.AD_LOGIN_FAILURE, result=audit.FAILURE,
            severity=audit.WARNING, actor_type="EMPLOYEE", source_ip=source_ip,
            request_id=request_id, reason="Ugyldige AD-credentials",
        )
        db.commit()
        raise AuthenticationError("Forkert brugernavn eller adgangskode.")
    except AdConnectionError:
        # AD-05: ingen fallback. Nye logins afvises, når AD ikke kan verificeres.
        audit.log_event(
            db, event_type=audit.AD_CONNECTION_ERROR, result=audit.FAILURE,
            severity=audit.ERROR, actor_type="EMPLOYEE", source_ip=source_ip,
            request_id=request_id, reason="AD utilgængelig",
        )
        db.commit()
        raise AuthenticationError("Login er midlertidigt utilgængeligt.")

    # AD-03: skal være medlem af den overordnede adgangsgruppe.
    group_cns = [c.lower() for c in identity.group_cns]
    if settings.ad_access_group.lower() not in group_cns:
        audit.log_event(
            db, event_type=audit.AD_GROUP_ACCESS_DENIED, result=audit.DENIED,
            severity=audit.WARNING, actor_type="EMPLOYEE",
            actor_id=identity.object_guid, source_ip=source_ip,
            request_id=request_id, reason="Ikke medlem af adgangsgruppe",
        )
        db.commit()
        raise AuthorizationError("Du har ikke adgang til medarbejderportalen.")

    roles = roles_from_ad_groups(identity.group_cns)
    emp = _upsert_employee(db, identity)
    login_rate_limiter.reset(rl_key)

    new = create_session(
        db, principal_type=PrincipalType.EMPLOYEE, principal_id=emp.id, roles=roles,
    )
    _set_session_cookie(response, new.token)
    audit.log_event(
        db, event_type=audit.AD_LOGIN_SUCCESS, result=audit.SUCCESS,
        actor_type="EMPLOYEE", actor_id=emp.ad_object_guid, source_ip=source_ip,
        request_id=request_id, extra={"roles": ",".join(r.value for r in roles)},
    )
    db.commit()
    return {
        "csrf_token": new.csrf_token,
        "employee": EmployeeMeResponse(
            employee_id=emp.id, ad_username=emp.ad_username,
            display_name=emp.display_name,
            roles=[r.value for r in roles],
            permissions=[p.value for p in permissions_for_roles(roles)],
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
        db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"message": "Du er nu logget ud."}


@router.get("/me", response_model=EmployeeMeResponse)
def me(current: CurrentEmployee = Depends(get_current_employee)):
    return EmployeeMeResponse(
        employee_id=current.employee.id,
        ad_username=current.employee.ad_username,
        display_name=current.employee.display_name,
        roles=[r.value for r in current.roles],
        permissions=[p.value for p in current.permissions()],
    )
