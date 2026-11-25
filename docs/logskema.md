# JSON-logskema til Wazuh

Applikationen skriver én JSON-record pr. linje (JSON Lines) til stien i
`SECURITY_LOG_PATH` og til stdout (`SECURITY_LOG_TO_STDOUT`). En Wazuh-agent på
bankapplikations-VM'en kan læse filen. Oprettelse af Wazuh-regler/dekodere er
**ikke** en del af denne kode.

## Feltformat (LOG-01)

| Felt | Altid? | Beskrivelse |
|---|---|---|
| `timestamp` | ja | UTC, ISO 8601 (`...Z`) |
| `application` | ja | Altid `bankapp` |
| `event_type` | ja | Se eventtyper nedenfor |
| `severity` | ja | `INFO` / `WARNING` / `ERROR` |
| `result` | ja | `SUCCESS` / `DENIED` / `FAILURE` |
| `request_id` | ja* | Korrelations-id (kan være null ved baggrundshændelser) |
| `actor_type` | ved relevans | `CUSTOMER` / `EMPLOYEE` |
| `actor_id` | ved relevans | Kunde-id eller medarbejderens AD-objectGUID |
| `source_ip` | ved relevans | Klientens IP |
| `target_type` / `target_id` | ved relevans | Ressource, fx `transfer`, `loan_application` |
| `reason` | ved relevans | Kort årsag (ingen følsomme data) |

**Aldrig logget (LOG-03):** adgangskoder, tokens, cookies, fulde kontonumre,
store mængder personoplysninger.

## Eksempel (afvist adgang)

```json
{"timestamp":"2026-11-18T12:00:00Z","application":"bankapp","event_type":"ACCESS_DENIED","severity":"WARNING","result":"DENIED","request_id":"req-demo-001","actor_type":"EMPLOYEE","actor_id":"employee-guid","source_ip":"192.0.2.25","target_type":"loan_application","target_id":"loan-uuid","reason":"Missing LOAN_DECIDE permission"}
```

## Eventtyper (afsnit 8.1)

**Kundeautentifikation:** `CUSTOMER_LOGIN_SUCCESS`, `CUSTOMER_LOGIN_FAILURE`,
`CUSTOMER_LOGOUT`, `CUSTOMER_RATE_LIMITED`

**Active Directory:** `AD_LOGIN_SUCCESS`, `AD_LOGIN_FAILURE`,
`AD_GROUP_ACCESS_DENIED`, `AD_CONNECTION_ERROR`, `AD_ACCESS_REVOKED`

**Autorisation:** `ACCESS_DENIED`, `CROSS_ACCOUNT_ACCESS_DENIED`,
`INTERNAL_API_ACCESS_DENIED`

**Bankfunktioner:** `TRANSFER_SUCCESS`, `TRANSFER_REJECTED`, `LOAN_CREATED`,
`LOAN_APPROVED`, `LOAN_REJECTED`

**Medarbejderhandlinger:** `CUSTOMER_LOOKUP`, `ACCOUNT_FROZEN`,
`ACCOUNT_UNFROZEN`, `SUPPORT_CASE_UPDATED`

**Systemfejl:** `INPUT_VALIDATION_FAILED`, `DATABASE_CONNECTION_ERROR`,
`APPLICATION_ERROR`

## Dobbelt spor

Hver sikkerhedshændelse skrives både til JSON-filen (til Wazuh) og til tabellen
`audit_events` (append-only, læses af IT og drift i portalen). Manglende adgang til
logdestinationen ruller **aldrig** en korrekt banktransaktion tilbage (LOG-05).
