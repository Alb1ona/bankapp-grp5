"""
FastAPI-applikation og entrypoint.

API-02: kunde- og medarbejder-API kan køre på separate listeners/hosts, så
interne ruter ikke kan proxys fra DMZ. Styres med miljøvariablen API_SURFACE:
  * customer  -> kun /api/v1/customer/*   (eksponeres via DMZ-reverse proxy)
  * internal  -> kun /api/v1/internal/*   (kun på internt netværk/VLAN 50)
  * all       -> begge (kun til lokal udvikling)
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.deps import get_request_id
from app.config import settings
from app.core.errors import DomainError

# Routers
from app.api.v1.customer import auth as customer_auth
from app.api.v1.customer import accounts as customer_accounts
from app.api.v1.customer import transfers as customer_transfers
from app.api.v1.customer import loans as customer_loans
from app.api.v1.internal import auth as internal_auth
from app.api.v1.internal import customers as internal_customers
from app.api.v1.internal import loans as internal_loans
from app.api.v1.internal import audit_routes as internal_audit
from app.api.v1.internal import system as internal_system


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """SEC-07: sikkerhedsheaders på alle svar."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_handler(request: Request, exc: DomainError):
        # SEC-08: kun public_message til klienten; detail logges server-side.
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "code": exc.code,
                "message": exc.public_message,
                "request_id": get_request_id(request),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        # API-04: 422 uden at afsløre interne detaljer.
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Ugyldige oplysninger i forespørgslen.",
                "request_id": get_request_id(request),
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        # SEC-08: ingen stack trace/SQL til klienten.
        return JSONResponse(
            status_code=500,
            content={
                "code": "APPLICATION_ERROR",
                "message": "Der opstod en intern fejl.",
                "request_id": get_request_id(request),
            },
        )


def create_app(surface: str | None = None) -> FastAPI:
    surface = (surface or os.environ.get("API_SURFACE", "all")).lower()
    docs_url = "/docs" if settings.expose_openapi_docs else None
    app = FastAPI(
        title=f"{settings.bank_display_name} API",
        version="1.0.0",
        docs_url=docs_url,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.expose_openapi_docs else None,
    )

    app.add_middleware(SecurityHeadersMiddleware)

    # CORS: kun de konfigurerede frontend-origins, med cookies.
    allow_origins = []
    if surface in ("customer", "all"):
        allow_origins.append(settings.customer_frontend_origin)
    if surface in ("internal", "all"):
        allow_origins.append(settings.internal_frontend_origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
    )

    _register_error_handlers(app)

    if surface in ("customer", "all"):
        app.include_router(customer_auth.router)
        app.include_router(customer_accounts.router)
        app.include_router(customer_transfers.router)
        app.include_router(customer_loans.router)
    if surface in ("internal", "all"):
        app.include_router(internal_auth.router)
        app.include_router(internal_customers.router)
        app.include_router(internal_loans.router)
        app.include_router(internal_audit.router)
        app.include_router(internal_system.router)

    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok", "surface": surface, "application": settings.app_name}

    return app


app = create_app()
