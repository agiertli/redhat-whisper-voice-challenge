#!/usr/bin/env bash
# Human and agent entry point. See docs/INSTALLATION.md.
set -Eeuo pipefail
CALLER_DIR=$PWD
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$ROOT"

usage() {
    cat <<'HELP'
Usage: ./deploy.sh [options]
  --free-rhdp-gpu        Stop ONLY my-first-model/llama-32-3b-instruct
  --language CODE        Required first language (or set game.requiredLanguage in --values)
  --namespace NAME       Target namespace (default: NAMESPACE or whisper)
  --values FILE          Additional Helm values (or HELM_VALUES environment variable)
  --admin-password-file FILE  Choose admin password from a private file (no trailing newline)
  --preflight            Read-only cluster/configuration checks; do not deploy
  --backup-file FILE     Recovery only: validate an existing snapshot instead of
                         downloading a fresh pre-upgrade backup
  --build                Build and push; requires IMAGE_REGISTRY and VERSION
  --skip-build           Use published image (default; no container engine needed)
  --timeout SECONDS      Deployment timeout (default: 1200; minimum: 300)
  -h, --help             Show help without contacting a cluster

Requires Bash, oc, Helm 3, Python 3, curl. OpenShift AI/GPU operators and storage must
already be configured. Optional build uses podman, or docker when unavailable.
IMAGE_REGISTRY / IMAGE_NAME / VERSION override chart image settings when set.
After successful verification, the game/admin URLs and installed admin password are printed.
HELP
}
fail() { echo "ERROR: $*" >&2; exit 1; }
NAMESPACE=${NAMESPACE:-whisper}
VALUES=${HELM_VALUES:-}
LANGUAGE=""
TIMEOUT=1200
BUILD=false
FREE_GPU=false
PREFLIGHT=false
BACKUP_FILE=""
ADMIN_PASSWORD_FILE=""
while (($#)); do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --free-rhdp-gpu) FREE_GPU=true; shift ;;
        --build) BUILD=true; shift ;;
        --skip-build) BUILD=false; shift ;;
        --preflight) PREFLIGHT=true; shift ;;
        --language|--namespace|--values|--timeout|--backup-file|--admin-password-file)
            if (($# < 2)) || [[ -z "${2:-}" || "${2:-}" == --* ]]; then
                fail "$1 requires a value"
            fi
            case "$1" in
                --language) LANGUAGE=$2 ;;
                --namespace) NAMESPACE=$2 ;;
                --values) VALUES=$2 ;;
                --timeout) TIMEOUT=$2 ;;
                --backup-file) BACKUP_FILE=$2 ;;
                --admin-password-file) ADMIN_PASSWORD_FILE=$2 ;;
            esac
            shift 2 ;;
        *) fail "Unknown option: $1 (see --help)" ;;
    esac
