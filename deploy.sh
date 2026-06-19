#!/bin/bash
#
# Red Hat AI Voice Challenge - Deploy Script
#
# Builds the container image, pushes it to a registry, and deploys via Helm.
# Handles all cluster prerequisites automatically (node labeling, monitoring).
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
            head -20 "$0" | tail -17
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

# --- Cluster prerequisites ---
echo ""
echo "Ensuring cluster prerequisites..."

# Label GPU nodes: the InferenceService nodeSelector requires gpu-worker label.
# On SNO or clusters where GPU nodes lack this label, add it to any node with an NVIDIA GPU.
GPU_NODES=$($KUBE_CLI get nodes -l nvidia.com/gpu.present=true -o name 2>/dev/null || true)
if [ -n "$GPU_NODES" ]; then
    for node in $GPU_NODES; do
        if ! $KUBE_CLI get "$node" --show-labels 2>/dev/null | grep -q "node-role.kubernetes.io/gpu-worker"; then
            echo "  Labeling $node with gpu-worker role..."
            $KUBE_CLI label "$node" node-role.kubernetes.io/gpu-worker=true --overwrite
        fi
    done
    echo "  GPU node labels: OK"
else
    echo "  WARNING: No nodes with nvidia.com/gpu.present=true found."
    echo "  The InferenceService may fail to schedule. Ensure GPU nodes are available."
fi

# Enable user workload monitoring for Prometheus metrics persistence
if ! $KUBE_CLI get configmap cluster-monitoring-config -n openshift-monitoring &>/dev/null 2>&1; then
    echo "  Enabling user workload monitoring..."
    $KUBE_CLI apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-monitoring-config
  namespace: openshift-monitoring
data:
  config.yaml: |
    enableUserWorkload: true
EOF
else
    echo "  User workload monitoring: already configured"
fi

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

# --- Wait for InferenceService ---
echo ""
echo "Waiting for Whisper InferenceService to become ready (up to 10 minutes)..."
echo "  (vLLM pulls model weights on first boot — this takes a few minutes)"
if $KUBE_CLI wait --for=condition=Ready inferenceservice/whisper -n "${NAMESPACE}" --timeout=600s; then
    echo "  InferenceService: Ready"
else
    echo "  WARNING: InferenceService did not become ready within 10 minutes."
    echo "  Check logs: $KUBE_CLI logs -n ${NAMESPACE} deployment/whisper-predictor -c kserve-container"
    exit 1
fi

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
