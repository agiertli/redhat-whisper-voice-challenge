#!/bin/bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-whisper}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
ADMIN_TOKEN="${ADMIN_TOKEN:?Set ADMIN_TOKEN env var}"
INTERVAL="${INTERVAL:-900}"

ROUTE=$(oc get route whisper-ui -n "$NAMESPACE" -o jsonpath='{.spec.host}')
mkdir -p "$BACKUP_DIR"

do_backup() {
    local TIMESTAMP
    TIMESTAMP=$(date +%Y-%m-%d_%H-%M)
    local DEST="$BACKUP_DIR/tournament-$TIMESTAMP.db"

    echo "[$(date +%H:%M:%S)] Downloading backup from https://$ROUTE ..."
    if curl -sSf -o "$DEST" "https://$ROUTE/api/admin/backup?token=$ADMIN_TOKEN"; then
        local SIZE
        SIZE=$(wc -c < "$DEST" | tr -d ' ')
        local TOTAL
        TOTAL=$(ls -1 "$BACKUP_DIR"/tournament-*.db 2>/dev/null | wc -l | tr -d ' ')
        echo "[$(date +%H:%M:%S)] Saved: $DEST ($SIZE bytes) | Total backups: $TOTAL"

        ls -1t "$BACKUP_DIR"/tournament-*.db 2>/dev/null | tail -n +51 | while read -r old; do
            echo "Pruning: $old"
            rm -f "$old"
        done
    else
        echo "[$(date +%H:%M:%S)] ERROR: Backup failed (curl exit $?)"
    fi
}

if [[ "${1:-}" == "--loop" ]]; then
    echo "Continuous backup mode: every ${INTERVAL}s ($(( INTERVAL / 60 )) min)"
    echo "Saving to: $BACKUP_DIR"
    echo "Press Ctrl+C to stop"
    echo "---"
    while true; do
        do_backup
        sleep "$INTERVAL"
    done
else
    do_backup
fi
