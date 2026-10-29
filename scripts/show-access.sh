#!/usr/bin/env bash
# Run after installation verification. Intentionally displays the admin password.
set -Eeuo pipefail
if [[ -n ${KUBE_CONTEXT:-} ]]; then
    oc() { command oc --context "$KUBE_CONTEXT" "$@"; }
fi
NS=${1:-whisper}
HOST=$(oc get route whisper-ui -n "$NS" -o jsonpath='{.spec.host}')
PASSWORD=$(oc get secret whisper-tournament-secret -n "$NS" \
    -o 'go-template={{index .data "ADMIN_TOKEN" | base64decode}}')
[[ -n "$HOST" && -n "$PASSWORD" ]] || { echo 'ERROR: Cannot retrieve installed access details' >&2; exit 1; }
printf 'Game URL:            https://%s/\n' "$HOST"
printf 'TV/Leaderboard URL:  https://%s/tv\n' "$HOST"
printf 'Admin URL:           https://%s/admin\n' "$HOST"
printf 'Architecture URL:    https://%s/architecture\n' "$HOST"
printf 'Game admin password: %s\n' "$PASSWORD"
