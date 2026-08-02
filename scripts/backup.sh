#!/bin/bash
set -eo pipefail

BACKUP_DIR="./backend/storage/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DEST="$BACKUP_DIR/backup_$TIMESTAMP"

mkdir -p "$DEST"

echo "=== ScaleFlow Production Backup System ==="
echo "Targeting destination: $DEST"

# 1. Backup SQLite database metadata
if [ -f "./backend/task_schedular.db" ]; then
    echo "[1/3] Backing up SQLite task_schedular.db..."
    sqlite3 ./backend/task_schedular.db ".backup '$DEST/task_schedular.db.bak'"
elif [ -f "./task_schedular.db" ]; then
    echo "[1/3] Backing up SQLite task_schedular.db..."
    sqlite3 ./task_schedular.db ".backup '$DEST/task_schedular.db.bak'"
else
    echo "[1/3] Warning: task_schedular.db not found at expected paths."
fi

# 2. Backup Whoosh Index
WHOOSH_DIR="./backend/storage/whoosh"
if [ -d "$WHOOSH_DIR" ]; then
    echo "[2/3] Backing up Whoosh search index files..."
    cp -r "$WHOOSH_DIR" "$DEST/whoosh_index"
else
    echo "[2/3] Warning: Whoosh index directory '$WHOOSH_DIR' not found."
fi

# 3. Snapshot Qdrant database (Hit Local REST API)
echo "[3/3] Requesting Qdrant database snapshot..."
QDRANT_URL="http://localhost:6333"
# Check if qdrant is running locally, if so trigger snapshot
if curl -s -o /dev/null -w "%{http_code}" "$QDRANT_URL/collections" | grep -q "200"; then
    echo "Triggering Qdrant collection snapshots..."
    # Get all collections
    COLLECTIONS=$(curl -s "$QDRANT_URL/collections" | json_pp | grep '"name"' | awk -F'"' '{print $4}' || true)
    for col in $COLLECTIONS; do
        echo "Creating snapshot for Qdrant collection: $col"
        curl -s -X POST "$QDRANT_URL/collections/$col/snapshots" > /dev/null || true
    done
else
    echo "Qdrant REST API not reachable on port 6333. Skipping live Qdrant API snapshots."
fi

# Compress the backup archive
cd "$BACKUP_DIR"
tar -czf "scaleflow_backup_$TIMESTAMP.tar.gz" "backup_$TIMESTAMP"
rm -rf "backup_$TIMESTAMP"

echo "=========================================="
echo "SUCCESS: Backup created at $BACKUP_DIR/scaleflow_backup_$TIMESTAMP.tar.gz"
echo "=========================================="
