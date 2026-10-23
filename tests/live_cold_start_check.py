"""Run inside a UI pod to check three fresh SQLite boots with four workers.

Uses a temporary DB and port 18081; never uses the running app's database/port.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import time
import urllib.request

for attempt in range(3):
    with tempfile.TemporaryDirectory(prefix='whisper-cold-start-') as directory:
        environment = dict(os.environ, DB_PATH=str(Path(directory) / 'test.db'))
        assert '--preload' in environment.get('GUNICORN_CMD_ARGS', '')
        with open(Path(directory) / 'startup.log', 'w+') as log:
            process = subprocess.Popen(['gunicorn', '--bind', '127.0.0.1:18081', '--workers', '4',
                                        'app_streaming:app'], env=environment, stdout=log, stderr=log)
            try:
                for _ in range(60):
                    assert process.poll() is None, 'Gunicorn failed to boot'
                    try:
                        with urllib.request.urlopen('http://127.0.0.1:18081/api/leaderboard', timeout=1) as response:
                            assert response.status == 200
                        break
                    except OSError:
                        time.sleep(0.25)
                else:
                    raise RuntimeError('Cold boot did not become ready')
                time.sleep(0.5)
            finally:
                process.terminate()
                process.wait(timeout=10)
            log.seek(0)
            text = log.read()
            assert text.count('Tournament database initialized') == 1, text
            assert text.count('Booting worker') == 4, text
            assert 'database is locked' not in text, text
print('PASS: three fresh SQLite databases booted with four workers, one initialization each, no lock errors')
