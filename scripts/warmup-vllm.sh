#!/usr/bin/env bash
# Manual repeat of the chart's warmup. Installer already runs the Helm hook.
set -Eeuo pipefail
if [[ -n ${KUBE_CONTEXT:-} ]]; then
    oc() { command oc --context "$KUBE_CONTEXT" "$@"; }
fi
NAMESPACE=${1:-whisper}
ISVC=${2:-whisper}
URL="http://${ISVC}-metrics.${NAMESPACE}.svc.cluster.local:8080/v1/audio/transcriptions"
oc exec -i deployment/whisper-ui -n "$NAMESPACE" -- python3 - "$URL" "$ISVC" <<'PY'
import json
import struct
import sys
import urllib.request

sample_rate = 16000
data = b'\x00\x00' * sample_rate
wav = struct.pack('<4sI4s4sIHHIIHH4sI', b'RIFF', 36 + len(data), b'WAVE',
                  b'fmt ', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
                  b'data', len(data)) + data
boundary = b'whisper-warmup'
body = b'--' + boundary + b'\r\nContent-Disposition: form-data; name="file"; filename="warmup.wav"\r\nContent-Type: audio/wav\r\n\r\n' + wav
body += b'\r\n--' + boundary + b'\r\nContent-Disposition: form-data; name="model"\r\n\r\n' + sys.argv[2].encode() + b'\r\n--' + boundary + b'--\r\n'
request = urllib.request.Request(sys.argv[1], data=body)
request.add_header('Content-Type', 'multipart/form-data; boundary=' + boundary.decode())
try:
    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.load(response)
    if not isinstance(result.get('text'), str):
        raise ValueError('Transcription response has no text field')
except Exception as error:
    sys.exit('ERROR: Warmup failed: ' + str(error))
print('Warmup request completed. Run scripts/verify-install.sh for a real-audio smoke test.')
PY
