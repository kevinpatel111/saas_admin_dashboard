#!/usr/bin/env bash
# ==============================================================================
# Automated SSL Certificate Setup (Let's Encrypt / Certbot)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ $# -lt 2 ]; then
    echo "Usage: $0 <your-domain.com> <your-email@example.com>"
    echo "Example: $0 dashboard.mycompany.com admin@mycompany.com"
    exit 1
fi

DOMAIN="$1"
EMAIL="$2"

echo "[*] Setting up SSL for domain: '$DOMAIN'..."

# Ensure services are up so Nginx can respond to ACME challenge
echo "[*] Ensuring Nginx is running..."
docker compose -f "${PROJECT_ROOT}/compose.yaml" up -d nginx

# Run certbot via official docker image
echo "[*] Requesting SSL certificate from Let's Encrypt..."
docker run --rm \
    -v "saas_admin_dashboard_certbot_www:/var/www/certbot" \
    -v "saas_admin_dashboard_certbot_certs:/etc/letsencrypt" \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

echo "[+] Certificate obtained successfully!"

# Prepare Nginx SSL configuration from template
echo "[*] Updating Nginx configuration for HTTPS..."
sed "s/YOUR_DOMAIN_NAME/${DOMAIN}/g" "${PROJECT_ROOT}/nginx/conf.d/ssl.conf.template" > "${PROJECT_ROOT}/nginx/conf.d/default.conf"

# Update COOKIE_SECURE=true in .env
if [ -f "${PROJECT_ROOT}/.env" ]; then
    if grep -q "COOKIE_SECURE=" "${PROJECT_ROOT}/.env"; then
        sed -i 's/COOKIE_SECURE=.*/COOKIE_SECURE=true/' "${PROJECT_ROOT}/.env"
    else
        echo "COOKIE_SECURE=true" >> "${PROJECT_ROOT}/.env"
    fi
    echo "[+] COOKIE_SECURE set to true in .env"
fi

# Reload Nginx and restart app container to pick up COOKIE_SECURE
echo "[*] Reloading Nginx and restarting App container..."
docker compose -f "${PROJECT_ROOT}/compose.yaml" restart app
docker compose -f "${PROJECT_ROOT}/compose.yaml" exec nginx nginx -s reload

echo "======================================================================="
echo "[+] SUCCESS! Your dashboard is now secured with HTTPS at:"
echo "    https://${DOMAIN}"
echo "======================================================================="
