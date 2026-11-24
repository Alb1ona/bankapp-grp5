"""
Applikationskonfiguration (FORM-05, SEC-09).

Alle miljøafhængige værdier - IP-adresser, hostnavne, LDAP-DN'er, secrets -
læses fra miljøvariabler / .env og har INGEN hardcodede produktionsværdier.
Dette gør lokal udvikling mulig, inden bankapplikations-VM'en oprettes.
"""
from __future__ import annotations

from decimal import Decimal
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Applikation
    app_name: str = "bankapp"
    app_env: str = "development"
    app_secret_key: str = "dev-only-insecure-secret-change-me"
    bank_display_name: str = "Demobank"
    demo_banner: bool = True

    # Netværk
    customer_frontend_origin: str = "http://localhost:5173"
    internal_frontend_origin: str = "http://localhost:5174"

    # Database
    database_url: str = "postgresql+psycopg://bankapp:bankapp@localhost:5432/bankapp"
    database_sslmode: str = "prefer"
    database_sslrootcert: str = ""

    # Sessioner
    session_idle_timeout_minutes: int = 30
    session_cookie_secure: bool = True
    session_cookie_samesite: str = "lax"

    # Rate limiting
    login_rate_limit_max: int = 5
    login_rate_limit_window_seconds: int = 300

    # Overførsler
    transfer_max_amount_dkk: Decimal = Decimal("50000.00")

    # Active Directory / LDAPS
    ad_enabled: bool = False
    ad_server_uri: str = ""
    ad_base_dn: str = ""
    ad_bind_dn: str = ""
    ad_bind_password: str = ""
    ad_user_search_filter: str = "(sAMAccountName={username})"
    ad_tls_ca_cert: str = ""
    ad_revalidate_seconds: int = 300
    ad_dev_fixture: str = ""        # sti til FakeLdapAdapter-fixture (kun AD_ENABLED=false)
    ad_access_group: str = "BANK-App-Employees"
    ad_group_support: str = "BANK-App-Support"
    ad_group_loans: str = "BANK-App-Loans"
    ad_group_auditors: str = "BANK-App-Auditors"
    ad_group_admins: str = "BANK-App-Admins"

    # Logging
    security_log_path: str = "./security.jsonl"
    security_log_to_stdout: bool = True

    # API
    expose_openapi_docs: bool = True

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Cachet, så .env kun læses én gang pr. proces."""
    return Settings()


settings = get_settings()
