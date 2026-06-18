#!/bin/bash
#
# Red Hat AI Voice Challenge - Deploy Script
#
# Builds the container image, pushes it to a registry, and deploys via Helm.
#
# Configuration via environment variables:
#   IMAGE_REGISTRY  - Container registry (default: quay.io/agiertli)
#   IMAGE_NAME      - Image name (default: whisper-ui)
#   VERSION         - Image tag, semver (default: reads from helm/whisper/values.yaml)
#   NAMESPACE       - Target namespace (default: whisper)
#   HELM_VALUES     - Extra Helm values file (optional)
#
# Usage:
#   ./deploy.sh                    # Build, push, deploy
#   ./deploy.sh --help             # Show this help
#   ./deploy.sh --skip-build       # Deploy without rebuilding the image
#

set -euo pipefail

# --- Configuration ---
IMAGE_REGISTRY="${IMAGE_REGISTRY:-quay.io/agiertli}"
IMAGE_NAME="${IMAGE_NAME:-whisper-ui}"
NAMESPACE="${NAMESPACE:-whisper}"
VERSION="${VERSION:-$(grep 'tag:' helm/whisper/values.yaml | head -1 | awk '{print $2}' | tr -d '"')}"
IMAGE="${IMAGE_REGISTRY}/${IMAGE_NAME}:${VERSION}"
SKIP_BUILD=false

# --- Parse arguments ---
for arg in "$@"; do
    case $arg in
        --help|-h)
            head -17 "$0" | tail -14
            echo ""
            echo "Environment variables:"
            echo "  IMAGE_REGISTRY  Container registry (current: ${IMAGE_REGISTRY})"
            echo "  IMAGE_NAME      Image name (current: ${IMAGE_NAME})"
            echo "  VERSION         Image tag, semver (current: ${VERSION})"
            echo "  NAMESPACE       Target namespace (current: ${NAMESPACE})"
            echo "  HELM_VALUES     Extra Helm values file (current: ${HELM_VALUES:-not set})"
            exit 0
            ;;
        --skip-build)
            SKIP_BUILD=true
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Run '$0 --help' for usage."
            exit 1
            ;;
    esac
done

# --- Prerequisite checks ---
echo "Checking prerequisites..."

missing=()
for cmd in helm podman; do
    if ! command -v "$cmd" &>/dev/null; then
        missing+=("$cmd")
    fi
done

# Accept either oc or kubectl
if command -v oc &>/dev/null; then
    KUBE_CLI="oc"
elif command -v kubectl &>/dev/null; then
    KUBE_CLI="kubectl"
else
    missing+=("oc or kubectl")
fi

if [ ${#missing[@]} -gt 0 ]; then
    echo "ERROR: Missing required tools: ${missing[*]}"
    echo "Install them and try again."
    exit 1
fi

# Check cluster login
if ! $KUBE_CLI whoami &>/dev/null 2>&1 && ! $KUBE_CLI cluster-info &>/dev/null 2>&1; then
    echo "ERROR: Not logged into a cluster. Run '$KUBE_CLI login' first."
    exit 1
fi

echo "  Tools: OK"
echo "  Cluster: OK"

# --- Build & Push ---
if [ "$SKIP_BUILD" = false ]; then
    echo ""
    echo "Building container image: ${IMAGE}"
    podman build --platform linux/amd64 -f Containerfile -t "${IMAGE}" .

    echo ""
    echo "Pushing to registry..."
    podman push "${IMAGE}"
    echo "  Pushed: ${IMAGE}"
else
    echo ""
    echo "Skipping build (--skip-build). Using image: ${IMAGE}"
fi

# --- Deploy via Helm ---
echo ""
echo "Deploying via Helm to namespace '${NAMESPACE}'..."

HELM_ARGS=(
    upgrade --install whisper helm/whisper
    --namespace "${NAMESPACE}"
    --create-namespace
    --wait --timeout 5m
    --set "image.repository=${IMAGE_REGISTRY}/${IMAGE_NAME}"
    --set "image.tag=${VERSION}"
)

if [ -n "${HELM_VALUES:-}" ]; then
    HELM_ARGS+=(--values "${HELM_VALUES}")
fi

helm "${HELM_ARGS[@]}"

# --- Print access info ---
echo ""
echo "========================================="
echo "Deployment complete!"
echo "========================================="
echo ""
echo "  Version:   ${VERSION}"
echo "  Image:     ${IMAGE}"
echo "  Namespace: ${NAMESPACE}"

if command -v oc &>/dev/null; then
    ROUTE_HOST=$($KUBE_CLI get route whisper-ui -n "${NAMESPACE}" -o jsonpath='{.spec.host}' 2>/dev/null || echo "")
    if [ -n "$ROUTE_HOST" ]; then
        echo ""
        echo "  URL: https://${ROUTE_HOST}/"
    fi
fi

echo ""
echo "Useful commands:"
echo "  $KUBE_CLI logs -f deployment/whisper-ui -n ${NAMESPACE}"
echo "  $KUBE_CLI get pods -n ${NAMESPACE}"
echo "  helm rollback whisper -n ${NAMESPACE}"
echo "========================================="
