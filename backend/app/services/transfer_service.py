"""
Overførselsmotor (FR-06 .. FR-11, DB-02/03/04).

Garantier:
  * Atomisk: debet + kredit + ledger + status i én DB-transaktion (FR-09).
  * Dobbelt bogføring: to ledger-poster hvis sum er nul (FR-11).
  * Idempotent: samme (kunde, idempotency_key) giver kun én økonomisk postering (FR-10, DB-04).
  * Concurrency-sikker: række-låsning på kontiene forhindrer overtræk ved
    samtidige overførsler (FR-10, DB-03).
  * Beløbsgrænse og dækningstjek (FR-08).

Kaldere styrer commit. Tjenesten bruger `flush()` og row-locks; selve commit
sker i API-laget, så audit-posten indgår i samme transaktion hvor det ønskes.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import (
    AccountNotActiveError,
    InsufficientFundsError,
    NotFoundError,
    TransferLimitError,
    ValidationError,
)
from app.models.account import Account, AccountStatus
from app.models.customer import Customer
from app.models.transfer import (
    LedgerEntry,
    LedgerEntryType,
    Transfer,
    TransferStatus,
)

TWOPLACES = Decimal("0.01")


def _load_for_update(db: Session, account_id: str) -> Account | None:
    """Hent konto med række-lås (SELECT ... FOR UPDATE på PostgreSQL)."""
    stmt = select(Account).where(Account.id == account_id).with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def _find_existing(db: Session, customer_id: str, idempotency_key: str) -> Transfer | None:
    stmt = select(Transfer).where(
        Transfer.initiated_by_customer_id == customer_id,
        Transfer.idempotency_key == idempotency_key,
    )
    return db.execute(stmt).scalar_one_or_none()


def execute_transfer(
    db: Session,
    *,
    customer: Customer,
    sender_account_id: str,
    receiver_account_number: str,
    amount: Decimal,
    description: str | None,
    idempotency_key: str,
) -> Transfer:
    # --- Idempotency (FR-10, DB-04) -----------------------------------------
    existing = _find_existing(db, customer.id, idempotency_key)
    if existing is not None:
        # Returnér den oprindelige transaktion uden at hæve igen.
        return existing

    # --- Beløbsvalidering (FR-08) -------------------------------------------
    if amount is None:
        raise ValidationError("Beløb mangler.")
    amount = Decimal(amount).quantize(TWOPLACES)
    if amount <= Decimal("0.00"):
        raise ValidationError("Beløbet skal være positivt.")
    if amount > settings.transfer_max_amount_dkk:
        raise TransferLimitError()

    # --- Lås afsenderkonto og verificér ejerskab (FR-08, SEC-06) ------------
    sender = _load_for_update(db, sender_account_id)
    if sender is None or sender.customer_id != customer.id:
        # Skjul om kontoen findes men tilhører en anden (undgå informationslæk).
        raise NotFoundError("Afsenderkontoen blev ikke fundet.")
    if sender.status != AccountStatus.ACTIVE:
        raise AccountNotActiveError("Afsenderkontoen er spærret eller lukket.")

    # --- Find og lås modtagerkonto ------------------------------------------
    recv_stmt = select(Account).where(
        Account.account_number == receiver_account_number
    ).with_for_update()
    receiver = db.execute(recv_stmt).scalar_one_or_none()
    if receiver is None:
        raise NotFoundError("Modtagerkontoen findes ikke.")
    if receiver.status == AccountStatus.CLOSED:
        raise AccountNotActiveError("Modtagerkontoen er lukket.")
    if receiver.id == sender.id:
        raise ValidationError("Afsender- og modtagerkonto må ikke være ens.")

    # --- Dækningstjek efter låsning (FR-08, T09) ----------------------------
    if sender.balance < amount:
        # Opret en afvist transfer-post for sporbarhed, men ingen saldoændring.
        rejected = Transfer(
            sender_account_id=sender.id,
            receiver_account_id=receiver.id,
            amount=amount,
            status=TransferStatus.REJECTED,
            description=description,
            initiated_by_customer_id=customer.id,
            idempotency_key=idempotency_key,
        )
        db.add(rejected)
        db.flush()
        raise InsufficientFundsError()

    # --- Udfør atomisk (FR-09, FR-11) ---------------------------------------
    transfer = Transfer(
        sender_account_id=sender.id,
        receiver_account_id=receiver.id,
        amount=amount,
        status=TransferStatus.COMPLETED,
        description=description,
        initiated_by_customer_id=customer.id,
        idempotency_key=idempotency_key,
    )
    db.add(transfer)
    db.flush()  # så transfer.id er sat

    sender.balance = (sender.balance - amount).quantize(TWOPLACES)
    receiver.balance = (receiver.balance + amount).quantize(TWOPLACES)

    debit = LedgerEntry(
        transfer_id=transfer.id, account_id=sender.id,
        signed_amount=(-amount).quantize(TWOPLACES),
        entry_type=LedgerEntryType.DEBIT,
    )
    credit = LedgerEntry(
        transfer_id=transfer.id, account_id=receiver.id,
        signed_amount=amount.quantize(TWOPLACES),
        entry_type=LedgerEntryType.CREDIT,
    )
    db.add_all([debit, credit])
    db.flush()
    # FR-11 invariant (defensivt tjek): de to posteringers sum er nul.
    assert (debit.signed_amount + credit.signed_amount) == Decimal("0.00")
    return transfer
