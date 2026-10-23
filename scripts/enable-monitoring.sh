#!/usr/bin/env bash
# Shared by agent/installer and direct Helm instructions. No Python/YAML package.
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
MODE=${1:-}
case "$MODE" in ''|--check|--wait) ;; *) echo 'Usage: enable-monitoring.sh [--check|--wait]' >&2; exit 1 ;; esac
for command_name in oc helm; do command -v "$command_name" >/dev/null; done
if [[ -n ${KUBE_CONTEXT:-} ]]; then
    oc() { command oc --context "$KUBE_CONTEXT" "$@"; }
fi
WORK=$(mktemp -d)
chmod 700 "$WORK"
trap 'rm -rf -- "$WORK"' EXIT
oc get configmap cluster-monitoring-config -n openshift-monitoring --ignore-not-found -o json > "$WORK/existing.json"
EXISTS=true
if [[ ! -s "$WORK/existing.json" ]]; then
    EXISTS=false
    cat > "$WORK/existing.json" <<'JSON'
{"apiVersion":"v1","kind":"ConfigMap","metadata":{"name":"cluster-monitoring-config","namespace":"openshift-monitoring"},"data":{}}
JSON
fi
# Helm's YAML parser preserves unrelated configuration semantics. The complete
# ConfigMap (other data, labels, annotations and resourceVersion) is retained.
helm template monitoring-prerequisite "$ROOT/helm/monitoring-prerequisite" \
    --set-file "existing=$WORK/existing.json" > "$WORK/desired.yaml"
if grep -q '[^[:space:]]' "$WORK/desired.yaml"; then
    if [[ "$MODE" == --check ]]; then
        echo 'User workload monitoring will be enabled (read-only preflight).'
        exit 0
    fi
    if $EXISTS; then
        # resourceVersion gives optimistic concurrency: a concurrent edit fails
        # rather than overwriting a cluster owner's newer configuration.
        oc replace -f "$WORK/desired.yaml" >/dev/null
    else
        oc create -f "$WORK/desired.yaml" >/dev/null
    fi
    echo 'User workload monitoring enabled; unrelated monitoring configuration preserved.'
else
    echo 'User workload monitoring: already enabled.'
fi
if [[ "$MODE" == --wait ]]; then
    FOUND=false
    for ((attempt=0; attempt<60; attempt++)); do
        RESOURCE=$(oc get statefulset prometheus-user-workload -n openshift-user-workload-monitoring --ignore-not-found -o name)
        if [[ -n "$RESOURCE" ]]; then FOUND=true; break; fi
        sleep 5
    done
    $FOUND || { echo 'ERROR: User workload Prometheus was not created within 300s' >&2; exit 1; }
    oc rollout status statefulset/prometheus-user-workload -n openshift-user-workload-monitoring --timeout=300s
fi
