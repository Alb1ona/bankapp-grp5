"""
Medarbejder/AD-scenarier:
  T03 - gyldigt AD-login i adgangsgruppe -> rolle ifølge AD.
  T04 - gyldig AD-bruger uden bankgruppe -> adgang afvist.
  T05 - AD-konto fjernet fra gruppe -> aktiv adgang bortfalder ved genvalidering.
  T07 - SUPPORT forsøger lånegodkendelse -> 403.
  T12 - låneansøgning afgøres kun af LOAN_OFFICER, og kun én gang.
"""
from __future__ import annotations

from app.config import settings


ACCESS = settings.ad_access_group          # BANK-App-Employees
G_SUPPORT = settings.ad_group_support       # BANK-App-Support
G_LOANS = settings.ad_group_loans           # BANK-App-Loans


def _emp(object_guid, groups, is_active=True, password="AD-pass-123", display="Medarbejder"):
    return {"password": password, "object_guid": object_guid,
            "display_name": display, "groups": groups, "is_active": is_active}


def test_t03_valid_ad_login_gets_role(client, fake_ad):
    fake_ad({"ida": _emp("guid-ida-001", [ACCESS, G_SUPPORT])})
    r = client.post("/api/v1/internal/auth/login",
                    json={"username": "ida", "password": "AD-pass-123"})
    assert r.status_code == 200
    body = r.json()
    assert "SUPPORT" in body["employee"]["roles"]
    assert "CUSTOMER_LOOKUP" in body["employee"]["permissions"]


def test_t04_valid_user_without_bank_group_denied(client, fake_ad):
    # Gyldige credentials, men ikke medlem af adgangsgruppen.
    fake_ad({"gustav": _emp("guid-gustav", ["Some-Other-Group"])})
    r = client.post("/api/v1/internal/auth/login",
                    json={"username": "gustav", "password": "AD-pass-123"})
    assert r.status_code == 403
    # Ingen medarbejdersession oprettet.
    r2 = client.get("/api/v1/internal/auth/me")
    assert r2.status_code == 401


def test_t05_access_revoked_blocks_next_action(client, fake_ad, monkeypatch):
    # Tving genvalidering ved hvert kald (AD-06).
    monkeypatch.setattr(settings, "ad_revalidate_seconds", 0)
    adapter = fake_ad({"karl": _emp("guid-karl", [ACCESS, G_SUPPORT])})

    r = client.post("/api/v1/internal/auth/login",
                    json={"username": "karl", "password": "AD-pass-123"})
    assert r.status_code == 200

    # Fjern Karl fra adgangsgruppen i AD.
    adapter._users["karl"]["groups"] = ["Some-Other-Group"]

    # Næste handling skal blokeres og sessionen tilbagekaldes.
    r = client.get("/api/v1/internal/system/status")
    assert r.status_code == 403


def test_t07_support_cannot_approve_loan(client, fake_ad, make_customer, db):
    from app.services.loan_service import create_application
    from decimal import Decimal

    cust = make_customer()
    loan = create_application(db, customer_id=cust["customer"].id, amount=Decimal("10000"),
                              loan_type="FORBRUG", duration_months=12, purpose="Test")
    db.commit()

    fake_ad({"ida": _emp("guid-ida-001", [ACCESS, G_SUPPORT])})
    login = client.post("/api/v1/internal/auth/login",
                        json={"username": "ida", "password": "AD-pass-123"})
    csrf = login.json()["csrf_token"]

    r = client.patch(f"/api/v1/internal/loans/{loan.id}/decision",
                     headers={"X-CSRF-Token": csrf},
                     json={"approve": True, "decision_note": "Godkendt"})
    assert r.status_code == 403

    # Ansøgningen er uændret.
    db.expire_all()
    from app.models.loan import LoanApplication, LoanStatus
    assert db.get(LoanApplication, loan.id).status == LoanStatus.AFVENTER


def test_t12_loan_decided_once_by_loan_officer(client, fake_ad, make_customer, db):
    from app.services.loan_service import create_application
    from decimal import Decimal

    cust = make_customer()
    loan = create_application(db, customer_id=cust["customer"].id, amount=Decimal("50000"),
                              loan_type="BIL", duration_months=48, purpose="Bil")
    db.commit()

    fake_ad({"ivan": _emp("guid-ivan", [ACCESS, G_LOANS], display="Ivan Lån")})
    login = client.post("/api/v1/internal/auth/login",
                        json={"username": "ivan", "password": "AD-pass-123"})
    csrf = login.json()["csrf_token"]

    # Første afgørelse lykkes.
    r1 = client.patch(f"/api/v1/internal/loans/{loan.id}/decision",
                      headers={"X-CSRF-Token": csrf},
                      json={"approve": True, "decision_note": "Kreditvurdering ok"})
    assert r1.status_code == 200
    assert r1.json()["status"] == "GODKENDT"
    assert r1.json()["reviewed_by_employee_id"] is not None

    # Anden afgørelse afvises (allerede afgjort).
    r2 = client.patch(f"/api/v1/internal/loans/{loan.id}/decision",
                      headers={"X-CSRF-Token": csrf},
                      json={"approve": False, "decision_note": "Fortryder"})
    assert r2.status_code == 409
    assert r2.json()["code"] == "LOAN_ALREADY_DECIDED"
