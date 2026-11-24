"""
Audit- og sikkerhedslogging (afsnit 8).

To destinationer for hver hændelse:
  1. Struktureret JSON Lines til fil + stdout  -> læses af Wazuh-agent (LOG-04).
  2. Row i audit_events-tabellen               -> append-only DB-spor (DB-05, LOG-05).

LOG-03: adgangskoder, tokens, cookies, fulde kontonumre og store mængder PII
må ALDRIG logges. Kaldere sender kun id'er og korte 'reason'-tekster.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.audit import AuditEvent
from app.models.base_types import utcnow

# -- Standard event-typer (afsnit 8.1) ---------------------------------------
# Kundeautentifikation
CUSTOMER_LOGIN_SUCCESS = "CUSTOMER_LOGIN_SUCCESS"
CUSTOMER_LOGIN_FAILURE = "CUSTOMER_LOGIN_FAILURE"
CUSTOMER_LOGOUT = "CUSTOMER_LOGOUT"
CUSTOMER_RATE_LIMITED = "CUSTOMER_RATE_LIMITED"
# Active Directory
AD_LOGIN_SUCCESS = "AD_LOGIN_SUCCESS"
AD_LOGIN_FAILURE = "AD_LOGIN_FAILURE"
AD_GROUP_ACCESS_DENIED = "AD_GROUP_ACCESS_DENIED"
AD_CONNECTION_ERROR = "AD_CONNECTION_ERROR"
AD_ACCESS_REVOKED = "AD_ACCESS_REVOKED"
# Autorisation
ACCESS_DENIED = "ACCESS_DENIED"
CROSS_ACCOUNT_ACCESS_DENIED = "CROSS_ACCOUNT_ACCESS_DENIED"
INTERNAL_API_ACCESS_DENIED = "INTERNAL_API_ACCESS_DENIED"
# Bankfunktioner
TRANSFER_SUCCESS = "TRANSFER_SUCCESS"
TRANSFER_REJECTED = "TRANSFER_REJECTED"
LOAN_CREATED = "LOAN_CREATED"
LOAN_APPROVED = "LOAN_APPROVED"
LOAN_REJECTED = "LOAN_REJECTED"
# Medarbejderhandlinger
CUSTOMER_LOOKUP = "CUSTOMER_LOOKUP"
ACCOUNT_FROZEN = "ACCOUNT_FROZEN"
ACCOUNT_UNFROZEN = "ACCOUNT_UNFROZEN"
SUPPORT_CASE_UPDATED = "SUPPORT_CASE_UPDATED"
# Systemfejl
INPUT_VALIDATION_FAILED = "INPUT_VALIDATION_FAILED"
DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
APPLICATION_ERROR = "APPLICATION_ERROR"

# Severity-niveauer
INFO = "INFO"
WARNING = "WARNING"
ERROR = "ERROR"

# Resultat
SUCCESS = "SUCCESS"
DENIED = "DENIED"
FAILURE = "FAILURE"


# -- JSON-fil/stdout-logger --------------------------------------------------
_json_logger = logging.getLogger("bankapp.security")
_json_logger.setLevel(logging.INFO)
_json_logger.propagate = False

if not _json_logger.handlers:
    # Fil-handler (JSON Lines). Fejler stille, hvis stien ikke kan oprettes lokalt.
    try:
        import os
        log_dir = os.path.dirname(settings.security_log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        fh = logging.FileHandler(settings.security_log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(message)s"))
        _json_logger.addHandler(fh)
    except OSError:
        pass
    if settings.security_log_to_stdout:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter("%(message)s"))
        _json_logger.addHandler(sh)


# Nøgler der aldrig må forekomme i en logrecord (LOG-03).
_FORBIDDEN_KEYS = {"password", "token", "cookie", "secret", "authorization"}


def _sanitize(extra: dict | None) -> dict:
    if not extra:
        return {}
    return {
        k: v for k, v in extra.items()
        if k.lower() not in _FORBIDDEN_KEYS and v is not None
    }


def log_event(
    db: Session | None,
    *,
    event_type: str,
    result: str,
    severity: str = INFO,
    actor_type: str | None = None,
    actor_id: str | None = None,
    source_ip: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    request_id: str | None = None,
    reason: str | None = None,
    extra: dict | None = None,
) -> None:
    """
    Log en hændelse til både JSON-fil/stdout og (hvis db gives) audit_events.

    LOG-05: manglende adgang til logdestinationen må ALDRIG kaste videre op og
    rulle en korrekt banktransaktion tilbage -> alt her er best-effort/try-except.
    """
    ts = utcnow().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    record = {
        "timestamp": ts,                 # LOG-01: UTC/ISO 8601
        "application": "bankapp",        # LOG-01
        "event_type": event_type,
        "severity": severity,
        "result": result,
        "request_id": request_id,
    }
    if actor_type:
        record["actor_type"] = actor_type
    if actor_id:
        record["actor_id"] = actor_id
    if source_ip:
        record["source_ip"] = source_ip
    if target_type:
        record["target_type"] = target_type
    if target_id:
        record["target_id"] = target_id
    if reason:
        record["reason"] = reason
    record.update(_sanitize(extra))

    # 1) JSON Lines (best-effort)
    try:
        _json_logger.info(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    except Exception:  # noqa: BLE001 - logging må aldrig vælte en request
        pass

    # 2) DB-audit (best-effort, separat fejlhåndtering)
    if db is not None:
        try:
            db.add(AuditEvent(
                event_type=event_type,
                severity=severity,
                result=result,
                actor_type=actor_type,
                actor_id=actor_id,
                source_ip=source_ip,
                target_type=target_type,
                target_id=target_id,
                request_id=request_id,
                reason=reason,
            ))
            db.flush()
        except Exception:  # noqa: BLE001
            pass
