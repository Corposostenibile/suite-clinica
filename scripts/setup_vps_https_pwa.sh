#!/usr/bin/env bash
set -euo pipefail

# Setup HTTPS reverse proxy for Suite Clinica on a VPS:
# - optional DuckDNS IP update
# - nginx install/config
# - Let's Encrypt certificate via certbot
#
# Usage:
#   bash scripts/setup_vps_https_pwa.sh \
#     --domain suite-clinica.duckdns.org \
#     --upstream http://127.0.0.1:3001 \
#     --email admin@example.com \
#     [--duckdns-token <token>] \
#     [--duckdns-subdomain suite-clinica] \
#     [--enable-ufw]

DOMAIN=""
UPSTREAM="http://127.0.0.1:3001"
EMAIL=""
DUCKDNS_TOKEN=""
DUCKDNS_SUBDOMAIN=""
ENABLE_UFW="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="${2:-}"; shift 2 ;;
    --upstream)
      UPSTREAM="${2:-}"; shift 2 ;;
    --email)
      EMAIL="${2:-}"; shift 2 ;;
    --duckdns-token)
      DUCKDNS_TOKEN="${2:-}"; shift 2 ;;
    --duckdns-subdomain)
      DUCKDNS_SUBDOMAIN="${2:-}"; shift 2 ;;
    --enable-ufw)
      ENABLE_UFW="true"; shift 1 ;;
    *)
      echo "Argomento non riconosciuto: $1" >&2
      exit 1 ;;
  esac
done

if [[ -z "${DOMAIN}" || -z "${EMAIL}" ]]; then
  echo "Parametri obbligatori mancanti."
  echo "Esempio:"
  echo "  bash scripts/setup_vps_https_pwa.sh --domain suite-clinica.duckdns.org --email admin@example.com"
  exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo non trovato. Script richiede privilegi amministrativi."
  exit 1
fi

if [[ -n "${DUCKDNS_TOKEN}" && -n "${DUCKDNS_SUBDOMAIN}" ]]; then
  echo "[1/8] Aggiornamento record DuckDNS..."
  DUCKDNS_URL="https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}&ip="
  DUCKDNS_RESPONSE="$(curl -fsSL "${DUCKDNS_URL}" || true)"
  if [[ "${DUCKDNS_RESPONSE}" != "OK" ]]; then
    echo "Aggiornamento DuckDNS fallito: ${DUCKDNS_RESPONSE}" >&2
    exit 1
  fi
fi

echo "[2/8] Verifica DNS ${DOMAIN}..."
if ! command -v dig >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y dnsutils
fi
DNS_IP="$(dig +short "${DOMAIN}" | head -n1 || true)"
if [[ -z "${DNS_IP}" ]]; then
  echo "DNS non risolto per ${DOMAIN}. Controlla il record prima di continuare." >&2
  exit 1
fi
echo "Risoluzione DNS: ${DOMAIN} -> ${DNS_IP}"

echo "[3/8] Installazione pacchetti..."
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx

echo "[4/8] Test upstream ${UPSTREAM}..."
if ! curl -fsS -I "${UPSTREAM}" >/dev/null; then
  echo "Upstream non raggiungibile: ${UPSTREAM}" >&2
  exit 1
fi

echo "[5/8] Configurazione Nginx..."
sudo tee "/etc/nginx/sites-available/${DOMAIN}" >/dev/null <<EOF
map \$http_upgrade \$connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    location / {
        proxy_pass ${UPSTREAM};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
EOF

sudo ln -sfn "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx

if [[ "${ENABLE_UFW}" == "true" ]]; then
  echo "[6/8] Configurazione UFW..."
  sudo ufw allow OpenSSH || true
  sudo ufw allow 'Nginx Full' || true
  sudo ufw --force enable || true
fi

echo "[7/8] Emissione certificato Let's Encrypt..."
sudo certbot --nginx -d "${DOMAIN}" --non-interactive --agree-tos -m "${EMAIL}" --redirect

echo "[8/8] Verifica HTTPS..."
curl -I --max-time 15 "https://${DOMAIN}" | head -n 1

cat <<MSG

Setup completato.
URL applicazione:
  https://${DOMAIN}

Test PWA da tablet:
1) Apri https://${DOMAIN}/auth/login
2) Installa da browser (Aggiungi a Home / Installa app)
3) Apri una volta online, poi prova offline

MSG
