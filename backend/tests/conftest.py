"""
Testopsætning. Sætter miljøvariabler FØR app importeres, så en isoleret
test-database bruges. Default er en midlertidig SQLite-fil, så testene kan køre
uden PostgreSQL; sæt TEST_DATABASE_URL for at køre mod rigtig PostgreSQL
(anbefales til concurrency-/låsningstest T11, DB-03).
"""
from __future__ import annotations

import os
import tempfile

# --- Miljø skal sættes før import af app-moduler ---
_tmp_db = os.path.join(tempfile.gettempdir(), "bankapp_test.db")
os.environ.setdefault("DATABASE_URL",
                      os.environ.get("TEST_DATABASE_URL", f"sqlite+pysqlite:///{_tmp_db}"))
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")   # TestClient kører over http
os.environ.setdefault("SECURITY_LOG_PATH", os.path.join(tempfile.gettempdir(), "bankapp_test.jsonl"))
os.environ.setdefault("AD_ENABLED", "false")
os.environ.setdefault("LOGIN_RATE_LIMIT_MAX", "5")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, engine, SessionLocal  # noqa: E402
import app.models  # noqa: E402,F401
from app.main import create_app  # noqa: E402
from app.core.security import hash_password  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    # Fjern evt. gammel SQLite-fil for en ren tavle.
    if settings.database_url.startswith("sqlite") and os.path.exists(_tmp_db):
        os.remove(_tmp_db)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    """Tøm tabeller mellem tests for isolation."""
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """In-memory rate limiter er global; nulstil så tests ikke påvirker hinanden."""
    from app.core.ratelimit import login_rate_limiter
    login_rate_limiter._hits.clear()
    yield


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client():
    return TestClient(create_app("all"))


# --- Hjælpere til at oprette testdata ---------------------------------------
@pytest.fixture
def make_customer(db):
    from app.models.customer import Customer, CustomerUser
    from app.models.account import Account, AccountType, AccountStatus
    from decimal import Decimal

    created = {"counter": 0}

    def _make(password="Test-1234", balance="1000.00", email=None, number=None):
        created["counter"] += 1
        i = created["counter"]
        email = email or f"kunde{i}@test.local"
        number = number or f"90000{i}"
        user = CustomerUser(email=email, password_hash=hash_password(password), is_active=True)
        db.add(user)
        db.flush()
        cust = Customer(user_id=user.id, customer_number=number,
                        first_name=f"Test{i}", last_name="Kunde")
        db.add(cust)
        db.flush()
        acc = Account(customer_id=cust.id, account_number=f"80000000{i:02d}",
                      account_type=AccountType.LOENKONTO,
                      balance=Decimal(balance), currency="DKK",
                      status=AccountStatus.ACTIVE)
        db.add(acc)
        db.commit()
        return {"user": user, "customer": cust, "account": acc,
                "email": email, "number": number, "password": password}

    return _make


@pytest.fixture
def fake_ad(monkeypatch):
    """Injicér en FakeLdapAdapter med et testfixture (ingen hardcodede passwords i src)."""
    from app.core.ldap_adapter import FakeLdapAdapter

    def _install(users: dict):
        adapter = FakeLdapAdapter(users)
        monkeypatch.setattr("app.api.v1.internal.auth.get_ldap_adapter", lambda: adapter)
        monkeypatch.setattr("app.api.deps.get_ldap_adapter", lambda: adapter)
        return adapter

    return _install
