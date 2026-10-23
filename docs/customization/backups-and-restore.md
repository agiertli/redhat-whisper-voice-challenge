# Run conference backups and rehearse recovery

Run one downloader on one external laptop. Copy only
[scripts/backup.sh](../../scripts/backup.sh) and the protected admin-token file
obtained using the [admin password guide](admin-password.md). The script requires
Bash 3.2+, curl and standard macOS/Linux utilities; no oc, Helm, Python, jq, SQLite
CLI, container engine or repository checkout is needed on that laptop.

## Start and verify

Use the actual trusted HTTPS game URL:

```bash
WHISPER_URL=https://YOUR-GAME-HOST ADMIN_TOKEN_FILE=./admin-token \
  BACKUP_DIR=./backups ./backup.sh

WHISPER_URL=https://YOUR-GAME-HOST ADMIN_TOKEN_FILE=./admin-token \
  BACKUP_DIR=./backups ./backup.sh --loop
```

The first command verifies one download; the second repeats it every five minutes.
The default retention is 288 successfully downloaded files (roughly one day at
that interval). Optional `INTERVAL` is in seconds; optional `KEEP_BACKUPS` is a
count of successful snapshots. Leave the interval at 300 unless the owner chooses
another recovery point. Keep the terminal running and the laptop awake. Ctrl+C
stops the loop. There should be only one loop, not a new process every five minutes.

The terminal reports successful snapshots and failed attempts. Check the newest
snapshot time during the event. TLS/HTTP/header/length failures do not prune older
backups. Do not bypass certificate validation. Update the local token file if the
admin password changes, then restart the loop to load it.

The script checks SQLite format and page completeness. Full integrity and actual
recoverability require a restore rehearsal. Loss since the last successful
snapshot remains possible; a five-minute loop does not mean zero data loss.

## Rehearse safely before the event

On the deployment workstation with authenticated oc, use a real downloaded snapshot:

```bash
oc exec -i deployment/whisper-ui -n whisper -- python3 -c \
  "$(cat tests/live_restore_check.py)" < /safe/path/tournament-snapshot.db
```

This application-level drill creates a separate temporary database and tests the
actual restore handler, counts, scores and SQLite integrity without replacing the
running tournament database. A complete cluster-loss drill additionally requires
recreating the installation/PVC and restoring on that disposable environment.
The player signing key is not in a database snapshot; preserve it separately if
existing player tokens must survive cluster loss.

## Upgrades or an incident

Pause the laptop loop during planned upgrades so the installer can take its fresh
pre-upgrade snapshot without another downloader. Resume the loop afterwards.

For an actual incident, stop admitting players, preserve the current database/PVC
and backups, and select the correct snapshot. The `/admin` restore operation
**replaces the tournament database**: use it only for deliberate recovery, then
verify players, games and scores before reopening. Do not rehearse against live
conference results or delete the PVC as a shortcut.

The exact upgrade/recovery contract and `--backup-file` behavior are in
[the operations runbook](../INSTALLATION.md#upgrades-and-recovery). That flag only
validates an owner-selected existing snapshot when a fresh download is unavailable;
it does not restore it automatically.
