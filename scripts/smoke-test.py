"""Runs inside the UI pod. No dependencies beyond the Python standard library."""
import json
import sys
import time
import urllib.request
import urllib.error
import uuid

base = 'http://127.0.0.1:8080'
required = sys.argv[1]
with urllib.request.urlopen(base + '/', timeout=15) as response:
    page = response.read().decode()
if "const REQUIRED_LANGUAGE = '" + required + "';" not in page:
    sys.exit('ERROR: Running UI has the wrong required language; check rollout/configuration.')
enabled = len(sys.argv) < 4 or sys.argv[3] != 'false'
if len(sys.argv) > 3 and sys.argv[3]:
    if 'const TOURNAMENT_ENABLED = ' + str(enabled).lower() + ';' not in page:
        sys.exit('ERROR: Running UI has the wrong tournament mode; check image/configuration.')
if len(sys.argv) > 2 and sys.argv[2]:
    mode = sys.argv[2]
    if 'const REGISTRATION_MODE = ' + json.dumps(mode) + ';' not in page:
        sys.exit('ERROR: Running UI has the wrong registration mode; check image/configuration.')
    if enabled and mode == 'username' and ('id="regUsername"' not in page or 'id="regEmail"' in page):
        sys.exit('ERROR: Username-only registration form does not match configuration.')
for path in ('/register', '/admin') + (('/tv',) if enabled else ()):
    with urllib.request.urlopen(base + path, timeout=15) as response:
        if response.status != 200:
            sys.exit('ERROR: Page unavailable: ' + path)
if enabled:
    with urllib.request.urlopen(base + '/api/leaderboard', timeout=15) as response:
        if not isinstance(json.load(response).get('leaderboard'), list):
            sys.exit('ERROR: Tournament database/leaderboard check failed')
else:
    if '<form ' in page:
        sys.exit('ERROR: Standalone mode exposes registration')
    for path in ('/tv', '/api/leaderboard'):
        try:
            urllib.request.urlopen(base + path, timeout=15)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                error.close()
                continue
        sys.exit('ERROR: Standalone mode exposes tournament surface: ' + path)
audio = sys.stdin.buffer.read()
if not audio.startswith(b'RIFF'):
    sys.exit('ERROR: Missing WAV smoke-test fixture')
boundary = uuid.uuid4().hex.encode()
body = b'--' + boundary + b'\r\nContent-Disposition: form-data; name="audio"; filename="test-en.wav"\r\nContent-Type: audio/wav\r\n\r\n' + audio
body += b'\r\n--' + boundary + b'\r\nContent-Disposition: form-data; name="language"\r\n\r\nen\r\n--' + boundary + b'--\r\n'
request = urllib.request.Request(base + '/transcribe-stream', data=body)
request.add_header('Content-Type', 'multipart/form-data; boundary=' + boundary.decode())
def transcribe():
    with urllib.request.urlopen(request, timeout=150) as response:
        text = ''
        done = False
        for line in response:
            if not line.startswith(b'data: '):
                continue
            event = json.loads(line[6:])
            if event.get('error'):
                sys.exit('ERROR: Transcription returned an error')
            text += event.get('text', '')
            done = done or event.get('done', False)
    if not done or not text.strip():
        sys.exit('ERROR: UI -> vLLM transcription was empty or incomplete')
    return text.strip()

text = transcribe()
print('PASS: configured language, UI pages, selected game mode and real-audio UI -> vLLM transcription.')
print('Transcript:', text.strip())

# Monitoring is required. Prometheus scrape and per-worker UI caches need time
# after the first real request, so allow a bounded convergence window.
deadline = time.monotonic() + 120
monitoring_attempts = 0
while True:
    with urllib.request.urlopen(base + '/metrics', timeout=15) as response:
        metrics = json.load(response)
    if ((metrics.get('vram_used') or 0) > 0
            and (metrics.get('temperature') or 0) > 0
            and (metrics.get('requests_processed') or 0) > 0
            and (metrics.get('vllm_generation_tokens') or 0) > 0):
        print('PASS: DCGM GPU gauges and persistent AI request/token counters:',
              metrics['requests_processed'], 'requests,', metrics['vllm_generation_tokens'], 'tokens')
        break
    if time.monotonic() >= deadline:
        sys.exit('ERROR: Required GPU/AI monitoring did not become usable within 120s; inspect DCGM, user workload Prometheus, ServiceMonitor and Thanos access')
    time.sleep(5)
    monitoring_attempts += 1
    if monitoring_attempts % 3 == 0:
        # increase() needs a sample before a request. On a fresh Prometheus,
        # the first fixture can precede the first scrape; generate a later event.
        transcribe()
