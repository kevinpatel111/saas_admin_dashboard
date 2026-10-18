#!/usr/bin/env bash
# ==============================================================================
# Database Backup Script for SaaS Admin Dashboard (MySQL in Docker)
# ==============================================================================
set -euo pipefail

# Directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"

mkdir -p "$BACKUP_DIR"

TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
BACKUP_FILE="${BACKUP_DIR}/saas_backup_${TIMESTAMP}.sql.gz"

echo "[*] Loading environment variables..."
if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
else
    echo "[-] Error: .env file not found at ${PROJECT_ROOT}/.env"
    exit 1
fi

DB_NAME="${MYSQL_DATABASE:-saas_dashboard}"
ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD}"

echo "[*] Starting backup for database: '${DB_NAME}'..."

# Dump database using mysqldump inside the db container
docker compose -f "${PROJECT_ROOT}/compose.yaml" exec -T db \
    mysqldump -u root -p"${ROOT_PASSWORD}" \
    --single-transaction \
    --quick \
    --routines \
    --triggers \
    "${DB_NAME}" | gzip > "$BACKUP_FILE"

# Set permissions
chmod 600 "$BACKUP_FILE"

FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[+] Backup successfully completed: $BACKUP_FILE (Size: $FILE_SIZE)"

# Optional: keep backups for the last 14 days and remove older ones
echo "[*] Cleaning up backups older than 14 days..."
find "$BACKUP_DIR" -type f -name "saas_backup_*.sql.gz" -mtime +14 -exec rm -f {} \; || true
echo "[+] Done."
