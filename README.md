# Demobank – simuleret banksystem

Et fiktivt demonstrationsbanksystem udviklet til Modul 7 (IT-sikkerhed).
Består af en **offentlig kundeportal (netbank)**, en **intern medarbejderportal**
og en **fælles backend/API** med PostgreSQL-datamodel.

> ⚠️ **Alle data er fiktive.** Systemet håndterer ikke rigtige penge eller
> rigtige kundedata. Login-sider er tydeligt markeret som demo.

Dette repo indeholder **kun selve applikationen**. Oprettelse af VM'er, VLAN,
firewallregler, domænecontroller, Wazuh og OPNsense er **ikke** en del af koden –
applikationen integrerer med dem gennem dokumenterede, konfigurerbare grænseflader.

---

## Arkitektur

Applikationens tre lag passer til jeres netværksopdeling:

```
   Internettet
        │  HTTPS (kun kunde-API)
        ▼
┌─────────────────────┐
│  DMZ-webserver       │   Statisk kunde-frontend + reverse proxy
│  (VLAN 90)           │   → kun /api/v1/customer/*
└─────────┬───────────┘
          │  internt
          ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Bankapplikation     │────▶│  PostgreSQL          │
│  backend + intern    │     │  (VLAN 60)           │
│  portal (VLAN 50)    │     └─────────────────────┘
└───┬─────────────┬────┘
    │ LDAPS       │ JSON-logs
    ▼             ▼
┌────────────┐  ┌────────────┐
│ Active Dir │  │ Wazuh SIEM │
│ (VLAN 50)  │  │ (VLAN 70)  │
└────────────┘  └────────────┘
```

Kunde- og medarbejder-API kan køre på **separate listeners** (miljøvariablen
`API_SURFACE`), så interne medarbejderruter aldrig kan proxyes fra DMZ (krav API-02).

| Mappe | Indhold | Teknologi |
|---|---|---|
| `backend/` | API, datamodel, migrationer, AD-integration, tests | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| `frontend-customer/` | Offentlig netbank | React + TypeScript (Vite) |
| `frontend-employee/` | Intern medarbejderportal | React + TypeScript (Vite) |
| `docs/` | Rollematrix, logskema, API- og installationsguide | — |

---

## Hurtig start (lokal udvikling)

Kræver: **Python 3.12+**, **Node 18+**, og enten **Docker** (til PostgreSQL) eller
en lokal PostgreSQL. Alt kan køres uden at bankapplikations-VM'en findes endnu.

### 1. Database

```bash
docker compose up -d db          # starter PostgreSQL på localhost:5432
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # ret evt. DATABASE_URL hvis ikke Docker-standard
alembic upgrade head             # opretter alle tabeller (DB-01)
python seed.py                   # fiktive testdata (udskriver demo-kundepassword)

# Kør begge API-overflader lokalt (kun til udvikling):
uvicorn app.main:app --reload --port 8000
```

I produktion køres **to** instanser med adskilte overflader:

```bash
API_SURFACE=customer uvicorn app.main:app --port 8000   # eksponeres via DMZ
API_SURFACE=internal uvicorn app.main:app --port 8001   # kun internt (VLAN 50)
```

### 3. Frontends

```bash
cd frontend-customer && cp .env.example .env && npm install && npm run dev   # http://localhost:5173
cd frontend-employee && cp .env.example .env && npm install && npm run dev   # http://localhost:5174
```

### 4. Log ind

- **Kunde:** brug e-mailen og demo-passwordet, som `seed.py` udskrev
  (fx `anders@demobank.local`).
- **Medarbejder:** kræver AD. Til lokal udvikling bruges en testbar LDAP-adapter –
  se "Active Directory" nedenfor.

---

## Tests

De obligatoriske scenarier **T01–T14** er implementeret.

```bash
cd backend
source .venv/bin/activate
pytest                 # kører mod midlertidig SQLite (ingen PostgreSQL krævet)
```

Concurrency-/låsningstesten **T11** kræver rigtig PostgreSQL og aktiveres med:

```bash
TEST_DATABASE_URL=postgresql+psycopg://bankapp:bankapp_dev_only@localhost:5432/bankapp_test pytest
```

