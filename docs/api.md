# API-oversigt

Versioneret REST-API (JSON) med adskilte navnerum for kunder og medarbejdere.
OpenAPI-dokumentation genereres automatisk på `/docs` (kan slås fra med
`EXPOSE_OPENAPI_DOCS=false`).

Alle ændrende requests kræver `X-CSRF-Token`-header (værdien returneres ved login).
Sessioner bæres i en HttpOnly-cookie (`bankapp_session`).

## Kunde-API (`/api/v1/customer`, eksponeres via DMZ)

| Metode | Rute | Beskrivelse |
|---|---|---|
| POST | `/auth/login` | Login med e-mail/kundenummer + adgangskode |
| POST | `/auth/logout` | Log ud (tilbagekalder session) |
| GET | `/auth/me` | Nuværende kunde |
| GET | `/accounts` | Kundens konti |
| GET | `/accounts/{id}/transactions` | Transaktioner (paginering: `limit`, `offset`) |
| POST | `/transfers` | Opret overførsel (kræver CSRF + `idempotency_key`) |
| GET | `/transfers` | Kundens overførsler |
| POST | `/loans` | Opret låneansøgning (kræver CSRF) |
| GET | `/loans` | Kundens låneansøgninger |

## Medarbejder-API (`/api/v1/internal`, kun internt netværk)

| Metode | Rute | Rettighed |
|---|---|---|
| POST | `/auth/login` | AD/LDAPS-login |
| POST | `/auth/logout` | Log ud |
| GET | `/auth/me` | Medarbejder, roller, rettigheder |
| GET | `/customers?q=` | `CUSTOMER_LOOKUP` |
| GET | `/customers/{id}/accounts` | `CUSTOMER_LOOKUP` |
| GET | `/loans?status=` | `LOAN_DECIDE` |
| PATCH | `/loans/{id}/decision` | `LOAN_DECIDE` (kræver CSRF) |
| GET | `/audit/events` | `AUDIT_READ` (filtre: `event_type`, `actor_id`, `result`, `request_id`, `since`, `until`) |
| GET | `/system/status` | `SYSTEM_STATUS_READ` |

## HTTP-statuskoder (API-04)

| Kode | Betydning |
|---|---|
| 401 | Ikke logget ind / ugyldig session |
| 403 | Mangler rettighed / CSRF-fejl / forkert portal |
| 404 | Ressource findes ikke (bruges også ved fremmed ejerskab, så eksistens ikke lækkes) |
| 409 | Konflikt (fx lån allerede afgjort) |
| 422 | Valideringsfejl / forretningsregel (fx manglende dækning) |
| 429 | Rate limit overskredet |

Fejlformat: `{"code": "...", "message": "...", "request_id": "..."}` –
aldrig stack traces, SQL eller interne detaljer (SEC-08).

## Reverse proxy (DMZ)

DMZ-webserveren serverer den statiske kunde-frontend og proxyer **kun**
kunde-API'et. Eksempel (nginx):

```nginx
# Kun kundernes API må proxys fra DMZ (API-02).
location /api/v1/customer/ {
    proxy_pass http://BANKAPP_VM:8000;   # udfyldes ved installation
    proxy_set_header Host $host;
    proxy_set_header X-Request-ID $request_id;
}
# /api/v1/internal/ proxys ALDRIG her.
```
