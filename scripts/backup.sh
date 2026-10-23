#!/usr/bin/env bash
# Standalone conference-laptop backup. No Python, oc, jq or SQLite CLI needed.
# Requires Bash 3.2+, curl and the standard macOS/Linux utilities checked below.
set -Eeuo pipefail
umask 077

usage() {
    cat <<'HELP'
Usage:
  WHISPER_URL=https://game.example ADMIN_TOKEN_FILE=./admin-token ./backup.sh [--loop]
  ./backup.sh --validate ./backups/tournament-....db

Environment:
  WHISPER_URL       HTTPS game URL (required)
  ADMIN_TOKEN_FILE  File containing admin token (recommended, chmod 600)
  ADMIN_TOKEN       Alternative token; otherwise read silently from the terminal
  BACKUP_DIR        Destination outside cluster (default: ./backups)
  INTERVAL          Seconds between loop snapshots (default: 300)
  KEEP_BACKUPS      Number of validated snapshots retained (default: 288)
  CURL_CA_BUNDLE    Optional trusted CA file for a private cluster certificate

Copy just this script to a conference laptop. Keep its terminal running and the
laptop awake. Never use shell tracing (bash -x) with credentials. Ctrl+C stops.
No TLS bypass, package installation, cluster credentials or repository needed.
HELP
}
fail() { echo "ERROR: $*" >&2; exit 1; }
LOOP=false
VALIDATE=""
while (($#)); do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --loop) LOOP=true; shift ;;
        --validate) (($# >= 2)) || fail '--validate requires a file'; VALIDATE=$2; shift 2 ;;
        *) fail "Unknown argument: $1" ;;
    esac
done
for cmd in cat curl mkdir mktemp chmod date wc od mv rm sleep; do
    command -v "$cmd" >/dev/null || fail "Required OS tool missing: $cmd (see --help)"
done
validate_snapshot() {
    local path=$1 signature size page_size pages
    local -a bytes
    [[ -f "$path" ]] || { echo 'Backup file missing' >&2; return 1; }
    signature=""
    IFS= read -r -n 15 signature < "$path" || return 1
    [[ "$signature" == 'SQLite format 3' ]] || { echo 'Not a SQLite backup' >&2; return 1; }
    size=$(wc -c < "$path")
    # Header offsets 16..31 contain page size and database page count (big endian).
    read -r -a bytes <<< "$(od -An -tu1 -j16 -N16 "$path")"
    [[ ${#bytes[@]} -eq 16 ]] || return 1
    page_size=$((bytes[0] * 256 + bytes[1]))
    [[ "$page_size" -ne 1 ]] || page_size=65536
    ((page_size >= 512 && page_size <= 65536 && (page_size & (page_size - 1)) == 0)) || return 1
    pages=$((bytes[12] * 16777216 + bytes[13] * 65536 + bytes[14] * 256 + bytes[15]))
    ((pages > 0 && size == page_size * pages)) || { echo 'SQLite backup is truncated or has an invalid page count' >&2; return 1; }
    # This checks format/completeness. Rehearse restore to verify recoverability.
}
if [[ -n "$VALIDATE" ]]; then
    validate_snapshot "$VALIDATE" || fail 'Snapshot header/length validation failed'
    echo "Snapshot header and complete page count verified: $VALIDATE"
    exit 0
fi
URL=${WHISPER_URL:-}
[[ "$URL" == https://* && "$URL" != *'?'* && "$URL" != *'#'* && "$URL" != *'@'* ]] || fail 'Set WHISPER_URL to the HTTPS game URL (no credentials/query string)'
INTERVAL=${INTERVAL:-300}
KEEP_BACKUPS=${KEEP_BACKUPS:-288}
[[ "$INTERVAL" =~ ^[1-9][0-9]*$ && "$KEEP_BACKUPS" =~ ^[1-9][0-9]*$ ]] || fail 'INTERVAL and KEEP_BACKUPS must be positive integers'
if [[ -n ${ADMIN_TOKEN_FILE:-} ]]; then
    [[ -r "$ADMIN_TOKEN_FILE" ]] || fail 'Cannot read ADMIN_TOKEN_FILE'
    ADMIN_TOKEN=$(< "$ADMIN_TOKEN_FILE")
elif [[ -z ${ADMIN_TOKEN:-} ]]; then
    [[ -t 0 ]] || fail 'Set ADMIN_TOKEN_FILE or ADMIN_TOKEN for unattended operation'
    IFS= read -r -s -p 'Admin token: ' ADMIN_TOKEN
    echo
fi
[[ -n "$ADMIN_TOKEN" && "$ADMIN_TOKEN" != *$'\n'* && "$ADMIN_TOKEN" != *$'\r'* ]] || fail 'Invalid admin token'
BACKUP_DIR=${BACKUP_DIR:-./backups}
mkdir -p -- "$BACKUP_DIR"
# Keep the curl credential configuration and downloads private.
WORK=$(mktemp -d)
chmod 700 "$WORK"
PART=""
cleanup() {
    [[ -z "$PART" ]] || rm -f -- "$PART"
    rm -rf -- "$WORK"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
# curl reads a private config file so the token never appears in its process args.
ESCAPED=${ADMIN_TOKEN//\\/\\\\}
ESCAPED=${ESCAPED//\"/\\\"}
printf 'header = "Authorization: Bearer %s"\n' "$ESCAPED" > "$WORK/auth"
unset ADMIN_TOKEN ESCAPED
LAST_SUCCESS=NONE
snapshot() {
    local destination attempt
    local -a snapshots
    PART=$(mktemp "$BACKUP_DIR/.whisper.XXXXXXXX") || return 1
    for attempt in 1 2 3; do
        if curl --config "$WORK/auth" --proto '=https' --tlsv1.2 \
            --fail --silent --show-error --connect-timeout 15 --max-time 120 \
            --output "$PART" "${URL%/}/api/admin/backup" && validate_snapshot "$PART"; then
            # Random suffix also prevents collisions between two backup processes.
            destination="$BACKUP_DIR/tournament-$(date -u +%Y-%m-%dT%H-%M-%SZ)-${PART##*.}.db"
            mv -- "$PART" "$destination" || return 1
            PART=""
            # Lexical timestamp order; only known snapshots are eligible for pruning.
            shopt -s nullglob
            snapshots=("$BACKUP_DIR"/tournament-*.db)
            shopt -u nullglob
            local excess=$((${#snapshots[@]} - KEEP_BACKUPS)) i removed=0
            for ((i=0; i<${#snapshots[@]} && removed<excess; i++)); do
                [[ "${snapshots[i]}" != "$destination" ]] || continue
                rm -f -- "${snapshots[i]}" || return 1
                removed=$((removed + 1))
            done
            LAST_SUCCESS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
            echo "[$LAST_SUCCESS] Saved complete SQLite download: $destination ($(wc -c < "$destination") bytes)"
            return 0
        fi
        echo "ERROR: Backup attempt $attempt/3 failed; last success in this process: $LAST_SUCCESS. Previous backups retained." >&2
        [[ "$attempt" -eq 3 ]] || sleep 2
    done
    rm -f -- "$PART"
    PART=""
    return 1
}
while true; do
    if ! snapshot; then
        $LOOP || fail 'No verified snapshot saved; check TLS, URL, token and disk space'
    fi
    $LOOP || exit 0
    sleep "$INTERVAL"
done