| Test | Scenarie |
|---|---|
| T01 | Kundelogin og logout |
| T02 | Rate limiting ved gentagne fejl-logins |
| T03 | Gyldigt AD-login i afdelingsgruppe → rolle ifølge AD |
| T04 | Gyldig AD-bruger uden afdelingsgruppe → afvist |
| T05 | AD-adgang fjernet → aktiv session blokeres ved genvalidering |
| T06 | Kunde tilgår anden kundes konto → 404, sikkerhedslog |
| T07 | Kundeservice forsøger lånegodkendelse → 403 |
| T08 | Gyldig overførsel → saldi, ledger og audit stemmer |
| T09 | Overførsel uden dækning → afvist, ingen ændring |
| T10 | Gentagen request med samme idempotency key → kun én postering |
| T11 | Samtidige overførsler → intet overtræk |
| T12 | Låneansøgning afgøres kun af Investering, kun én gang |
| T13 | Kunde-session afvist på intern API-rute |
| T14 | Intern fejl → generisk besked uden secrets |

---

## Active Directory (medarbejderlogin)

- **Produktion:** sæt `AD_ENABLED=true` og udfyld LDAPS-indstillingerne i `.env`
  (server-URI, base-DN, læsebegrænset søgekonto, CA-cert, gruppenavne).
  Login sker via LDAPS med certifikatvalidering; ingen AD-passwords gemmes.
- **Lokal udvikling:** lad `AD_ENABLED=false`. Kopiér
  `backend/ad_dev_fixture.example.json` til `backend/ad_dev_fixture.json`
  (gitignored), udfyld test-passwords, og sæt `AD_DEV_FIXTURE=ad_dev_fixture.json`.
  Så kan I logge ind med testbrugerne:

  | Bruger | AD-gruppe | Rolle |
  |---|---|---|
  | `ida` | Kundeservice | KUNDESERVICE |
  | `ivan` | Investering | INVESTERING |
  | `karl`, `anna` | IT og drift | IT_OG_DRIFT |
  | `uffe` | (ingen) | afvises |

Roller er virksomhedens tre **AD-afdelinger** og bestemmes **udelukkende** af
AD-gruppemedlemskab (gruppenavnene sættes i `AD_GROUP_IT_DRIFT`,
`AD_GROUP_KUNDESERVICE` og `AD_GROUP_INVESTERING`):

| Afdeling | Kan |
|---|---|
| IT og drift | Se systemstatus og auditlog |
| Kundeservice | Kundeopslag, kontospærring, supportsager |
| Investering | Lånebehandling og kundeopslag |

Adgang til medarbejderportalen kræver medlemskab af mindst én af de tre grupper
(se `docs/rollematrix.md`).

---

## Sikkerhed (udvalgte punkter)

- Kunde-adgangskoder hashes med **Argon2id**; AD-passwords gemmes aldrig.
- **Server-side sessioner**, kun hash gemt, HttpOnly+Secure cookies, 30 min. timeout.
- **CSRF-beskyttelse** på alle ændrende requests (X-CSRF-Token).
- **RBAC** håndhæves server-side på hvert endpoint (ikke kun i frontend).
- **BOLA/IDOR-beskyttelse**: ejerskab tjekkes på hver kundeforespørgsel.
- **Rate limiting** på begge loginflows med generiske fejlbeskeder.
- **Atomiske, idempotente overførsler** med dobbelt bogføring og række-låsning.
- **Struktureret JSON-audit** til Wazuh (se `docs/logskema.md`).
- Ingen stack traces, SQL eller secrets i klientfejl.

---

## Dokumentation

- `docs/rollematrix.md` – roller, AD-grupper og rettigheder
- `docs/logskema.md` – JSON-logformat og eventtyper til Wazuh
- `docs/api.md` – API-endpoints
- `docs/vm-installation.md` – installation på bankapplikations-VM'en senere

## Leverancer (jf. afsnit 11.2)

- [x] Kildekode: to React/TypeScript-portaler + FastAPI-backend
- [x] SQLAlchemy-modeller, Alembic-migrationer, seed-script
- [x] LDAPS-integration med konfigurerbar gruppemapping
- [x] API-dokumentation og rolle-/rettighedsmatrix
- [x] JSON-logskema med dokumenterede eventtyper
- [x] Automatiske tests (T01–T14)
- [x] README med opstart, miljøvariabler og VM-installationsguide
- [x] `.env.example` uden adgangskoder + reverse proxy-ruter