done
[[ "$TIMEOUT" =~ ^[0-9]+$ ]] || fail "Timeout must be 300-7200 seconds"
TIMEOUT=$((10#$TIMEOUT))
if ((TIMEOUT < 300 || TIMEOUT > 7200)); then fail "Timeout must be 300-7200 seconds"; fi
[[ "$NAMESPACE" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ && ${#NAMESPACE} -le 63 ]] || fail "Invalid namespace"
if [[ -n "$VALUES" && "$VALUES" != /* ]]; then VALUES="$CALLER_DIR/$VALUES"; fi
if [[ -n "$BACKUP_FILE" && "$BACKUP_FILE" != /* ]]; then BACKUP_FILE="$CALLER_DIR/$BACKUP_FILE"; fi
if [[ -n "$ADMIN_PASSWORD_FILE" ]]; then
    [[ "$ADMIN_PASSWORD_FILE" == /* ]] || ADMIN_PASSWORD_FILE="$CALLER_DIR/$ADMIN_PASSWORD_FILE"
    [[ -r "$ADMIN_PASSWORD_FILE" && -s "$ADMIN_PASSWORD_FILE" ]] || fail "Admin password file must be readable and non-empty"
fi
[[ -z "$LANGUAGE" || "$LANGUAGE" =~ ^[a-z]{2}$ ]] || fail "Language must be a two-letter code (cs/sk/en/de)"
if [[ -n ${IMAGE_REGISTRY:-} ]]; then
    [[ "${IMAGE_REGISTRY}/${IMAGE_NAME:-whisper-ui}" =~ ^[a-z0-9][a-z0-9./:_-]*$ ]] || fail "Invalid image repository"
fi
[[ -z "$VALUES" || -f "$VALUES" ]] || fail "Values file not found: $VALUES"
for cmd in oc helm python3 curl; do command -v "$cmd" >/dev/null || fail "Install required tool: $cmd"; done
[[ $(helm version --template '{{.Version}}') == v3.* ]] || fail "Helm 3 is required"
if $BUILD; then
    [[ -n ${IMAGE_REGISTRY:-} && -n ${VERSION:-} ]] || fail "--build requires IMAGE_REGISTRY and an explicit semver VERSION"
    if command -v podman >/dev/null; then ENGINE=podman
    elif command -v docker >/dev/null; then ENGINE=docker
    else fail "--build requires podman or docker"; fi
fi
if [[ -n ${VERSION:-} ]]; then
    [[ "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.-]+)?$ ]] || fail "VERSION must be semver, for example v2.2.1"
fi
WORK=$(mktemp -d)
chmod 700 "$WORK"
cleanup() { rm -rf -- "$WORK"; }
trap cleanup EXIT
# This file contains a generated signing key on first install. Never print it.
ARGS=(--namespace "$NAMESPACE")
[[ -z "$VALUES" ]] || ARGS+=(-f "$VALUES")
[[ -z "$ADMIN_PASSWORD_FILE" ]] || ARGS+=(--set-file "tournament.adminToken=$ADMIN_PASSWORD_FILE")
ARGS+=(--set-string "namespace=$NAMESPACE" --set "warmup.deadlineSeconds=$((TIMEOUT - 60))")
[[ -z "$LANGUAGE" ]] || ARGS+=(--set-string "game.requiredLanguage=$LANGUAGE")
[[ -z ${IMAGE_REGISTRY:-} ]] || ARGS+=(--set-string "image.repository=${IMAGE_REGISTRY}/${IMAGE_NAME:-whisper-ui}")
[[ -z ${VERSION:-} ]] || ARGS+=(--set-string "image.tag=$VERSION")
helm lint helm/whisper "${ARGS[@]}" > "$WORK/lint.log" || { cat "$WORK/lint.log"; fail "Chart validation failed"; }
helm template whisper helm/whisper "${ARGS[@]}" --show-only templates/configmap.yaml > "$WORK/config.yaml"
MODEL=$(sed -n 's/^  WHISPER_MODEL_NAME: "\([^"]*\)"$/\1/p' "$WORK/config.yaml")
REGISTRATION_MODE=$(sed -n 's/^  REGISTRATION_MODE: "\([^"]*\)"$/\1/p' "$WORK/config.yaml")
LANGUAGE=$(sed -n 's/^  REQUIRED_CHALLENGE_LANGUAGE: "\([^"]*\)"$/\1/p' "$WORK/config.yaml")
[[ -n "$MODEL" && -n "$LANGUAGE" ]] || fail "Could not resolve model/language from chart"
helm template whisper helm/whisper "${ARGS[@]}" --show-only templates/deployment.yaml > "$WORK/deployment.yaml"
IMAGE=$(sed -n 's/^        image: "\([^"]*\)"$/\1/p' "$WORK/deployment.yaml")
[[ -n "$IMAGE" ]] || fail "Could not resolve UI image"

# Pin both clients to the context inspected here, even if another terminal switches
# the workstation's default context while this deployment is waiting.
KUBE_CONTEXT=$(oc config current-context)
[[ -n "$KUBE_CONTEXT" ]] || fail "No current kube context"
export KUBE_CONTEXT
oc() { command oc --context "$KUBE_CONTEXT" "$@"; }
ARGS+=(--kube-context "$KUBE_CONTEXT")

echo "Checking current OpenShift context..."
oc whoami >/dev/null
oc whoami --show-server
[[ $(oc auth can-i '*' '*' --all-namespaces) == yes ]] || fail "Cluster-admin permissions are required"
ROUTE_API=$(oc api-resources --api-group=route.openshift.io -o name)
[[ "$ROUTE_API" == *routes.route.openshift.io* ]] || fail "OpenShift Route API is required"
for crd in inferenceservices.serving.kserve.io servingruntimes.serving.kserve.io; do
    oc get crd "$crd" -o name >/dev/null
done
oc get csv -A -o json > "$WORK/operators.json"
oc get nodes -o json > "$WORK/nodes.json"
oc get storageclasses -o json > "$WORK/storage.json"
oc get pods -A -o json > "$WORK/pods.json"
oc get pvc whisper-tournament-db -n "$NAMESPACE" --ignore-not-found -o json > "$WORK/pvc.json"
[[ -s "$WORK/pvc.json" ]] || echo '{}' > "$WORK/pvc.json"
helm template whisper helm/whisper "${ARGS[@]}" --show-only templates/pvc.yaml > "$WORK/pvc.yaml"
sed -n 's/^  storageClassName: "\([^" ]*\)"$/\1/p' "$WORK/pvc.yaml" > "$WORK/storage-class"
python3 "$ROOT/scripts/check-cluster.py" "$WORK" "$NAMESPACE" "$MODEL" "$FREE_GPU"
"$ROOT/scripts/enable-monitoring.sh" --check
# Disallow an accidental second installation using the fixed chart resource names.
INSTALLED=$(oc get deployment whisper-ui -n "$NAMESPACE" --ignore-not-found -o name)
OWNER=$(oc get deployment whisper-ui -n "$NAMESPACE" --ignore-not-found -o 'jsonpath={.metadata.annotations.meta\.helm\.sh/release-name}')
[[ -z "$OWNER" || "$OWNER" == whisper ]] || fail "whisper-ui belongs to another Helm release: $OWNER"
echo "Preflight passed: namespace=$NAMESPACE, model=$MODEL, language=$LANGUAGE, UI=$IMAGE"
if $PREFLIGHT; then
    echo "Read-only checks complete. Registry pulls, scheduling, route TLS and inference still require a live deployment."
    exit 0
fi

diagnostics() {
    local code=$?
    trap - ERR
    echo "ERROR: Deployment failed (exit $code). Collecting non-secret diagnostics..." >&2
    oc get pods,pvc,inferenceservices -n "$NAMESPACE" -o wide >&2 || true
    oc get events -n "$NAMESPACE" --sort-by=.lastTimestamp >&2 || true
    echo "See docs/INSTALLATION.md for recovery. Resources were retained; no automatic uninstall or data deletion." >&2
    exit "$code"
}
trap diagnostics ERR
if [[ -n "$INSTALLED" ]]; then
    if [[ -n "$BACKUP_FILE" ]]; then
        "$ROOT/scripts/backup.sh" --validate "$BACKUP_FILE"
        echo "Using owner-selected recovery snapshot: $BACKUP_FILE"
    else
        echo "Saving a verified off-cluster snapshot before upgrading..."
        oc get secret whisper-tournament-secret -n "$NAMESPACE" -o 'go-template={{index .data "ADMIN_TOKEN" | base64decode}}' > "$WORK/admin-token"
        BACKUP_HOST=$(oc get route whisper-ui -n "$NAMESPACE" -o jsonpath='{.spec.host}')
        ADMIN_TOKEN_FILE="$WORK/admin-token" WHISPER_URL="https://$BACKUP_HOST" \
            BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups/$NAMESPACE}" "$ROOT/scripts/backup.sh"
    fi
fi
"$ROOT/scripts/enable-monitoring.sh"
if $FREE_GPU; then "$ROOT/scripts/free-gpu.sh"; fi
# Label only detected GPU nodes; monitoring is handled by the shared helper above.
oc label nodes -l nvidia.com/gpu.present=true node-role.kubernetes.io/gpu-worker=true --overwrite
if $BUILD; then
    "$ENGINE" build --platform linux/amd64 -f Containerfile -t "$IMAGE" .
    "$ENGINE" push "$IMAGE"
fi
# Helm lookup preserves existing credentials. Do not use --reuse-values: defaults
# and explicit venue files are the source of non-secret deployment configuration.
helm upgrade --install whisper helm/whisper "${ARGS[@]}" --create-namespace --wait --timeout "${TIMEOUT}s"
oc wait --for=condition=Ready "inferenceservice/$MODEL" -n "$NAMESPACE" --timeout="${TIMEOUT}s"
oc rollout status deployment/whisper-ui -n "$NAMESPACE" --timeout="${TIMEOUT}s"
"$ROOT/scripts/enable-monitoring.sh" --wait
"$ROOT/scripts/verify-install.sh" "$NAMESPACE" "$LANGUAGE" "$REGISTRATION_MODE"
echo "Deployment and internal smoke checks passed."
"$ROOT/scripts/show-access.sh" "$NAMESPACE"
echo "Next: verify browser TLS, microphone, registration, a complete game, /tv and /admin."
echo "Backup instructions: docs/INSTALLATION.md"
