"""
Overførsler: T08 (gyldig), T09 (ingen dækning), T10 (idempotens),
T11 (samtidige overførsler). Verificerer saldi, ledger og atomicitet.
"""
from __future__ import annotations

import threading
from decimal import Decimal

import pytest

from app.database import SessionLocal
from app.models.account import Account
from app.models.ledger_helpers import ledger_sum_for_transfer  # se nedenfor
from app.config import settings


def _login(client, c):
    r = client.post("/api/v1/customer/auth/login",
                    json={"identifier": c["email"], "password": c["password"]})
    assert r.status_code == 200
    return r.json()["csrf_token"]


def test_t08_valid_transfer(client, db, make_customer):
    sender = make_customer(balance="1000.00")
    receiver = make_customer(balance="0.00")
    csrf = _login(client, sender)

    r = client.post("/api/v1/customer/transfers",
                    headers={"X-CSRF-Token": csrf},
                    json={
                        "sender_account_id": sender["account"].id,
                        "receiver_account_number": receiver["account"].account_number,
                        "amount": "250.00",
                        "description": "Test",
                        "idempotency_key": "test-key-00000001",
                    })
    assert r.status_code == 200
    assert r.json()["status"] == "COMPLETED"

    # Saldi opdateret korrekt
    db.expire_all()
    s = db.get(Account, sender["account"].id)
    rcv = db.get(Account, receiver["account"].id)
    assert s.balance == Decimal("750.00")
    assert rcv.balance == Decimal("250.00")

    # Ledger: to poster, sum nul (FR-11)
    tid = r.json()["id"]
    assert ledger_sum_for_transfer(db, tid) == Decimal("0.00")


def test_t09_insufficient_funds(client, db, make_customer):
    sender = make_customer(balance="100.00")
    receiver = make_customer(balance="0.00")
    csrf = _login(client, sender)

    r = client.post("/api/v1/customer/transfers",
                    headers={"X-CSRF-Token": csrf},
                    json={
                        "sender_account_id": sender["account"].id,
                        "receiver_account_number": receiver["account"].account_number,
                        "amount": "500.00",
                        "idempotency_key": "test-key-00000002",
                    })
    assert r.status_code == 422
    assert r.json()["code"] == "INSUFFICIENT_FUNDS"

    db.expire_all()
    assert db.get(Account, sender["account"].id).balance == Decimal("100.00")
    assert db.get(Account, receiver["account"].id).balance == Decimal("0.00")


def test_t10_idempotency_no_double_charge(client, db, make_customer):
    sender = make_customer(balance="1000.00")
    receiver = make_customer(balance="0.00")
    csrf = _login(client, sender)
    payload = {
        "sender_account_id": sender["account"].id,
        "receiver_account_number": receiver["account"].account_number,
        "amount": "300.00",
        "idempotency_key": "same-key-duplicate-01",
    }
    r1 = client.post("/api/v1/customer/transfers", headers={"X-CSRF-Token": csrf}, json=payload)
    r2 = client.post("/api/v1/customer/transfers", headers={"X-CSRF-Token": csrf}, json=payload)
    assert r1.status_code == 200 and r2.status_code == 200
    # Samme transfer-id returneres, kun én økonomisk postering.
    assert r1.json()["id"] == r2.json()["id"]

    db.expire_all()
    assert db.get(Account, sender["account"].id).balance == Decimal("700.00")


@pytest.mark.skipif(
    settings.database_url.startswith("sqlite"),
    reason="Ægte samtidighed/låsning (T11) kræver PostgreSQL; sæt TEST_DATABASE_URL.",
)
def test_t11_concurrent_transfers_no_overdraft(client, db, make_customer):
    sender = make_customer(balance="1000.00")
    receiver = make_customer(balance="0.00")
    csrf = _login(client, sender)

    results: list[int] = []

    def do_transfer(key: str):
        from fastapi.testclient import TestClient
        from app.main import create_app
        cl = TestClient(create_app("all"))
        login = cl.post("/api/v1/customer/auth/login",
                        json={"identifier": sender["email"], "password": sender["password"]})
        own_csrf = login.json()["csrf_token"]   # hver tråd har sit eget CSRF-token
        r = cl.post("/api/v1/customer/transfers",
                    headers={"X-CSRF-Token": own_csrf},
                    json={"sender_account_id": sender["account"].id,
                          "receiver_account_number": receiver["account"].account_number,
                          "amount": "800.00", "idempotency_key": key})
        results.append(r.status_code)

    t1 = threading.Thread(target=do_transfer, args=("conc-00000001",))
    t2 = threading.Thread(target=do_transfer, args=("conc-00000002",))
    t1.start(); t2.start(); t1.join(); t2.join()

    # Kun én af to 800-overførsler kan lykkes fra en saldo på 1000.
    db.expire_all()
    assert db.get(Account, sender["account"].id).balance >= Decimal("0.00")
    assert results.count(200) == 1
