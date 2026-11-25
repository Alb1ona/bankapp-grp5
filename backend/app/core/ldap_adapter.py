"""
AD/LDAPS-adapter til medarbejderautentifikation (AD-01..AD-06, SEC-10).

To implementeringer bag ét interface:
  * Ldap3Adapter  - rigtig LDAPS-bind mod domænecontrolleren (produktion).
  * FakeLdapAdapter - til lokal udvikling og automatiske tests. Fixtures
    (brugere, grupper, passwords) injiceres udefra ved runtime/test -
    der er INGEN hardcodede test-adgangskoder i kildekoden.

Roller udledes aldrig her; adapteren returnerer kun rå AD-fakta (objectGUID,
brugernavn, visningsnavn, gruppe-CN'er). RBAC-laget oversætter til roller.

SEC-10: produktionsstien bruger TLS-certifikatvalidering, en læsebegrænset
søgekonto og aldrig domæneadministratorkontoen.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Protocol

from app.config import settings


@dataclass
class AdIdentity:
    object_guid: str
    username: str
    display_name: str
    group_cns: list[str] = field(default_factory=list)
    is_active: bool = True


class AdConnectionError(Exception):
    """AD kunne ikke kontaktes/valideres sikkert (-> AD_CONNECTION_ERROR, AD-05)."""


class AdAuthError(Exception):
    """Ugyldige credentials eller inaktiv/ukendt konto (-> AD_LOGIN_FAILURE)."""


class LdapAdapter(Protocol):
    def authenticate(self, username: str, password: str) -> AdIdentity:
        """Bind som brugeren og returnér vedkommendes AD-identitet. Rejser ved fejl."""
        ...

    def fetch_identity(self, username: str) -> AdIdentity:
        """Hent identitet/grupper uden password (AD-06 genvalidering)."""
        ...


# -- Rigtig LDAPS-implementering ---------------------------------------------
class Ldap3Adapter:
    """
    Produktionsadapter. Flow:
      1. Bind med den læsebegrænsede søgekonto (AD_BIND_DN).
      2. Søg brugeren -> hent DN, objectGUID, displayName, memberOf.
      3. Re-bind som brugerens DN med det angivne password (verificerer login).
      4. Luk forbindelsen.
    """

    def __init__(self) -> None:
        # Importér ldap3 dovent, så lokal udvikling uden pakken stadig virker.
        import ldap3  # noqa: F401
        self._ldap3 = ldap3

    def _server(self):
        ldap3 = self._ldap3
        tls = None
        if settings.ad_tls_ca_cert:
            import ssl
            tls = ldap3.Tls(
                ca_certs_file=settings.ad_tls_ca_cert,
                validate=ssl.CERT_REQUIRED,   # SEC-10: certifikatvalidering
            )
        return ldap3.Server(settings.ad_server_uri, use_ssl=True, tls=tls, get_info=ldap3.NONE)

    def _search_identity(self, conn, username: str) -> tuple[str, AdIdentity]:
        ldap3 = self._ldap3
        search_filter = settings.ad_user_search_filter.format(username=self._escape(username))
        conn.search(
            search_base=settings.ad_base_dn,
            search_filter=search_filter,
            search_scope=ldap3.SUBTREE,
            attributes=["objectGUID", "displayName", "sAMAccountName", "memberOf", "userAccountControl"],
        )
        if not conn.entries:
            raise AdAuthError("Bruger ikke fundet i AD")
        entry = conn.entries[0]
        guid = str(entry.objectGUID.value)
        display = str(entry.displayName.value) if entry.displayName else username
        groups = [self._cn_from_dn(dn) for dn in (entry.memberOf.values if entry.memberOf else [])]
        # userAccountControl bit 0x2 = ACCOUNTDISABLE (AD-03: inaktive afvises).
        uac = int(entry.userAccountControl.value) if entry.userAccountControl else 0
        is_active = not (uac & 0x2)
        dn = entry.entry_dn
        return dn, AdIdentity(object_guid=guid, username=username, display_name=display,
                              group_cns=groups, is_active=is_active)

    def authenticate(self, username: str, password: str) -> AdIdentity:
        ldap3 = self._ldap3
        try:
            server = self._server()
            svc = ldap3.Connection(
                server,
                user=settings.ad_bind_dn,
                password=settings.ad_bind_password,
                auto_bind=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise AdConnectionError(f"Kunne ikke binde søgekonto: {exc}") from exc

        try:
            dn, identity = self._search_identity(svc, username)
        finally:
            svc.unbind()

        if not identity.is_active:
            raise AdAuthError("Konto er deaktiveret")

        # Verificér brugerens password ved at binde som brugeren.
        try:
            user_conn = ldap3.Connection(self._server(), user=dn, password=password)
            if not user_conn.bind():
                raise AdAuthError("Ugyldige credentials")
            user_conn.unbind()
        except AdAuthError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AdConnectionError(f"LDAPS-fejl ved brugerbind: {exc}") from exc

        return identity

    def fetch_identity(self, username: str) -> AdIdentity:
        ldap3 = self._ldap3
        try:
            svc = ldap3.Connection(
                self._server(),
                user=settings.ad_bind_dn,
                password=settings.ad_bind_password,
                auto_bind=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise AdConnectionError(f"Kunne ikke binde søgekonto: {exc}") from exc
        try:
            _dn, identity = self._search_identity(svc, username)
            return identity
        finally:
            svc.unbind()

    @staticmethod
    def _cn_from_dn(dn: str) -> str:
        # "CN=Investering,OU=Groups,DC=bank,DC=local" -> "Investering"
        first = dn.split(",")[0]
        return first[3:] if first.upper().startswith("CN=") else first

    @staticmethod
    def _escape(value: str) -> str:
        # Minimal LDAP-filter-escaping (forebyg injection i søgefilter).
        for ch, rep in [("\\", r"\5c"), ("*", r"\2a"), ("(", r"\28"),
                        (")", r"\29"), ("\x00", r"\00")]:
            value = value.replace(ch, rep)
        return value


# -- Testbar/lokal adapter ----------------------------------------------------
class FakeLdapAdapter:
    """
    Til udvikling og tests. Indeholder INGEN indbyggede brugere.
    Fixtures leveres enten:
      * programmatisk af en test:  FakeLdapAdapter({"ida": {...}})
      * eller fra en fil angivet i miljøvariablen AD_DEV_FIXTURE (gitignored).
    """

    def __init__(self, fixture: dict | None = None) -> None:
        self._users: dict[str, dict] = fixture or self._load_from_env()

    @staticmethod
    def _load_from_env() -> dict:
        # Læs både fra rigtige miljøvariabler og fra .env (via settings).
        path = os.environ.get("AD_DEV_FIXTURE", "") or settings.ad_dev_fixture
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        return {}

    def authenticate(self, username: str, password: str) -> AdIdentity:
        key = username.lower()
        rec = self._users.get(key)
        if rec is None:
            raise AdAuthError("Ukendt bruger")
        if not rec.get("password") or password != rec["password"]:
            raise AdAuthError("Ugyldige credentials")
        if not rec.get("is_active", True):
            raise AdAuthError("Konto er deaktiveret")
        return self._to_identity(username, rec)

    def fetch_identity(self, username: str) -> AdIdentity:
        rec = self._users.get(username.lower())
        if rec is None:
            raise AdAuthError("Ukendt bruger")
        return self._to_identity(username, rec)

    @staticmethod
    def _to_identity(username: str, rec: dict) -> AdIdentity:
        return AdIdentity(
            object_guid=rec["object_guid"],
            username=username,
            display_name=rec.get("display_name", username),
            group_cns=list(rec.get("groups", [])),
            is_active=rec.get("is_active", True),
        )


def get_ldap_adapter() -> LdapAdapter:
    """Vælg adapter ud fra konfiguration (AD_ENABLED)."""
    if settings.ad_enabled:
        return Ldap3Adapter()
    return FakeLdapAdapter()
