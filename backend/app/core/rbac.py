"""
Rollebaseret adgangskontrol (afsnit 2.3, FR-16).

Roller afledes 1:1 af virksomhedens tre AD-afdelingsgrupper (IT og drift,
Kundeservice, Investering). Adgang til medarbejderportalen kræver medlemskab af
mindst én af dem. Rettigheder håndhæves ALTID server-side (SEC-05). Denne modul
definerer rolle-enum, mapping fra AD-grupper og en rolle-til-rettigheds-matrix
brugt af både API og frontend-visninger.
"""
from __future__ import annotations

import enum

from app.config import settings


class Role(str, enum.Enum):
    """Én rolle pr. AD-afdeling."""
    IT_OG_DRIFT = "IT_OG_DRIFT"
    KUNDESERVICE = "KUNDESERVICE"
    INVESTERING = "INVESTERING"


class Permission(str, enum.Enum):
    # Rettighederne er uændrede; de tildeles via afdelingsrollerne nedenfor.
    CUSTOMER_LOOKUP = "CUSTOMER_LOOKUP"
    ACCOUNT_FREEZE = "ACCOUNT_FREEZE"
    SUPPORT_CASE_MANAGE = "SUPPORT_CASE_MANAGE"
    # Lån
    LOAN_DECIDE = "LOAN_DECIDE"
    # Revision
    AUDIT_READ = "AUDIT_READ"
    # Admin
    SYSTEM_STATUS_READ = "SYSTEM_STATUS_READ"


# Afdelingsrolle -> tilladte rettigheder.
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.IT_OG_DRIFT: {
        Permission.SYSTEM_STATUS_READ,
        Permission.AUDIT_READ,
    },
    Role.KUNDESERVICE: {
        Permission.CUSTOMER_LOOKUP,
        Permission.ACCOUNT_FREEZE,
        Permission.SUPPORT_CASE_MANAGE,
    },
    Role.INVESTERING: {
        Permission.LOAN_DECIDE,
        Permission.CUSTOMER_LOOKUP,
    },
}


def ad_group_to_role_map() -> dict[str, Role]:
    """Mapping fra (konfigurerbare) AD-afdelingsgrupper til roller (sammenlignes uden store/små bogstaver)."""
    return {
        settings.ad_group_it_drift.strip().lower(): Role.IT_OG_DRIFT,
        settings.ad_group_kundeservice.strip().lower(): Role.KUNDESERVICE,
        settings.ad_group_investering.strip().lower(): Role.INVESTERING,
    }


def roles_from_ad_groups(group_names: list[str]) -> list[Role]:
    """
    Oversæt en liste af AD-gruppenavne (CN'er) til applikationsroller.
    Ukendte grupper ignoreres. Rækkefølgen er deterministisk.
    """
    mapping = ad_group_to_role_map()
    roles: list[Role] = []
    for g in group_names:
        role = mapping.get(g.strip().lower())
        if role and role not in roles:
            roles.append(role)
    return roles


def has_portal_access(group_names: list[str]) -> bool:
    """AD-03: adgang til medarbejderportalen = medlem af mindst én afdelingsgruppe."""
    return len(roles_from_ad_groups(group_names)) > 0


def permissions_for_roles(roles: list[Role]) -> set[Permission]:
    perms: set[Permission] = set()
    for r in roles:
        perms |= ROLE_PERMISSIONS.get(r, set())
    return perms


def has_permission(roles: list[Role], permission: Permission) -> bool:
    return permission in permissions_for_roles(roles)
