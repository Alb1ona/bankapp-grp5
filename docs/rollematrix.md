# Rolle- og rettighedsmatrix

Roller svarer 1:1 til virksomhedens tre **AD-afdelinger** og afledes **udelukkende**
af AD-gruppemedlemskab. Gruppenavnene (CN) er konfigurerbare i `.env`
(`AD_GROUP_IT_DRIFT`, `AD_GROUP_KUNDESERVICE`, `AD_GROUP_INVESTERING`) og
sammenlignes uden forskel på store/små bogstaver. Applikationen ændrer aldrig AD-grupper.

## Adgang til medarbejderportalen

En medarbejder har adgang, hvis vedkommende er medlem af **mindst én** af de tre
afdelingsgrupper. En gyldig AD-bruger uden nogen af dem afvises ved login (AD-03, T04),
og mister adgangen ved næste genvalidering, hvis den sidste afdelingsgruppe fjernes
(AD-06, T05). Der er ikke længere en separat overordnet adgangsgruppe.

Er en medarbejder i flere afdelinger, får vedkommende foreningsmængden af rettighederne.

## Afdelinger → AD-grupper → rettigheder

| Rolle | AD-gruppe (standard) | Rettigheder (Permission) | Må IKKE |
|---|---|---|---|
| **IT_OG_DRIFT** | `IT og drift` | `SYSTEM_STATUS_READ`, `AUDIT_READ`: se systemstatus, læse og filtrere auditlog (skrivebeskyttet) | Se kundedata, godkende lån, overføre penge, ændre bankdata, slette logs |
| **KUNDESERVICE** | `Kundeservice` | `CUSTOMER_LOOKUP`, `ACCOUNT_FREEZE`, `SUPPORT_CASE_MANAGE`: søge kunder, læse konto-/transaktionsdata, spærre konti, besvare supportsager | Godkende lån, overføre penge, læse auditlog |
| **INVESTERING** | `Investering` | `LOAN_DECIDE`, `CUSTOMER_LOOKUP`: se og afgøre låneansøgninger med begrundelse, slå kunder op | Spærre konti, overføre penge, læse auditlog, se systemstatus |

Ingen afdeling kan tildele roller; det sker alene i AD.

## Rettigheder (Permission-enum) → endpoints

| Permission | Afdeling(er) | Endpoints der kræver den |
|---|---|---|
| `CUSTOMER_LOOKUP` | Kundeservice, Investering | `GET /api/v1/internal/customers`, `GET /api/v1/internal/customers/{id}/accounts` |
| `LOAN_DECIDE` | Investering | `GET /api/v1/internal/loans`, `PATCH /api/v1/internal/loans/{id}/decision` |
| `AUDIT_READ` | IT og drift | `GET /api/v1/internal/audit/events` |
| `SYSTEM_STATUS_READ` | IT og drift | `GET /api/v1/internal/system/status` |
| `ACCOUNT_FREEZE`, `SUPPORT_CASE_MANAGE` | Kundeservice | (reserveret til P1-funktioner; endnu ingen endpoints) |

## Håndhævelse

- Håndhæves **server-side** i `app/api/deps.py` via `require_permission(...)`.
  Frontend skjuler menupunkter (FR-16), men backend afgør altid adgang (SEC-05/06).
- En **kundesession** afvises på alle `/internal`-ruter, og en **medarbejdersession**
  afvises på kunders private netbankruter (API-01).
- Gruppemedlemskab genvalideres mod AD mindst hvert 5. minut i aktive sessioner
  (`AD_REVALIDATE_SECONDS`). Fjernet adgang blokerer næste handling (AD-06).
