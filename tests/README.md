# Local verification

No GitHub Actions pipeline is required. Run from the repository root:

```bash
python3 -m venv /tmp/whisper-tests
/tmp/whisper-tests/bin/pip install -r tests/requirements.txt
/tmp/whisper-tests/bin/python -m unittest discover -s tests -v
helm lint helm/whisper --set game.requiredLanguage=en
bash -n deploy.sh scripts/*.sh scripts/reporting/*.sh tests/audio/*.sh
```

The suite exercises chart rendering, installer safeguards, backups, real Flask
registration routes and isolated SQLite databases. Helm 3 must be available.
Tests never connect to a cluster and do not prove browser microphone or GPU
inference behavior. Follow the live acceptance checklist in
[the runbook](../docs/INSTALLATION.md) before handing over a deployment.

`audio/test-en.wav` is the real-audio smoke fixture used by
`scripts/verify-install.sh`. The remaining audio and `audio/whisper.sh` are an
optional manual test collection, not application assets or Python dependencies.
`live_restore_check.py` is an explicit isolated restore drill against a temporary
database in a running UI pod; it is not executed by unittest discovery.
