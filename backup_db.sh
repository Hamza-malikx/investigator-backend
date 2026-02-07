#!/bin/bash

set -e

# Navigate to backend directory
cd "$(dirname "$0")"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="investigator_prod"
BACKUP_DIR="./backups"
BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create database backup
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U investigator_user $DB_NAME > $BACKUP_FILE

# Compress the backup
gzip $BACKUP_FILE

# Keep only last 7 days of backups
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Database backup completed: ${BACKUP_FILE}.gz"