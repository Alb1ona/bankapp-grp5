#!/usr/bin/env bash
# Installerer og starter bankapp's systemd-tjenester (kunde-API og internt API).
# Kør som root fra repo'et:  sudo ./deploy/install-services.sh
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Dette script skal køres som root (brug sudo)." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES=(bankapp-customer.service bankapp-internal.service)

# Logmappe til JSON-audit (SECURITY_LOG_PATH), ejet af tjenestebrugeren.
install -d -o bankadmin -g bankadmin -m 750 /var/log/bankapp

for svc in "${SERVICES[@]}"; do
  install -m 644 "$SCRIPT_DIR/$svc" "/etc/systemd/system/$svc"
done

systemctl daemon-reload
systemctl enable --now "${SERVICES[@]}"

systemctl --no-pager --lines=0 status "${SERVICES[@]}" || true
