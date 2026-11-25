"""
Medarbejder/AD-scenarier. Roller = AD-afdelinger (IT og drift, Kundeservice,
Investering); adgang kræver medlemskab af mindst én af dem.
  T03 - gyldigt AD-login i afdelingsgruppe -> rolle ifølge AD.
  T04 - gyldig AD-bruger uden afdelingsgruppe -> adgang afvist.
  T05 - AD-konto fjernet fra afdelingsgruppe -> aktiv adgang bortfalder ved genvalidering.
  T07 - Kundeservice forsøger lånegodkendelse -> 403.
  T12 - låneansøgning afgøres kun af Investering, og kun én gang.
"""
from __future__ import annotations

from app.config import settings


G_IT = settings.ad_group_it_drift               # "IT og drift"
G_KUNDESERVICE = settings.ad_group_kundeservice  # "Kundeservice"
G_INVESTERING = settings.ad_group_investering    # "Investering"


def _emp(object_guid, groups, is_active=True, password="AD-pass-123", display="Medarbejder"):
    return {"password": password, "object_guid": object_guid,
            "display_name": display, "groups": groups, "is_active": is_active}


def test_t03_valid_ad_login_gets_role(client, fake_ad):
    fake_ad({"ida": _emp("guid-ida-001", [G_KUNDESERVICE])})
    r = client.post("/api/v1/internal/auth/login",
                    json={"username": "ida", "password": "AD-pass-123"})
    assert r.status_code == 200
    body = r.json()
    assert body["employee"]["roles"] == ["KUNDESERVICE"]
    assert set(body["employee"]["permissions"]) == {
        "CUSTOMER_LOOKUP", "ACCOUNT_FREEZE", "SUPPORT_CASE_MANAGE"}


def test_t04_valid_user_without_bank_group_denied(client, fake_ad):
    # Gyldige credentials, men ikke medlem af nogen afdelingsgruppe.
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
    adapter = fake_ad({"karl": _emp("guid-karl", [G_KUNDESERVICE])})

    r = client.post("/api/v1/internal/auth/login",
                    json={"username": "karl", "password": "AD-pass-123"})
    assert r.status_code == 200

    # Fjern Karl fra sin afdelingsgruppe i AD.
    adapter._users["karl"]["groups"] = ["Some-Other-Group"]

    # Næste handling skal blokeres og sessionen tilbagekaldes.
    r = client.get("/api/v1/internal/system/status")
    assert r.status_code == 403


def test_t07_kundeservice_cannot_approve_loan(client, fake_ad, make_customer, db):
    from app.services.loan_service import create_application
    from decimal import Decimal

    cust = make_customer()
    loan = create_application(db, customer_id=cust["customer"].id, amount=Decimal("10000"),
                              loan_type="FORBRUG", duration_months=12, purpose="Test")
    db.commit()

    fake_ad({"ida": _emp("guid-ida-001", [G_KUNDESERVICE])})
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


def test_t12_loan_decided_once_by_investering(client, fake_ad, make_customer, db):
    from app.services.loan_service import create_application
    from decimal import Decimal

    cust = make_customer()
    loan = create_application(db, customer_id=cust["customer"].id, amount=Decimal("50000"),
                              loan_type="BIL", duration_months=48, purpose="Bil")
    db.commit()

    fake_ad({"ivan": _emp("guid-ivan", [G_INVESTERING], display="Ivan Lån")})
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


# -- Afdelingsroller ---------------------------------------------------------
def test_role_permission_matrix():
    from app.core.rbac import Permission as P, Role, ROLE_PERMISSIONS
    assert set(Role) == {Role.IT_OG_DRIFT, Role.KUNDESERVICE, Role.INVESTERING}
    assert ROLE_PERMISSIONS[Role.IT_OG_DRIFT] == {P.SYSTEM_STATUS_READ, P.AUDIT_READ}
    assert ROLE_PERMISSIONS[Role.KUNDESERVICE] == {
        P.CUSTOMER_LOOKUP, P.ACCOUNT_FREEZE, P.SUPPORT_CASE_MANAGE}
    assert ROLE_PERMISSIONS[Role.INVESTERING] == {P.LOAN_DECIDE, P.CUSTOMER_LOOKUP}


def test_default_group_names_match_ad_departments():
    from app.core.rbac import Role, roles_from_ad_groups
    assert roles_from_ad_groups(["IT og drift", "Kundeservice", "Investering"]) == [
        Role.IT_OG_DRIFT, Role.KUNDESERVICE, Role.INVESTERING]
    # Store/små bogstaver og mellemrum omkring navnet er ligegyldige.
    assert roles_from_ad_groups(["  it OG DRIFT "]) == [Role.IT_OG_DRIFT]
    # Ukendte og gamle generiske grupper giver ingen rolle.
    assert roles_from_ad_groups(["BANK-App-Employees", "BANK-App-Support", "IT"]) == []


def test_it_og_drift_reads_status_and_audit_but_not_customers(client, fake_ad):
    fake_ad({"karl": _emp("guid-karl", [G_IT])})
    r = client.post("/api/v1/internal/auth/login",
                    json={"username": "karl", "password": "AD-pass-123"})
    assert r.status_code == 200
    assert r.json()["employee"]["roles"] == ["IT_OG_DRIFT"]
    assert client.get("/api/v1/internal/system/status").status_code == 200
    assert client.get("/api/v1/internal/audit/events").status_code == 200
    assert client.get("/api/v1/internal/customers?q=a").status_code == 403
    assert client.get("/api/v1/internal/loans").status_code == 403


def test_investering_can_lookup_customers_and_loans_only(client, fake_ad):
    fake_ad({"ivan": _emp("guid-ivan", [G_INVESTERING])})
    r = client.post("/api/v1/internal/auth/login",
                    json={"username": "ivan", "password": "AD-pass-123"})
    assert r.status_code == 200
    assert client.get("/api/v1/internal/customers?q=a").status_code == 200
    assert client.get("/api/v1/internal/loans").status_code == 200
    assert client.get("/api/v1/internal/system/status").status_code == 403
    assert client.get("/api/v1/internal/audit/events").status_code == 403


def test_old_generic_access_group_alone_is_denied(client, fake_ad):
    # Den gamle overordnede adgangsgruppe giver ikke længere adgang i sig selv.
    fake_ad({"gammel": _emp("guid-gammel", ["BANK-App-Employees"])})
    r = client.post("/api/v1/internal/auth/login",
                    json={"username": "gammel", "password": "AD-pass-123"})
    assert r.status_code == 403


def test_member_of_multiple_departments_gets_union(client, fake_ad):
    fake_ad({"multi": _emp("guid-multi", [G_KUNDESERVICE, G_INVESTERING])})
    r = client.post("/api/v1/internal/auth/login",
                    json={"username": "multi", "password": "AD-pass-123"})
    emp = r.json()["employee"]
    assert emp["roles"] == ["KUNDESERVICE", "INVESTERING"]
    assert {"LOAN_DECIDE", "CUSTOMER_LOOKUP", "ACCOUNT_FREEZE"} <= set(emp["permissions"])
