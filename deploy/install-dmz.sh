#!/usr/bin/env bash
# Installerer netbank (kunde-frontend + nginx-config) på DMZ-webserveren.
# Kør som root fra repo'et:  sudo ./deploy/install-dmz.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Dette script skal køres som root (brug sudo)." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_ROOT=/var/www/netbank
SITE_AVAILABLE=/etc/nginx/sites-available/netbank
SITE_ENABLED=/etc/nginx/sites-enabled/netbank

if [[ ! -f "$SCRIPT_DIR/netbank/index.html" ]]; then
  echo "Fandt ikke $SCRIPT_DIR/netbank/index.html - er frontend'en bygget?" >&2
  exit 1
fi

# Statiske filer
mkdir -p "$WEB_ROOT"
cp -r "$SCRIPT_DIR"/netbank/* "$WEB_ROOT"/

# nginx-site
install -m 644 "$SCRIPT_DIR/nginx-netbank.conf" "$SITE_AVAILABLE"
ln -sf "$SITE_AVAILABLE" "$SITE_ENABLED"

# Fjern default-sitet, hvis det er aktivt
if [[ -L /etc/nginx/sites-enabled/default ]]; then
  rm /etc/nginx/sites-enabled/default
fi

nginx -t
systemctl reload nginx

echo "Netbank installeret: https://netbank-grp5.sof60.dk"
