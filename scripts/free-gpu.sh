#!/bin/bash
# Scales down the default RHOAI 3.x llama-32-3b-instruct InferenceService
# to free the GPU for Whisper. Safe to run multiple times.

NS="${1:-my-first-model}"
ISVC="${2:-llama-32-3b-instruct}"

echo "Scaling down $ISVC in namespace $NS..."

oc patch inferenceservice "$ISVC" -n "$NS" \
  --type='json' \
  -p='[{"op":"replace","path":"/spec/predictor/minReplicas","value":0}]' 2>/dev/null

oc scale deployment "${ISVC}-predictor" -n "$NS" --replicas=0 2>/dev/null

echo "Waiting for pods to terminate..."
oc wait --for=delete pod -l "serving.kserve.io/inferenceservice=${ISVC}" \
  -n "$NS" --timeout=120s 2>/dev/null || true

REMAINING=$(oc get pods -n "$NS" -l "serving.kserve.io/inferenceservice=${ISVC}" --no-headers 2>/dev/null | wc -l | tr -d ' ')
if [ "$REMAINING" -eq 0 ]; then
  echo "GPU freed. No $ISVC pods running."
else
  echo "Warning: $REMAINING pod(s) still running in $NS."
fi
