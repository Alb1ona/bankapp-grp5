"""
Rollebaseret adgangskontrol (afsnit 2.3, FR-16).

Roller afledes af AD-gruppemedlemskab. Rettigheder håndhæves ALTID server-side
(SEC-05). Denne modul definerer rolle-enum, mapping fra AD-grupper og en
rolle-til-rettigheds-matrix brugt af både API og frontend-visninger.
"""
from __future__ import annotations

import enum

from app.config import settings


class Role(str, enum.Enum):
    SUPPORT = "SUPPORT"
    LOAN_OFFICER = "LOAN_OFFICER"
    AUDITOR = "AUDITOR"
    ADMIN = "ADMIN"


class Permission(str, enum.Enum):
    # Kundeservice
    CUSTOMER_LOOKUP = "CUSTOMER_LOOKUP"
    ACCOUNT_FREEZE = "ACCOUNT_FREEZE"
    SUPPORT_CASE_MANAGE = "SUPPORT_CASE_MANAGE"
    # Lån
    LOAN_DECIDE = "LOAN_DECIDE"
    # Revision
    AUDIT_READ = "AUDIT_READ"
    # Admin
    SYSTEM_STATUS_READ = "SYSTEM_STATUS_READ"


# Rolle -> tilladte rettigheder (afsnit 2.3).
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.SUPPORT: {
        Permission.CUSTOMER_LOOKUP,
        Permission.ACCOUNT_FREEZE,
        Permission.SUPPORT_CASE_MANAGE,
    },
    Role.LOAN_OFFICER: {
        Permission.LOAN_DECIDE,
    },
    Role.AUDITOR: {
        Permission.AUDIT_READ,
    },
    Role.ADMIN: {
        Permission.SYSTEM_STATUS_READ,
    },
}


def ad_group_to_role_map() -> dict[str, Role]:
    """Mapping fra (konfigurerbare) AD-gruppenavne til roller."""
    return {
        settings.ad_group_support.lower(): Role.SUPPORT,
        settings.ad_group_loans.lower(): Role.LOAN_OFFICER,
        settings.ad_group_auditors.lower(): Role.AUDITOR,
        settings.ad_group_admins.lower(): Role.ADMIN,
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


def permissions_for_roles(roles: list[Role]) -> set[Permission]:
    perms: set[Permission] = set()
    for r in roles:
        perms |= ROLE_PERMISSIONS.get(r, set())
    return perms


def has_permission(roles: list[Role], permission: Permission) -> bool:
    return permission in permissions_for_roles(roles)
