#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
mkdir -p "${BACKUP_DIR}"

STAMP="$(date +%F-%H%M%S)"

docker run --rm \
  -v n8n_n8n_data:/volume \
  -v "$(pwd)/${BACKUP_DIR}:/backup" \
  alpine \
  sh -c "tar czf /backup/n8n-data-${STAMP}.tgz -C /volume ."

if docker ps --format '{{.Names}}' | grep -q '^nutrihealth-n8n-postgres$'; then
  docker exec nutrihealth-n8n-postgres pg_dump -U "${POSTGRES_USER:-n8n}" "${POSTGRES_DB:-n8n}" > "${BACKUP_DIR}/postgres-${STAMP}.sql"
fi

echo "Backup completed in ${BACKUP_DIR}"
