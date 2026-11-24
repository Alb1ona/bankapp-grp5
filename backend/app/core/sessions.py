"""
Server-side sessionshåndtering (SEC-02, SEC-03, FR-02).

En session identificeres af et høj-entropi token i en HttpOnly+Secure cookie.
Kun hash'et gemmes i databasen. Sessioner udløber efter inaktivitet og kan
tilbagekaldes (logout eller AD-adgang fjernet).
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.core.rbac import Role
from app.core.security import (
    generate_csrf_token,
    generate_session_token,
    hash_token,
)
from app.models.base_types import utcnow
from app.models.session import PrincipalType, Session as SessionRow

SESSION_COOKIE_NAME = "bankapp_session"
CSRF_HEADER_NAME = "X-CSRF-Token"


class NewSession:
    """Resultat af at oprette en session: klar-token (til cookie) + metadata."""

    def __init__(self, token: str, csrf_token: str, row: SessionRow) -> None:
        self.token = token
        self.csrf_token = csrf_token
        self.row = row


def create_session(
    db: DbSession,
    *,
    principal_type: PrincipalType,
    principal_id: str,
    roles: list[Role] | None = None,
) -> NewSession:
    token = generate_session_token()
    csrf = generate_csrf_token()
    now = utcnow()
    expires = now + timedelta(minutes=settings.session_idle_timeout_minutes)

    row = SessionRow(
        principal_type=principal_type,
        principal_id=principal_id,
        token_hash=hash_token(token),
        csrf_token=csrf,
        created_at=now,
        last_seen_at=now,
        expires_at=expires,
        last_revalidated_at=now if principal_type == PrincipalType.EMPLOYEE else None,
        roles_cache=",".join(r.value for r in roles) if roles else None,
    )
    db.add(row)
    db.flush()
    return NewSession(token=token, csrf_token=csrf, row=row)


def get_valid_session(db: DbSession, token: str | None) -> SessionRow | None:
    """
    Slå en session op fra cookie-token. Returnér None hvis udløbet/tilbagekaldt.
    Forlænger 'last_seen_at' og udløbstid ved aktivitet (glidende inaktivitet).
    """
    if not token:
        return None
    row = db.execute(
        select(SessionRow).where(SessionRow.token_hash == hash_token(token))
    ).scalar_one_or_none()
    if row is None:
        return None

    now = utcnow()
    if row.revoked_at is not None:
        return None
    # Sammenlign tidszone-sikkert.
    expires = row.expires_at
    if expires.tzinfo is None:
        from datetime import timezone as _tz
        expires = expires.replace(tzinfo=_tz.utc)
    if expires < now:
        return None

    # Forlæng glidende inaktivitetsvindue (SEC-03).
    row.last_seen_at = now
    row.expires_at = now + timedelta(minutes=settings.session_idle_timeout_minutes)
    db.flush()
    return row


def revoke_session(db: DbSession, row: SessionRow) -> None:
    row.revoked_at = utcnow()
    db.flush()


def roles_from_cache(row: SessionRow) -> list[Role]:
    if not row.roles_cache:
        return []
    out: list[Role] = []
    for part in row.roles_cache.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(Role(part))
        except ValueError:
            continue
    return out


def update_roles_cache(db: DbSession, row: SessionRow, roles: list[Role]) -> None:
    row.roles_cache = ",".join(r.value for r in roles)
    row.last_revalidated_at = utcnow()
    db.flush()
