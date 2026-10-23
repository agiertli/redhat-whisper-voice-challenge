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
printf 'Game URL: https://%s/\nAdmin URL: https://%s/admin\nAdmin password: %s\n' "$HOST" "$HOST" "$PASSWORD"
