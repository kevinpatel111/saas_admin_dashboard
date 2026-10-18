#!/usr/bin/env bash
# ==============================================================================
# Production Deployment & Update Script for SaaS Admin Dashboard
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "======================================================================="
echo "Starting Deployment for SaaS Admin Dashboard"
echo "======================================================================="

# 1. Verify .env exists
if [ ! -f "${PROJECT_ROOT}/.env" ]; then
    echo "[-] Error: .env file is missing at ${PROJECT_ROOT}/.env"
    echo "    Please copy .env.example to .env and configure secrets first."
    exit 1
fi

# 2. Build and launch containers
echo "[*] Building and starting Docker containers..."
docker compose -f "${PROJECT_ROOT}/compose.yaml" up --build -d

# 3. Wait for database and application readiness
echo "[*] Waiting for application container to become healthy..."
MAX_ATTEMPTS=20
ATTEMPT=1
while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    STATUS=$(docker inspect --format='{{json .State.Health.Status}}' "$(docker compose -f "${PROJECT_ROOT}/compose.yaml" ps -q app)" 2>/dev/null || echo '"unknown"')
    if [ "$STATUS" = '"healthy"' ]; then
        echo "[+] App container is healthy!"
        break
    fi
    echo "    Attempt $ATTEMPT/$MAX_ATTEMPTS: Status is $STATUS, waiting 5s..."
    sleep 5
    ATTEMPT=$((ATTEMPT + 1))
done

if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
    echo "[-] Warning: App container health check did not report healthy in time. Checking logs:"
    docker compose -f "${PROJECT_ROOT}/compose.yaml" logs --tail=30 app
fi

# 4. Run database migrations
echo "[*] Running Alembic database migrations..."
docker compose -f "${PROJECT_ROOT}/compose.yaml" exec app alembic upgrade head

echo "======================================================================="
echo "[+] Deployment completed successfully!"
echo "======================================================================="
echo "Helpful commands:"
echo "  - View live logs:     docker compose logs -f"
echo "  - Create admin user:  docker compose exec -it app python scripts/create_admin.py"
echo "  - Database backup:    bash scripts/backup_db.sh"
echo "======================================================================="
