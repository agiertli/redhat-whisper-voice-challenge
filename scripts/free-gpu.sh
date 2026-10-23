#!/usr/bin/env bash
# Stop exactly the explicitly selected InferenceService; never discover/delete others.
set -Eeuo pipefail
if [[ -n ${KUBE_CONTEXT:-} ]]; then
    oc() { command oc --context "$KUBE_CONTEXT" "$@"; }
fi
NS=${1:-my-first-model}
ISVC=${2:-llama-32-3b-instruct}
command -v oc >/dev/null || { echo 'ERROR: oc is required' >&2; exit 1; }
RESOURCE=$(oc get inferenceservice "$ISVC" -n "$NS" --ignore-not-found -o name)
if [[ -z "$RESOURCE" ]]; then
    ORPHANS=$(oc get pods -n "$NS" -l "serving.kserve.io/inferenceservice=$ISVC" -o name)
    [[ -z "$ORPHANS" ]] || { echo "ERROR: Pods remain without $NS/$ISVC; investigate manually" >&2; exit 1; }
    echo "No $NS/$ISVC InferenceService or pods; nothing to scale down."
    exit 0
fi
echo "Stopping $NS/$ISVC to release its GPU..."
# Merge works whether minReplicas was present or omitted.
oc patch inferenceservice "$ISVC" -n "$NS" --type=merge -p '{"spec":{"predictor":{"minReplicas":0}}}'
DEPLOYMENT=$(oc get deployment "${ISVC}-predictor" -n "$NS" --ignore-not-found -o name)
if [[ -n "$DEPLOYMENT" ]]; then
    oc scale "$DEPLOYMENT" -n "$NS" --replicas=0
fi
PODS=$(oc get pods -n "$NS" -l "serving.kserve.io/inferenceservice=$ISVC" -o name)
if [[ -n "$PODS" ]]; then
    oc wait --for=delete pod -l "serving.kserve.io/inferenceservice=$ISVC" -n "$NS" --timeout=180s
fi
PODS=$(oc get pods -n "$NS" -l "serving.kserve.io/inferenceservice=$ISVC" -o name)
if [[ -n "$PODS" ]]; then
    echo "ERROR: $NS/$ISVC still has pods; GPU release is not verified" >&2
    exit 1
fi
echo "Verified: no $NS/$ISVC pods remain. Whisper scheduling will verify GPU availability."
