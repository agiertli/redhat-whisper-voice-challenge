#!/usr/bin/env bash
# Tests the deployed UI -> vLLM path without creating synthetic tournament players.
set -Eeuo pipefail
if [[ -n ${KUBE_CONTEXT:-} ]]; then
    oc() { command oc --context "$KUBE_CONTEXT" "$@"; }
fi
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
NS=${1:-whisper}
LANGUAGE=${2:-en}
oc exec -i deployment/whisper-ui -n "$NS" -- python3 -c "$(cat "$ROOT/scripts/smoke-test.py")" "$LANGUAGE" < "$ROOT/wav-tests/test-en.wav"
