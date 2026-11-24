# Installation på bankapplikations-VM'en (senere)

Denne guide beskriver, hvordan applikationen installeres, når infrastrukturen er
klar. Selve VM-, VLAN-, firewall-, AD- og Wazuh-opsætningen er **ikke** en del af
koden – den forudsættes etableret separat.

## Forudsætninger (etableres af infrastrukturprojektet)

| Komponent | Placering | Applikationens behov |
|---|---|---|
| Bankapplikations-VM | Server-VLAN 50 | Python 3.12, kører backend + intern portal |
| PostgreSQL | VLAN 60 | Database, nåbar fra VLAN 50 på 5432/TLS |
| Active Directory | VLAN 50 | LDAPS (636) + en læsebegrænset søgekonto |
| DMZ-webserver | VLAN 90 | Serverer kunde-frontend, proxyer kunde-API |
| Wazuh-agent | På app-VM'en | Læser `SECURITY_LOG_PATH` |

## 1. Hent koden og opret miljø

```bash
cd /opt
git clone <repo> bankapp && cd bankapp/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Konfigurér `.env`

```bash
cp .env.example .env
```

Udfyld **ved installation** (ingen værdier gættes – jf. afsnit 1.1):

- `APP_ENV=production`, `APP_SECRET_KEY=<tilfældig 64 tegn>`
- `DATABASE_URL=postgresql+psycopg://bankapp:<kode>@<db-host-VLAN60>:5432/bankapp`
- `DATABASE_SSLMODE=verify-full`, `DATABASE_SSLROOTCERT=/sti/ca.pem`
- `AD_ENABLED=true`, `AD_SERVER_URI=ldaps://<dc-host>:636`, `AD_BASE_DN=...`
- `AD_BIND_DN=<søgekonto>`, `AD_BIND_PASSWORD=<kode>`, `AD_TLS_CA_CERT=/sti/ca.pem`
- `AD_GROUP_*` = jeres faktiske AD-gruppenavne
- `SECURITY_LOG_PATH=/var/log/bankapp/security.jsonl`
- `SESSION_COOKIE_SECURE=true`, `EXPOSE_OPENAPI_DOCS=false`
- `CUSTOMER_FRONTEND_ORIGIN` / `INTERNAL_FRONTEND_ORIGIN` = de rigtige URL'er

## 3. Opret databasen

```bash
alembic upgrade head
python seed.py        # kun hvis demodata ønskes; udelad i et "rent" miljø
```

## 4. Kør de to API-overflader adskilt (API-02)

```bash
API_SURFACE=customer uvicorn app.main:app --host 0.0.0.0 --port 8000   # mod DMZ
API_SURFACE=internal uvicorn app.main:app --host 127.0.0.1 --port 8001 # kun internt
```

Brug fx `systemd` eller `gunicorn -k uvicorn.workers.UvicornWorker` i produktion.
Bind den **interne** overflade til et interface, som kun er tilgængeligt fra det
interne netværk – aldrig fra DMZ.

## 5. Byg og udstil frontends

```bash
cd ../frontend-customer
echo "VITE_API_BASE=https://<offentlig-netbank-url>" > .env
npm ci && npm run build        # output i dist/ → lægges på DMZ-webserveren

cd ../frontend-employee
echo "VITE_API_BASE=https://<intern-portal-url>" > .env
npm ci && npm run build        # output i dist/ → udstilles KUN internt
```

## 6. Wazuh

Peg en eksisterende Wazuh-agent mod `SECURITY_LOG_PATH`. Applikationen skriver
allerede JSON Lines i det format, agenten kan opsamle (se `docs/logskema.md`).

## 7. Verifikation

- `GET /health` på begge overflader svarer `ok`.
- Kunde kan logge ind via den offentlige URL; intern portal er **ikke** nåbar
  udefra.
- En testhændelse (fx fejl-login) dukker op i `security.jsonl` og i Wazuh.
