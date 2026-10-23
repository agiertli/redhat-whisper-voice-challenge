#!/usr/bin/env bash
# Tests UI -> vLLM without creating synthetic tournament players.
set -Eeuo pipefail
if [[ -n ${KUBE_CONTEXT:-} ]]; then
    oc() { command oc --context "$KUBE_CONTEXT" "$@"; }
fi
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
NS=${1:-whisper}
LANGUAGE=${2:-en}
REGISTRATION_MODE=${3:-}
TOURNAMENT_ENABLED=${4:-true}
SCRIPT="$ROOT/scripts/smoke-test.py"
SCRIPT_BYTES=$(wc -c < "$SCRIPT")
WORK=$(mktemp -d "${TMPDIR:-/tmp}/whisper-smoke.XXXXXXXX")
trap 'rm -rf "$WORK"' EXIT
# Keep source out of the exec URL. Read exactly its byte length, leaving WAV stdin
# available to the smoke check, including non-ASCII source and binary audio.
BOOTSTRAP='import sys; n=int(sys.argv.pop(1)); code=sys.stdin.buffer.read(n); exec(compile(code,"smoke-test.py","exec"))'
for ATTEMPT in 1 2 3; do
    if cat "$SCRIPT" "$ROOT/tests/audio/test-en.wav" | oc exec -i deployment/whisper-ui -n "$NS" -- \
        python3 -c "$BOOTSTRAP" "$SCRIPT_BYTES" "$LANGUAGE" "$REGISTRATION_MODE" "$TOURNAMENT_ENABLED" 2> "$WORK/error"; then
        exit 0
    else
        CODE=$?
    fi
    ERROR=$(cat "$WORK/error")
    case "$ERROR" in
        *'tls: bad record MAC'*|*'connection reset by peer'*|*'unexpected EOF'*)
            if [[ $ATTEMPT -lt 3 ]]; then
                echo "Transient API exec transport failure; retrying read-only smoke check ($ATTEMPT/3)..." >&2
                sleep 2
                continue
            fi
            ;;
    esac
    printf '%s\n' "$ERROR" >&2
    exit "$CODE"
done
