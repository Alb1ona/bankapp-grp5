#!/usr/bin/env bash
# Opretter test-AD-brugere til medarbejderportalen (FakeLdapAdapter, AD_ENABLED=false)
# og genstarter backend-tjenesterne.
#
#   sudo ./deploy/setup-ad-fixture.sh [password]     (default: Demo-Medarb-1234)
#
# Skriver backend/ad_dev_fixture.json (gitignored - committes ALDRIG) med 5 testbrugere:
#   ida  = Kundeservice      ivan = Investering
#   karl = IT og drift       anna = IT og drift      uffe = ingen gruppe (afvises)
# og sætter AD_DEV_FIXTURE + SESSION_COOKIE_SECURE=false i backend/.env.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Dette script skal køres som root (brug sudo)." >&2
  exit 1
fi

PASSWORD="${1:-Demo-Medarb-1234}"
SERVICE_USER=bankadmin
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/../backend" && pwd)"
ENV_FILE="$BACKEND_DIR/.env"
FIXTURE="$BACKEND_DIR/ad_dev_fixture.json"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Fandt ikke $ENV_FILE - opret den først (kopiér fra .env.example)." >&2
  exit 1
fi

# -- Fixture (JSON skrives af Python, så passwordet escapes korrekt) ----------
FIXTURE_PASSWORD="$PASSWORD" python3 - "$FIXTURE" <<'PY'
import json, os, sys
pw = os.environ["FIXTURE_PASSWORD"]
users = {
    "ida":  ("11111111-1111-1111-1111-111111111111", "Ida Kundeservice", ["Kundeservice"]),
    "ivan": ("33333333-3333-3333-3333-333333333333", "Ivan Investering", ["Investering"]),
    "karl": ("22222222-2222-2222-2222-222222222222", "Karl IT og drift", ["IT og drift"]),
    "anna": ("44444444-4444-4444-4444-444444444444", "Anna IT og drift", ["IT og drift"]),
    "uffe": ("55555555-5555-5555-5555-555555555555", "Uffe Udenadgang", []),
}
data = {u: {"password": pw, "object_guid": g, "display_name": d, "groups": gr, "is_active": True}
        for u, (g, d, gr) in users.items()}
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
chown "$SERVICE_USER:$SERVICE_USER" "$FIXTURE"
chmod 600 "$FIXTURE"
echo "Skrev $FIXTURE (5 testbrugere)."

# -- .env: sæt eller erstat en nøgle ------------------------------------------
set_env() {
  local key="$1" value="$2" tmp
  tmp="$(mktemp)"
  awk -v k="$key" -v v="$value" '
    BEGIN { done = 0 }
    $0 ~ "^[[:space:]]*" k "=" { print k "=" v; done = 1; next }
    { print }
    END { if (!done) print k "=" v }
  ' "$ENV_FILE" > "$tmp"
  cat "$tmp" > "$ENV_FILE"   # bevarer ejer og rettigheder på .env
  rm -f "$tmp"
}
set_env AD_DEV_FIXTURE "$FIXTURE"
set_env SESSION_COOKIE_SECURE false
echo "Opdaterede $ENV_FILE: AD_DEV_FIXTURE=$FIXTURE, SESSION_COOKIE_SECURE=false"

# Fixturen bruges kun, når AD er slået fra.
if grep -Eiq '^[[:space:]]*AD_ENABLED[[:space:]]*=[[:space:]]*"?(true|1|yes)' "$ENV_FILE"; then
  echo "ADVARSEL: AD_ENABLED=true i .env - testbrugerne bruges IKKE, før den sættes til false." >&2
fi

# -- Genstart backend --------------------------------------------------------
systemctl restart bankapp-internal bankapp-customer
sleep 2
systemctl --no-pager --lines=0 status bankapp-internal bankapp-customer || true
echo "Færdig. Log ind på http://192.168.50.100/ som ida, ivan, karl eller anna."
