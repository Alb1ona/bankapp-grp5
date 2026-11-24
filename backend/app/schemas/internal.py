"""Request/response-skemaer for medarbejder-API'et."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# -- AD-login -----------------------------------------------------------------
class EmployeeLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)   # sAMAccountName
    password: str = Field(min_length=1, max_length=256)


class EmployeeMeResponse(BaseModel):
    employee_id: str
    ad_username: str
    display_name: str
    roles: list[str]
    permissions: list[str]


# -- Kundesøgning (SUPPORT) ---------------------------------------------------
class CustomerSearchResult(BaseModel):
    customer_id: str
    customer_number: str
    full_name: str
    email: str


class AccountAdminView(BaseModel):
    id: str
    account_number: str
    account_type: str
    balance: Decimal
    currency: str
    status: str


# -- Lånebehandling (LOAN_OFFICER) --------------------------------------------
class LoanDecisionRequest(BaseModel):
    approve: bool
    decision_note: str = Field(min_length=3, max_length=500)


class LoanAdminView(BaseModel):
    id: str
    customer_id: str
    amount: Decimal
    loan_type: str
    duration_months: int
    purpose: str
    status: str
    decision_note: str | None
    reviewed_by_employee_id: str | None
    created_at: datetime
    reviewed_at: datetime | None


# -- Kontospærring (SUPPORT, P1) ----------------------------------------------
class AccountFreezeRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


# -- Audit (AUDITOR) ----------------------------------------------------------
class AuditEventView(BaseModel):
    id: str
    timestamp: datetime
    actor_type: str | None
    actor_id: str | None
    event_type: str
    severity: str
    result: str
    source_ip: str | None
    target_type: str | None
    target_id: str | None
    request_id: str | None
    reason: str | None


# -- Systemstatus (ADMIN) -----------------------------------------------------
class SystemStatusView(BaseModel):
    application: str
    env: str
    ad_enabled: bool
    database_ok: bool
    customer_count: int
    account_count: int
    uptime_note: str
