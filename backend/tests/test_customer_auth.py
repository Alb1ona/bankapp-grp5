"""T01: kundelogin/logout. T02: rate limiting ved gentagne fejl-logins."""
from __future__ import annotations


def test_t01_login_and_logout(client, make_customer):
    c = make_customer(password="Hemmelig-123")
    # Login
    r = client.post("/api/v1/customer/auth/login",
                    json={"identifier": c["email"], "password": "Hemmelig-123"})
    assert r.status_code == 200
    body = r.json()
    assert "csrf_token" in body
    assert body["customer"]["customer_number"] == c["number"]

    # Session virker: /me returnerer kunden
    r = client.get("/api/v1/customer/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == c["email"]

    # Logout tilbagekalder sessionen
    r = client.post("/api/v1/customer/auth/logout")
    assert r.status_code == 200
    r = client.get("/api/v1/customer/auth/me")
    assert r.status_code == 401


def test_login_with_customer_number(client, make_customer):
    c = make_customer(password="Kode-9999", number="900123")
    r = client.post("/api/v1/customer/auth/login",
                    json={"identifier": "900123", "password": "Kode-9999"})
    assert r.status_code == 200


def test_t02_rate_limit_on_repeated_failures(client, make_customer):
    c = make_customer(password="RigtigKode-1")
    # Standardgrænse er 5 forsøg i vinduet.
    last = None
    for _ in range(7):
        last = client.post("/api/v1/customer/auth/login",
                           json={"identifier": c["email"], "password": "forkert"})
    # Efter grænsen rammes 429 (generisk fejl, afslører ikke brugeropslag).
    assert last.status_code == 429
    assert last.json()["code"] == "RATE_LIMITED"


def test_generic_error_hides_user_existence(client):
    # Ukendt bruger giver 401, ikke 404 - afslører ikke om kontoen findes.
    r = client.post("/api/v1/customer/auth/login",
                    json={"identifier": "findes-ikke@test.local", "password": "x"})
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHENTICATED"
