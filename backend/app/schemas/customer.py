"""Request/response-skemaer for kunde-API'et."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


# -- Auth ---------------------------------------------------------------------
class CustomerLoginRequest(BaseModel):
    # Login med e-mail ELLER kundenummer (KUN-01).
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class CustomerMeResponse(BaseModel):
    customer_id: str
    customer_number: str
    first_name: str
    last_name: str
    # str (ikke EmailStr): output fra egen DB; EmailStr afviser .local-domæner
    email: str


# -- Konti --------------------------------------------------------------------
class AccountResponse(BaseModel):
    id: str
    account_number: str
    account_type: str
    balance: Decimal
    currency: str
    status: str


class TransactionResponse(BaseModel):
    transfer_id: str
    created_at: datetime
    description: str | None
    signed_amount: Decimal       # negativ = hævet, positiv = indsat
    entry_type: str
    counterpart_account: str | None


# -- Overførsler --------------------------------------------------------------
class TransferCreateRequest(BaseModel):
    sender_account_id: str
    receiver_account_number: str = Field(min_length=4, max_length=20)
    amount: Decimal = Field(gt=0)
    description: str | None = Field(default=None, max_length=140)
    idempotency_key: str = Field(min_length=8, max_length=80)

    @field_validator("amount")
    @classmethod
    def _max_two_decimals(cls, v: Decimal) -> Decimal:
        if v.as_tuple().exponent < -2:
            raise ValueError("Beløb må højst have 2 decimaler.")
        return v


class TransferResponse(BaseModel):
    id: str
    sender_account_id: str | None
    receiver_account_id: str
    amount: Decimal
    status: str
    description: str | None
    created_at: datetime


# -- Lån ----------------------------------------------------------------------
class LoanCreateRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    loan_type: str = Field(min_length=1, max_length=40)
    duration_months: int = Field(ge=1, le=480)
    purpose: str = Field(min_length=3, max_length=300)


class LoanResponse(BaseModel):
    id: str
    amount: Decimal
    loan_type: str
    duration_months: int
    purpose: str
    status: str
    decision_note: str | None
    created_at: datetime
    reviewed_at: datetime | None
