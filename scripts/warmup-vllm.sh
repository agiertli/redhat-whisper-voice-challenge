#!/bin/bash
# Sends a dummy audio request to Whisper vLLM to trigger lazy initialization.
# Run after InferenceService is Ready, before real users hit the app.
# Eliminates the ~20s gibberish response on first request.

set -euo pipefail

NAMESPACE="${1:-whisper}"
ISVC="${2:-whisper}"

INTERNAL_URL="http://${ISVC}-predictor.${NAMESPACE}.svc.cluster.local/v1/audio/transcriptions"
ROUTE_URL=$(oc get route "$ISVC" -n "$NAMESPACE" -o jsonpath='{.spec.host}' 2>/dev/null || true)

# Generate a 1-second silent WAV file inside the UI pod (has python)
UI_POD=$(oc get pods -n "$NAMESPACE" -l app=whisper-ui -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$UI_POD" ]; then
  echo "Error: No whisper-ui pod found in namespace $NAMESPACE"
  exit 1
fi

echo "Generating silent WAV and sending warmup request via pod $UI_POD..."

oc exec "$UI_POD" -n "$NAMESPACE" -- python3 -c "
import struct, io, urllib.request, json

# Generate 1-second 16kHz mono silent WAV
sample_rate = 16000
num_samples = sample_rate
data = b'\x00\x00' * num_samples
header = struct.pack('<4sI4s4sIHHIIHH4sI',
    b'RIFF', 36 + len(data), b'WAVE',
    b'fmt ', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
    b'data', len(data))
wav = header + data

# Send as multipart form to vLLM
boundary = b'----warmup-boundary'
body = b'--' + boundary + b'\r\n'
body += b'Content-Disposition: form-data; name=\"file\"; filename=\"warmup.wav\"\r\n'
body += b'Content-Type: audio/wav\r\n\r\n'
body += wav + b'\r\n'
body += b'--' + boundary + b'\r\n'
body += b'Content-Disposition: form-data; name=\"model\"\r\n\r\n'
body += b'whisper\r\n'
body += b'--' + boundary + b'--\r\n'

url = '${INTERNAL_URL}'
req = urllib.request.Request(url, data=body, method='POST')
req.add_header('Content-Type', 'multipart/form-data; boundary=' + boundary.decode())

try:
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    print(f'Warmup OK: {json.dumps(result)}')
except Exception as e:
    print(f'Warmup request sent (response: {e})')
    print('First inference path is now initialized.')
"

echo ""
echo "Warmup complete. First real request should now respond in <3s."
