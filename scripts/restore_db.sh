#!/usr/bin/env bash
# ==============================================================================
# Database Restore Script for SaaS Admin Dashboard (MySQL in Docker)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -z "${1:-}" ]; then
    echo "Usage: $0 <path_to_backup.sql.gz>"
    echo "Example: $0 backups/saas_backup_20261018_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[-] Error: Backup file '$BACKUP_FILE' does not exist."
    exit 1
fi

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

echo "======================================================================="
echo "WARNING: Restoring will overwrite existing data in '${DB_NAME}'!"
echo "Target Backup: $BACKUP_FILE"
echo "======================================================================="
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "[-] Restore aborted by user."
    exit 0
fi

echo "[*] Restoring database from '$BACKUP_FILE'..."

# Decompress and restore into database
gzip -dc "$BACKUP_FILE" | docker compose -f "${PROJECT_ROOT}/compose.yaml" exec -T db \
    mysql -u root -p"${ROOT_PASSWORD}" "${DB_NAME}"

echo "[+] Database restore completed successfully."
