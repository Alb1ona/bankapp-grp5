"""
Lånelogik (FR-12, FR-13, FR-18).

Kunden opretter en ansøgning (status AFVENTER). En medarbejder i Investering afgør den
præcis én gang; en afgjort sag kan ikke afgøres igen (FR-18, T12).
Ingen automatisk udbetaling eller kreditvurdering (FR-13).
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import LoanAlreadyDecidedError, NotFoundError, ValidationError
from app.models.base_types import utcnow
from app.models.loan import LoanApplication, LoanStatus

TWOPLACES = Decimal("0.01")
_ALLOWED_TYPES = {"FORBRUG", "BOLIG", "BIL", "ANDET"}


def create_application(
    db: Session,
    *,
    customer_id: str,
    amount: Decimal,
    loan_type: str,
    duration_months: int,
    purpose: str,
) -> LoanApplication:
    amount = Decimal(amount).quantize(TWOPLACES)
    if amount <= Decimal("0.00"):
        raise ValidationError("Lånebeløbet skal være positivt.")
    if loan_type not in _ALLOWED_TYPES:
        raise ValidationError("Ugyldig lånetype.")
    if not (1 <= duration_months <= 480):
        raise ValidationError("Løbetiden skal være mellem 1 og 480 måneder.")
    if not purpose or len(purpose.strip()) < 3:
        raise ValidationError("Angiv et formål.")

    app = LoanApplication(
        customer_id=customer_id,
        amount=amount,
        loan_type=loan_type,
        duration_months=duration_months,
        purpose=purpose.strip(),
        status=LoanStatus.AFVENTER,
    )
    db.add(app)
    db.flush()
    return app


def decide_application(
    db: Session,
    *,
    loan_id: str,
    approve: bool,
    employee_id: str,
    decision_note: str,
) -> LoanApplication:
    # Lås rækken, så to sagsbehandlere ikke afgør samtidig.
    stmt = select(LoanApplication).where(LoanApplication.id == loan_id).with_for_update()
    app = db.execute(stmt).scalar_one_or_none()
    if app is None:
        raise NotFoundError("Låneansøgningen blev ikke fundet.")
    if app.status != LoanStatus.AFVENTER:
        raise LoanAlreadyDecidedError()
    if not decision_note or len(decision_note.strip()) < 3:
        raise ValidationError("En begrundelse er obligatorisk.")

    app.status = LoanStatus.GODKENDT if approve else LoanStatus.AFVIST
    app.reviewed_by_employee_id = employee_id
    app.decision_note = decision_note.strip()
    app.reviewed_at = utcnow()
    db.flush()
    return app
