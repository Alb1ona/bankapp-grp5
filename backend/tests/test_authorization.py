"""
Autorisation på tværs af identiteter:
  T06 - kunde tilgår en anden kundes konto (IDOR/BOLA).
  T13 - offentligt/kunde-kald mod intern API-rute.
"""
from __future__ import annotations


def _login_customer(client, c):
    r = client.post("/api/v1/customer/auth/login",
                    json={"identifier": c["email"], "password": c["password"]})
    assert r.status_code == 200
    return r.json()["csrf_token"]


def test_t06_cannot_access_other_customers_account(client, make_customer):
    a = make_customer()
    b = make_customer()
    _login_customer(client, a)

    # Kunde A forsøger at læse kunde B's kontotransaktioner.
    r = client.get(f"/api/v1/customer/accounts/{b['account'].id}/transactions")
    # 404 (ikke 403) så eksistensen af fremmede konti ikke afsløres.
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


def test_t13_customer_session_rejected_on_internal_route(client, make_customer):
    a = make_customer()
    _login_customer(client, a)

    # API-01: kundesession afvises på /internal-ruter.
    r = client.get("/api/v1/internal/system/status")
    assert r.status_code in (401, 403)


def test_internal_route_requires_auth(client):
    # Uden session: 401.
    r = client.get("/api/v1/internal/customers?q=test")
    assert r.status_code == 401


def test_transfer_requires_csrf(client, make_customer):
    sender = make_customer(balance="1000.00")
    receiver = make_customer(balance="0.00")
    _login_customer(client, sender)
    # Uden X-CSRF-Token header afvises ændrende request (SEC-03).
    r = client.post("/api/v1/customer/transfers",
                    json={"sender_account_id": sender["account"].id,
                          "receiver_account_number": receiver["account"].account_number,
                          "amount": "10.00", "idempotency_key": "nocsrf-00000001"})
    assert r.status_code == 403
