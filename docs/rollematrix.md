# Rolle- og rettighedsmatrix

Roller afledes **udelukkende** af AD-gruppemedlemskab. Alle gruppenavne/DN'er er
konfigurerbare i `.env` (`AD_GROUP_*`). Applikationen ændrer aldrig AD-grupper.

## Overordnet adgang

Alle medarbejdere skal være medlem af den overordnede adgangsgruppe
(`AD_ACCESS_GROUP`, standard `BANK-App-Employees`). Uden den afvises login (AD-03),
uanset øvrige grupper.

## Roller → AD-grupper → rettigheder

| Rolle | AD-gruppe (standardforslag) | Rettigheder | Må IKKE |
|---|---|---|---|
| **SUPPORT** | `BANK-App-Support` | Søge kunder, læse konto-/transaktionsdata, besvare sager, spærre konti | Overføre penge, godkende lån, ændre roller |
| **LOAN_OFFICER** | `BANK-App-Loans` | Se og afgøre låneansøgninger med begrundelse | Ændre roller, foretage overførsler |
| **AUDITOR** | `BANK-App-Auditors` | Læse og filtrere auditlog (skrivebeskyttet) | Ændre bankdata, slette logs |
| **ADMIN** | `BANK-App-Admins` | Se systemstatus og applikationsoplysninger | Overføre penge, godkende lån, tildele sig selv rettigheder |

## Rettigheder (Permission-enum) → endpoints

| Permission | Endpoints der kræver den |
|---|---|
| `CUSTOMER_LOOKUP` | `GET /api/v1/internal/customers`, `GET /api/v1/internal/customers/{id}/accounts` |
| `LOAN_DECIDE` | `GET /api/v1/internal/loans`, `PATCH /api/v1/internal/loans/{id}/decision` |
| `AUDIT_READ` | `GET /api/v1/internal/audit/events` |
| `SYSTEM_STATUS_READ` | `GET /api/v1/internal/system/status` |

## Håndhævelse

- Håndhæves **server-side** i `app/api/deps.py` via `require_permission(...)`.
  Frontend skjuler menupunkter (FR-16), men backend afgør altid adgang (SEC-05/06).
- En **kundesession** afvises på alle `/internal`-ruter, og en **medarbejdersession**
  afvises på kunders private netbankruter (API-01).
- Gruppemedlemskab genvalideres mod AD mindst hvert 5. minut i aktive sessioner
  (`AD_REVALIDATE_SECONDS`). Fjernet adgang blokerer næste handling (AD-06).
