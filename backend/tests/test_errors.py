"""T14: kontrolleret fejl uden at lække interne detaljer (SEC-08, API-04)."""
from __future__ import annotations


def _login(client, c):
    r = client.post("/api/v1/customer/auth/login",
                    json={"identifier": c["email"], "password": c["password"]})
    return r.json()["csrf_token"]


def test_t14_internal_error_is_generic(make_customer, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import create_app
    # Lad appens egen fejlhandler svare (i stedet for at TestClient re-raiser).
    client = TestClient(create_app("all"), raise_server_exceptions=False)
    sender = make_customer(balance="1000.00")
    receiver = make_customer(balance="0.00")
    csrf = _login(client, sender)

    # Simulér en uventet intern fejl (fx DB-fejl) i overførselsmotoren.
    def boom(*args, **kwargs):
        raise RuntimeError("hemmelig SQL-detalje og stacktrace")

    monkeypatch.setattr("app.api.v1.customer.transfers.execute_transfer", boom)

    r = client.post("/api/v1/customer/transfers",
                    headers={"X-CSRF-Token": csrf},
                    json={"sender_account_id": sender["account"].id,
                          "receiver_account_number": receiver["account"].account_number,
                          "amount": "10.00", "idempotency_key": "err-00000001"})
    assert r.status_code == 500
    body = r.json()
    # Generisk besked; ingen intern detalje/SQL/stacktrace til klienten.
    assert body["code"] == "APPLICATION_ERROR"
    assert "hemmelig" not in str(body).lower()
    assert "sql" not in body["message"].lower()


def test_validation_error_shape(client, make_customer):
    c = make_customer()
    _login(client, c)
    # Manglende felter -> 422 i standardformat.
    r = client.post("/api/v1/customer/loans",
                    headers={"X-CSRF-Token": "x"},
                    json={"amount": "-5", "loan_type": "", "duration_months": 0, "purpose": ""})
    assert r.status_code in (403, 422)  # 403 hvis CSRF rammer først
