# Whisper Voice Challenge: instructions for every agent

Read [docs/INSTALLATION.md](docs/INSTALLATION.md) before installing or upgrading.
It is the shared operations runbook. Agents normally execute `./deploy.sh` using
[docs/AGENT-INSTALLATION.md](docs/AGENT-INSTALLATION.md). The separately documented
[direct Helm path](docs/HELM-INSTALLATION.md) is for human/scripted installation or
an explicit request to use Helm directly. Both use the same chart. Do not invent
a third deployment procedure. The consolidation candidate is on `codex/consolidate-modes`. Keep accepted
`main` and `tournament-mode` unchanged until the documented merge gates pass.

## Installation contract

- Target environment: RHDP OpenShift AI 3, SNO, NVIDIA GPU. Broader compatibility
  is unverified. Discover the current logged-in cluster with `oc`; do not reuse
  credentials/hosts from an earlier conversation or `now.env`.
- The technical owner MUST select the first challenge language. If the request
  gives a country but no language, confirm the language choice. Never infer it
  from laptop locale or silently fall back to Slovak/English. Examples: `cs` for
  Czech, `sk` for Slovak, `de` for German, `en` for English.
- Tournament is enabled by default (`tournament.enabled: true`). False opens
  anonymous standalone play; preserve PVC/Secret/data in both modes. See
  `docs/customization/game-mode.md`. Registration settings apply only when enabled.
- Registration is configurable via `registration.mode`: `full` (default) or
  `username` (one form/field to register or resume, no name/email collection).
  Preserve the owner's mode in the values file across upgrades. This uses the
  same application/chart/image in both registration modes.
- Accept an admin password directly in the owner prompt or from a private file.
  For a literal value, create a mode-600 temporary file, use --admin-password-file,
  then remove that file. Never put it in command arguments or versioned values.
- Normalize language names and obvious typos to supported codes (German/Germand
  -> de); clarify ambiguous input. The script/Helm still require the language code.
- Ask for missing owner choices early; continue read-only discovery meanwhile.
- On the usual RHDP SNO, use `--free-rhdp-gpu` only when stopping the bundled
  `my-first-model/llama-32-3b-instruct` is authorized. Never stop unrelated models.
- Monitoring is REQUIRED on every installation. Use `scripts/enable-monitoring.sh`
  to enable user workload monitoring while preserving existing settings, and
  `--wait` to verify readiness. This standard prerequisite is authorized: do not
  ask the owner whether monitoring should be enabled. Verify DCGM GPU gauges and
  persistent AI counters before declaring the installation complete.
- Run read-only `--preflight`, then the same command without `--preflight`.
- Preserve tournament data and credentials. Upgrades take a verified external
  backup first. Never uninstall, delete a PVC, reset scores, or rotate keys as a
  troubleshooting shortcut. Recovery with `--backup-file` is an explicit owner
  decision, not an automatic fallback.
- Reuse the same venue values file and explicit language on every upgrade.
- Do not claim completion based only on Ready pods: internal real-audio smoke
  checks must pass; browser TLS, microphone and a complete game need verification.
- After successful verification, report the game URL, admin URL and installed admin
  password from `scripts/show-access.sh`. The owner explicitly requests this
  credential in the installation handoff. Never print the signing key.
- An owner can choose the admin password using `--admin-password-file FILE`;
  direct Helm uses `--set-file tournament.adminToken=FILE`. Omit on ordinary
  upgrades to preserve the existing password; never impose a shared default.
- Start the standalone backup loop on an external laptop before admitting players.
  Verify the first snapshot and rehearse restore on a disposable installation.
- Record actual versions and test evidence; distinguish local tests from cluster
  tests. Do not describe a custom demo as Red Hat supported without verification.

## Repository map and development

- `src/app_streaming.py`: Flask application, streaming proxy, tournament API/SQLite.
- `src/templates/`: game, registration, TV and admin pages.
- `src/static/`: runtime logos and the interactive architecture page.
- `helm/whisper/`: chart, runtime, modelcar, RBAC, PVC and env configuration.
- `helm/whisper/challenges.json`: phrases; `values.yaml`: language pools/metadata.
- `scripts/backup.sh`: standalone Bash conference backup; no Python/oc dependency.
- `tests/`: offline regression checks; development requirements and commands in `tests/README.md`.
- `tests/audio/test-en.wav`: real-audio installer smoke fixture; keep it in deployment checkouts.
- `scripts/reporting/`: optional statistics utilities, not application runtime.

Keep configuration in env vars/Helm, logs on stdout, explicit pinned dependencies,
and semantic image tags (never `latest`). SQLite uses one UI replica and a PVC;
do not scale replicas as an HA solution. Config changes must roll the UI. Existing
Secret values must survive ordinary upgrades. Keep secrets, backups and local
`now.env` out of Git and image build contexts. If maintaining `now.env`, use the
current cluster's information. Only the requested admin password handoff may
include a credential in terminal/chat output; keep other diagnostics secret-free.
