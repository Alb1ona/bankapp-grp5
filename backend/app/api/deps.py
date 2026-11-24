"""
FastAPI-afhængigheder: request-kontekst, autentifikation og autorisation.

Alle adgangsbeslutninger træffes her server-side ud fra den server-side session
og (for medarbejdere) AD-genvalidering. Frontend-angivne roller/id'er er aldrig
autoritative (SEC-05).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timezone

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core import audit
from app.core.errors import AuthenticationError, AuthorizationError
from app.core.ldap_adapter import AdConnectionError, get_ldap_adapter
from app.core.rbac import (
    Permission,
    Role,
    has_permission,
    permissions_for_roles,
    roles_from_ad_groups,
)
from app.core.sessions import (
    CSRF_HEADER_NAME,
    SESSION_COOKIE_NAME,
    get_valid_session,
    revoke_session,
    roles_from_cache,
    update_roles_cache,
)
from app.database import get_db
from app.models.base_types import utcnow
from app.models.customer import Customer
from app.models.employee import Employee
from app.models.session import PrincipalType, Session as SessionRow

__all__ = [
    "get_db",
    "get_request_id",
    "get_client_ip",
    "CurrentCustomer",
    "CurrentEmployee",
    "get_current_customer",
    "get_current_employee",
    "require_permission",
    "csrf_protect",
]


def get_request_id(request: Request) -> str:
    """Stabil request-id til korrelation i logs (LOG-01)."""
    rid = request.headers.get("X-Request-ID")
    if not rid or len(rid) > 64:
        rid = f"req-{uuid.uuid4().hex[:16]}"
    return rid


def get_client_ip(request: Request) -> str:
    """
    Kilde-IP til logging. SEC-05: vi stoler ikke på klient-angivne headers til
    autorisation. source_ip bruges kun til logning, og vi tager den direkte
    TCP-peer-adresse (request.client), ikke X-Forwarded-For medmindre en
    betroet proxy er konfigureret (udeladt her med vilje).
    """
    return request.client.host if request.client else "unknown"


# -- Kunde-kontekst -----------------------------------------------------------
@dataclass
class CurrentCustomer:
    session: SessionRow
    customer: Customer
    request_id: str
    source_ip: str


def get_current_customer(
    request: Request,
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
    source_ip: str = Depends(get_client_ip),
) -> CurrentCustomer:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    row = get_valid_session(db, token)
    if row is None or row.principal_type != PrincipalType.CUSTOMER:
        raise AuthenticationError()
    customer = db.get(Customer, row.principal_id)
    if customer is None:
        raise AuthenticationError()
    return CurrentCustomer(session=row, customer=customer, request_id=request_id, source_ip=source_ip)


# -- Medarbejder-kontekst -----------------------------------------------------
@dataclass
class CurrentEmployee:
    session: SessionRow
    employee: Employee
    roles: list[Role]
    request_id: str
    source_ip: str

    def permissions(self) -> set[Permission]:
        return permissions_for_roles(self.roles)


def _needs_revalidation(row: SessionRow) -> bool:
    last = row.last_revalidated_at
    if last is None:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return (utcnow() - last).total_seconds() > settings.ad_revalidate_seconds


def get_current_employee(
    request: Request,
    db: Session = Depends(get_db),
    request_id: str = Depends(get_request_id),
    source_ip: str = Depends(get_client_ip),
) -> CurrentEmployee:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    row = get_valid_session(db, token)
    if row is None or row.principal_type != PrincipalType.EMPLOYEE:
        raise AuthenticationError()
    employee = db.get(Employee, row.principal_id)
    if employee is None:
        raise AuthenticationError()

    roles = roles_from_cache(row)

    # AD-06: genvalidér gruppemedlemskab/kontostatus maks. hvert 5. minut.
    if _needs_revalidation(row):
        try:
            adapter = get_ldap_adapter()
            identity = adapter.fetch_identity(employee.ad_username)
            group_cns = [c.lower() for c in identity.group_cns]
            in_access_group = settings.ad_access_group.lower() in group_cns
            if not identity.is_active or not in_access_group:
                # AD-05/AD-06: adgang fjernet -> bloker og tilbagekald session.
                revoke_session(db, row)
                audit.log_event(
                    db, event_type=audit.AD_ACCESS_REVOKED, result=audit.DENIED,
                    severity=audit.WARNING, actor_type="EMPLOYEE",
                    actor_id=employee.ad_object_guid, source_ip=source_ip,
                    request_id=request_id, reason="Adgang fjernet i AD",
                )
                db.commit()
                raise AuthorizationError("Din adgang er blevet fjernet.")
            roles = roles_from_ad_groups(identity.group_cns)
            update_roles_cache(db, row, roles)
            db.commit()
        except AdConnectionError:
            # AD kan ikke verificeres sikkert. Eksisterende session får lov at
            # fortsætte på cachede roller, men hændelsen logges (AD-05 gælder
            # nye logins; her undgår vi at smide en aktiv bruger ud ved et
            # forbigående netværksudfald - dokumenteret designvalg).
            audit.log_event(
                db, event_type=audit.AD_CONNECTION_ERROR, result=audit.FAILURE,
                severity=audit.WARNING, actor_type="EMPLOYEE",
                actor_id=employee.ad_object_guid, source_ip=source_ip,
                request_id=request_id, reason="AD utilgængelig ved genvalidering",
            )
            db.commit()

    return CurrentEmployee(
        session=row, employee=employee, roles=roles,
        request_id=request_id, source_ip=source_ip,
    )


def require_permission(permission: Permission):
    """Dependency-factory: kræv en bestemt rettighed (FR-16, SEC-06)."""

    def _dep(
        db: Session = Depends(get_db),
        current: CurrentEmployee = Depends(get_current_employee),
    ) -> CurrentEmployee:
        if not has_permission(current.roles, permission):
            audit.log_event(
                db, event_type=audit.ACCESS_DENIED, result=audit.DENIED,
                severity=audit.WARNING, actor_type="EMPLOYEE",
                actor_id=current.employee.ad_object_guid, source_ip=current.source_ip,
                request_id=current.request_id,
                reason=f"Mangler rettighed {permission.value}",
            )
            db.commit()
            raise AuthorizationError()
        return current

    return _dep


def csrf_protect(
    request: Request,
    db: Session = Depends(get_db),
) -> None:
    """
    CSRF-beskyttelse for ændrende requests (SEC-03).
    Dobbelt-submit: headeren X-CSRF-Token skal matche sessionens csrf_token.
    """
    token = request.cookies.get(SESSION_COOKIE_NAME)
    row = get_valid_session(db, token)
    if row is None:
        raise AuthenticationError()
    header_token = request.headers.get(CSRF_HEADER_NAME, "")
    from app.core.security import constant_time_equals
    if not header_token or not constant_time_equals(header_token, row.csrf_token):
        raise AuthorizationError("Ugyldigt CSRF-token.")
