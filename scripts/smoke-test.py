"""Runs inside the UI pod. No dependencies beyond the Python standard library."""
import json
import sys
import urllib.request
import uuid

base = 'http://127.0.0.1:8080'
required = sys.argv[1]
with urllib.request.urlopen(base + '/', timeout=15) as response:
    page = response.read().decode()
if "const REQUIRED_LANGUAGE = '" + required + "';" not in page:
    sys.exit('ERROR: Running UI has the wrong required language; check rollout/configuration.')
for path in ('/register', '/tv', '/admin'):
    with urllib.request.urlopen(base + path, timeout=15) as response:
        if response.status != 200:
            sys.exit('ERROR: Page unavailable: ' + path)
with urllib.request.urlopen(base + '/api/leaderboard', timeout=15) as response:
    if not isinstance(json.load(response).get('leaderboard'), list):
        sys.exit('ERROR: Tournament database/leaderboard check failed')
audio = sys.stdin.buffer.read()
if not audio.startswith(b'RIFF'):
    sys.exit('ERROR: Missing WAV smoke-test fixture')
boundary = uuid.uuid4().hex.encode()
body = b'--' + boundary + b'\r\nContent-Disposition: form-data; name="audio"; filename="test-en.wav"\r\nContent-Type: audio/wav\r\n\r\n' + audio
body += b'\r\n--' + boundary + b'\r\nContent-Disposition: form-data; name="language"\r\n\r\nen\r\n--' + boundary + b'--\r\n'
request = urllib.request.Request(base + '/transcribe-stream', data=body)
request.add_header('Content-Type', 'multipart/form-data; boundary=' + boundary.decode())
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
print('PASS: configured language, UI pages, tournament database and real-audio UI -> vLLM transcription.')
print('Transcript:', text.strip())
