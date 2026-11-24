"""
Domæne-fejl med stabile koder.

API-laget oversætter disse til korrekte HTTP-statuskoder (API-04) og
ikke-afslørende fejlbeskeder (SEC-08). Intern diagnostik logges server-side,
aldrig til klienten.
"""
from __future__ import annotations


class DomainError(Exception):
    """Basisklasse. `public_message` er den tekst, klienten må se."""

    http_status: int = 400
    code: str = "DOMAIN_ERROR"
    public_message: str = "Handlingen kunne ikke gennemføres."

    def __init__(self, public_message: str | None = None, *, detail: str | None = None) -> None:
        if public_message:
            self.public_message = public_message
        # detail er kun til serverlog, aldrig til klienten.
        self.detail = detail or self.public_message
        super().__init__(self.detail)


class NotFoundError(DomainError):
    http_status = 404
    code = "NOT_FOUND"
    public_message = "Ressourcen blev ikke fundet."


class AuthorizationError(DomainError):
    http_status = 403
    code = "FORBIDDEN"
    public_message = "Du har ikke adgang til denne handling."


class AuthenticationError(DomainError):
    http_status = 401
    code = "UNAUTHENTICATED"
    public_message = "Login kræves."


class ValidationError(DomainError):
    http_status = 422
    code = "VALIDATION_ERROR"
    public_message = "Ugyldige oplysninger."


class ConflictError(DomainError):
    http_status = 409
    code = "CONFLICT"
    public_message = "Handlingen er i konflikt med den aktuelle tilstand."


class RateLimitedError(DomainError):
    http_status = 429
    code = "RATE_LIMITED"
    public_message = "For mange forsøg. Prøv igen senere."


# -- Specifikke bankfejl ------------------------------------------------------
class InsufficientFundsError(ValidationError):
    code = "INSUFFICIENT_FUNDS"
    public_message = "Der er ikke dækning på afsenderkontoen."


class AccountNotActiveError(ValidationError):
    code = "ACCOUNT_NOT_ACTIVE"
    public_message = "Kontoen er ikke aktiv."


class TransferLimitError(ValidationError):
    code = "TRANSFER_LIMIT"
    public_message = "Beløbet overstiger den tilladte grænse."


class LoanAlreadyDecidedError(ConflictError):
    code = "LOAN_ALREADY_DECIDED"
    public_message = "Ansøgningen er allerede afgjort."
