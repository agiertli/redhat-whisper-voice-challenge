"""Run INSIDE the deployed UI pod, with a snapshot on stdin.

oc exec -i deployment/whisper-ui -n whisper -- python3 -c \
  "$(cat tests/live_restore_check.py)" < /path/to/snapshot.db

Restores only into a new temporary database in this separate Python process.
The running server's database, players, scores and configuration are untouched.
"""
from contextlib import closing
import io
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

snapshot = sys.stdin.buffer.read()
with tempfile.TemporaryDirectory(prefix='whisper-restore-check-') as directory:
    original = Path(directory) / 'snapshot.db'
    original.write_bytes(snapshot)
    target = Path(directory) / 'restored.db'
    os.environ['DB_PATH'] = str(target)
    import app_streaming as application

    assert application.DB_PATH == str(target)
    assert target.parent == original.parent
    with closing(sqlite3.connect(original)) as database:
        assert database.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        expected = {table: database.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                    for table in ('players', 'games', 'attempts')}
        scores = database.execute('SELECT total_score FROM games WHERE completed_at IS NOT NULL ORDER BY id').fetchall()
    with application.app.test_client() as client:
        response = client.post('/api/admin/restore',
                               data={'file': (io.BytesIO(snapshot), 'snapshot.db')},
                               headers={'Authorization': 'Bearer ' + os.environ['ADMIN_TOKEN']})
        assert response.status_code == 200, response.status_code
        response.close()
        response = client.get('/api/leaderboard')
        assert response.status_code == 200
        response.close()
    with closing(sqlite3.connect(target)) as database:
        assert database.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
        actual = {table: database.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                  for table in expected}
        assert actual == expected, (actual, expected)
        assert database.execute('SELECT total_score FROM games WHERE completed_at IS NOT NULL ORDER BY id').fetchall() == scores
    print('PASS: published restore endpoint restored an isolated temporary database; integrity, counts and scores match:', actual)
