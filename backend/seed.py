"""
Idempotent seed-script med fiktive testdata (afsnit 11.1, DB-07).

Opretter:
  * 6 fiktive kunder, 10 konti
  * Åbningssaldi som tydeligt markerede OPENING_BALANCE-ledgerposter (DB-07)
  * >30 historiske posteringer (åbningssaldi + gennemførte overførsler)
  * 5 låneansøgninger i forskellige statusser
  * 3 supportsager (P1)

Alle beløb/personer er fiktive. Ingen medarbejderadgangskoder oprettes
(medarbejdere kommer fra AD). Kundernes demo-password læses fra miljøvariablen
SEED_CUSTOMER_PASSWORD; i development bruges en tydelig demo-standard, og den
anvendte værdi printes, så intet rigtigt password ligger i kildekoden.

Kørsel:
    python seed.py            # idempotent: springer over hvis allerede seedet
    python seed.py --reset    # sletter eksisterende demodata og seeder forfra
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal

from sqlalchemy import delete, select

from app.config import settings
from app.core.security import hash_password
from app.database import SessionLocal
from app.models.account import Account, AccountStatus, AccountType
from app.models.base_types import utcnow
from app.models.customer import Customer, CustomerUser
from app.models.loan import LoanApplication, LoanStatus
from app.models.support import SupportCase, SupportStatus, SupportMessage
from app.models.transfer import (
    LedgerEntry, LedgerEntryType, Transfer, TransferStatus,
)

TWO = Decimal("0.01")


def _demo_password() -> str:
    pw = os.environ.get("SEED_CUSTOMER_PASSWORD")
    if pw:
        return pw
    if settings.is_production:
        print("FEJL: SEED_CUSTOMER_PASSWORD skal sættes i produktion.", file=sys.stderr)
        sys.exit(1)
    return "demo-Kode-1234"   # kun development; tydeligt en demoværdi


# (fornavn, efternavn, kundenr, email, [ (kontonr, type, åbningssaldo), ... ])
CUSTOMERS = [
    ("Anders", "Andersen", "100001", "anders@demobank.local",
     [("5001000001", AccountType.LOENKONTO, "25000.00"),
      ("5001000002", AccountType.OPSPARING, "60000.00")]),
    ("Bente", "Berg", "100002", "bente@demobank.local",
     [("5001000003", AccountType.LOENKONTO, "12000.00"),
      ("5001000004", AccountType.BUDGET, "3000.00")]),
    ("Carla", "Clausen", "100003", "carla@demobank.local",
     [("5001000005", AccountType.LOENKONTO, "840.00")]),
    ("David", "Dam", "100004", "david@demobank.local",
     [("5001000006", AccountType.LOENKONTO, "47000.00"),
      ("5001000007", AccountType.OPSPARING, "150000.00")]),
    ("Esben", "Eriksen", "100005", "esben@demobank.local",
     [("5001000008", AccountType.LOENKONTO, "5200.00")]),
    ("Fatima", "Frandsen", "100006", "fatima@demobank.local",
     [("5001000009", AccountType.LOENKONTO, "9800.00"),
      ("5001000010", AccountType.OPSPARING, "22000.00")]),
]

# (afsender-kundenr, afsender-kontonr, modtager-kontonr, beløb, tekst)
TRANSFERS = [
    ("100001", "5001000001", "5001000003", "1200.00", "Deling af frokost"),
    ("100001", "5001000001", "5001000005", "500.00", "Gave"),
    ("100002", "5001000003", "5001000006", "750.00", "Husleje andel"),
    ("100004", "5001000006", "5001000001", "3000.00", "Tilbagebetaling"),
    ("100004", "5001000007", "5001000006", "10000.00", "Opsparing til forbrug"),
    ("100006", "5001000009", "5001000008", "400.00", "Biografbilletter"),
    ("100001", "5001000002", "5001000001", "5000.00", "Overførsel til løn"),
    ("100004", "5001000006", "5001000009", "250.00", "Fælles gave"),
    ("100002", "5001000003", "5001000001", "300.00", "Lån retur"),
    ("100006", "5001000010", "5001000009", "2000.00", "Buffer"),
    ("100001", "5001000001", "5001000006", "150.00", "Kaffe"),
    ("100004", "5001000007", "5001000001", "1250.00", "Refusion"),
]

# (kundenr, beløb, type, løbetid, formål, status)
LOANS = [
    ("100001", "150000.00", "BIL", 60, "Køb af brugt bil", LoanStatus.AFVENTER),
    ("100002", "25000.00", "FORBRUG", 24, "Ny computer og møbler", LoanStatus.AFVENTER),
    ("100004", "1200000.00", "BOLIG", 360, "Boligkøb", LoanStatus.GODKENDT),
    ("100003", "80000.00", "FORBRUG", 36, "Rejse", LoanStatus.AFVIST),
    ("100006", "40000.00", "ANDET", 48, "Tandlæge", LoanStatus.AFVENTER),
]


def _already_seeded(db) -> bool:
    return db.execute(
        select(Customer).where(Customer.customer_number == "100001")
    ).scalar_one_or_none() is not None


def _reset(db) -> None:
    # Sletter i FK-sikker rækkefølge.
    for model in [SupportMessage, SupportCase, LedgerEntry, Transfer,
                  LoanApplication, Account, Customer, CustomerUser]:
        db.execute(delete(model))
    db.commit()
    print("Eksisterende demodata slettet.")


def _opening_entry(account: Account) -> LedgerEntry:
    # DB-07: markeret åbningssaldo, så balancen kan afstemmes.
    return LedgerEntry(
        transfer_id=None, account_id=account.id,
        signed_amount=Decimal(account.balance).quantize(TWO),
        entry_type=LedgerEntryType.OPENING_BALANCE,
    )


def seed() -> None:
    reset = "--reset" in sys.argv
    db = SessionLocal()
    try:
        if reset:
            _reset(db)
        elif _already_seeded(db):
            print("Databasen er allerede seedet. Brug --reset for at gendanne.")
            return

        pw_hash = hash_password(_demo_password())
        accounts_by_number: dict[str, Account] = {}
        customers_by_number: dict[str, Customer] = {}
        posting_count = 0

        # Kunder + konti + åbningssaldi
        for first, last, cnr, email, accounts in CUSTOMERS:
            user = CustomerUser(email=email.lower(), password_hash=pw_hash, is_active=True)
            db.add(user)
            db.flush()
            cust = Customer(user_id=user.id, customer_number=cnr,
                            first_name=first, last_name=last, phone="+45 20000000")
            db.add(cust)
            db.flush()
            customers_by_number[cnr] = cust
            for accnr, atype, opening in accounts:
                acc = Account(customer_id=cust.id, account_number=accnr,
                              account_type=atype, balance=Decimal(opening).quantize(TWO),
                              currency="DKK", status=AccountStatus.ACTIVE)
                db.add(acc)
                db.flush()
                accounts_by_number[accnr] = acc
                db.add(_opening_entry(acc))
                posting_count += 1
        db.flush()

        # Gennemførte overførsler (hver = 2 posteringer)
        for i, (snr, sacc, racc, amount, text) in enumerate(TRANSFERS):
            cust = customers_by_number[snr]
            sender = accounts_by_number[sacc]
            receiver = accounts_by_number[racc]
            amt = Decimal(amount).quantize(TWO)
            t = Transfer(
                sender_account_id=sender.id, receiver_account_id=receiver.id,
                amount=amt, status=TransferStatus.COMPLETED, description=text,
                initiated_by_customer_id=cust.id, idempotency_key=f"seed-{i:03d}",
            )
            db.add(t)
            db.flush()
            sender.balance = (sender.balance - amt).quantize(TWO)
            receiver.balance = (receiver.balance + amt).quantize(TWO)
            db.add_all([
                LedgerEntry(transfer_id=t.id, account_id=sender.id,
                            signed_amount=(-amt).quantize(TWO), entry_type=LedgerEntryType.DEBIT),
                LedgerEntry(transfer_id=t.id, account_id=receiver.id,
                            signed_amount=amt, entry_type=LedgerEntryType.CREDIT),
            ])
            posting_count += 2
        db.flush()

        # Låneansøgninger
        for cnr, amount, ltype, dur, purpose, status in LOANS:
            cust = customers_by_number[cnr]
            la = LoanApplication(
                customer_id=cust.id, amount=Decimal(amount).quantize(TWO),
                loan_type=ltype, duration_months=dur, purpose=purpose, status=status,
            )
            if status != LoanStatus.AFVENTER:
                la.decision_note = "Afgjort i demodata."
                la.reviewed_at = utcnow()
            db.add(la)

        # Supportsager (P1)
        support = [
            ("100002", "Kan ikke se min opsparing", "Hej, min opsparingskonto mangler."),
            ("100003", "Spørgsmål til gebyr", "Hvorfor er der trukket et gebyr?"),
            ("100005", "Kort virker ikke", "Mit kort blev afvist i butikken."),
        ]
        for cnr, subject, body in support:
            cust = customers_by_number[cnr]
            case = SupportCase(customer_id=cust.id, subject=subject,
                               status=SupportStatus.AABEN)
            db.add(case)
            db.flush()
            db.add(SupportMessage(case_id=case.id, sender_type="CUSTOMER",
                                  sender_id=cust.id, body=body))

        db.commit()
        print("Seed gennemført:")
        print(f"  Kunder:        {len(CUSTOMERS)}")
        print(f"  Konti:         {len(accounts_by_number)}")
        print(f"  Posteringer:   {posting_count}")
        print(f"  Overførsler:   {len(TRANSFERS)}")
        print(f"  Låneansøgn.:   {len(LOANS)}")
        print(f"  Supportsager:  {len(support)}")
        if not os.environ.get("SEED_CUSTOMER_PASSWORD"):
            print(f"\n  Demo-kunde-password (development): {_demo_password()}")
            print("  Login f.eks.: anders@demobank.local / kundenr 100001")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
