#!/bin/bash

# Backup database before any operations
BACKUP_DIR="/home/manu/justmailit/db_backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "Creating database backup at $TIMESTAMP..."

# Backup main database
if [ -f "/home/manu/justmailit/sendmail/justmailit.db" ]; then
    cp /home/manu/justmailit/sendmail/justmailit.db "$BACKUP_DIR/justmailit_$TIMESTAMP.db"
    echo "✅ Backed up: sendmail/justmailit.db"
fi

# Keep only last 10 backups
ls -t "$BACKUP_DIR"/*.db | tail -n +11 | xargs -r rm
echo "✅ Database backup complete: $BACKUP_DIR/justmailit_$TIMESTAMP.db"
