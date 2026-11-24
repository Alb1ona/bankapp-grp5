"""Auditlog-visning for AUDITOR (FR-21). Skrivebeskyttet, filtrerbar (DB-05)."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentEmployee, get_db, require_permission
from app.core.rbac import Permission
from app.models.audit import AuditEvent
from app.schemas.internal import AuditEventView

router = APIRouter(prefix="/api/v1/internal/audit", tags=["internal-audit"])


@router.get("/events", response_model=list[AuditEventView])
def list_events(
    db: Session = Depends(get_db),
    current: CurrentEmployee = Depends(require_permission(Permission.AUDIT_READ)),
    event_type: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    result: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    since: datetime | None = Query(default=None),
    until: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    stmt = select(AuditEvent)
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if result:
        stmt = stmt.where(AuditEvent.result == result)
    if request_id:
        stmt = stmt.where(AuditEvent.request_id == request_id)
    if since:
        stmt = stmt.where(AuditEvent.timestamp >= since)
    if until:
        stmt = stmt.where(AuditEvent.timestamp <= until)
    stmt = stmt.order_by(AuditEvent.timestamp.desc()).limit(limit).offset(offset)
    rows = db.execute(stmt).scalars().all()
    return [
        AuditEventView(
            id=e.id, timestamp=e.timestamp, actor_type=e.actor_type, actor_id=e.actor_id,
            event_type=e.event_type, severity=e.severity, result=e.result,
            source_ip=e.source_ip, target_type=e.target_type, target_id=e.target_id,
            request_id=e.request_id, reason=e.reason,
        ) for e in rows
    ]
