"""Fælles response-skemaer."""
from __future__ import annotations

from pydantic import BaseModel


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    """Ikke-afslørende fejlformat (SEC-08, API-04)."""
    code: str
    message: str
    request_id: str | None = None
