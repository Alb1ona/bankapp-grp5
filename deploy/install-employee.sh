#!/usr/bin/env bash
# Installerer medarbejderportalen (statisk frontend + nginx-config) på bankapp01.
# Kør som root fra repo'et:  sudo ./deploy/install-employee.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Dette script skal køres som root (brug sudo)." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_ROOT=/var/www/employee
SITE_AVAILABLE=/etc/nginx/sites-available/employee
SITE_ENABLED=/etc/nginx/sites-enabled/employee

if [[ ! -f "$SCRIPT_DIR/employee/index.html" ]]; then
  echo "Fandt ikke $SCRIPT_DIR/employee/index.html - er frontend'en bygget?" >&2
  exit 1
fi

# nginx (installeres kun hvis det mangler)
if ! command -v nginx >/dev/null 2>&1; then
  echo "nginx mangler - installerer..."
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y nginx
fi

# Statiske filer
mkdir -p "$WEB_ROOT"
cp -r "$SCRIPT_DIR"/employee/* "$WEB_ROOT"/

# nginx-site
install -m 644 "$SCRIPT_DIR/nginx-employee.conf" "$SITE_AVAILABLE"
ln -sf "$SITE_AVAILABLE" "$SITE_ENABLED"

# Fjern default-sitet, hvis det er aktivt (det lytter også på port 80)
if [[ -L /etc/nginx/sites-enabled/default ]]; then
  rm /etc/nginx/sites-enabled/default
fi

nginx -t
systemctl enable nginx >/dev/null 2>&1 || true
if systemctl is-active --quiet nginx; then
  systemctl reload nginx
else
  systemctl start nginx
fi

echo "Medarbejderportal installeret: http://192.168.50.100/"
