"""Systemstatus for IT og drift (FR-22). Rettighedstildeling sker i AD, ikke her."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentEmployee, get_db, require_permission
from app.config import settings
from app.core.rbac import Permission
from app.models.account import Account
from app.models.customer import Customer
from app.schemas.internal import SystemStatusView

router = APIRouter(prefix="/api/v1/internal/system", tags=["internal-system"])


@router.get("/status", response_model=SystemStatusView)
def status(
    db: Session = Depends(get_db),
    current: CurrentEmployee = Depends(require_permission(Permission.SYSTEM_STATUS_READ)),
):
    database_ok = True
    try:
        customer_count = db.execute(select(func.count()).select_from(Customer)).scalar_one()
        account_count = db.execute(select(func.count()).select_from(Account)).scalar_one()
    except Exception:  # noqa: BLE001
        database_ok = False
        customer_count = 0
        account_count = 0
    return SystemStatusView(
        application=settings.app_name,
        env=settings.app_env,
        ad_enabled=settings.ad_enabled,
        database_ok=database_ok,
        customer_count=customer_count,
        account_count=account_count,
        uptime_note="Statussen afspejler applikationens egne data; infrastruktur overvåges separat.",
    )
