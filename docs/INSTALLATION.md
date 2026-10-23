# Install and operate the tournament game

This is the canonical runbook for technical owners and AI agents. No prior chat
history, Anton's workstation, registry push permission, or `now.env` is needed for
the published-image installation. Agent instructions live in `AGENTS.md`;
`CLAUDE.md` points to the same instructions. Choose the [agent procedure](AGENT-INSTALLATION.md), which uses the installer,
or the [traditional Helm procedure](HELM-INSTALLATION.md), which invokes the same
chart directly. This page covers their shared configuration and operations. Common owner tasks
have dedicated guides in the [customization index](CUSTOMIZATION.md).

## Target environment and validation status

The initial target is **RHDP "RHOAI on OCP on AWS with NVIDIA GPUs", OpenShift AI 3,
SNO, NVIDIA L4**, ordered at https://demo.redhat.com. Enable Open Environment when
ordering if additional GPU capacity may be needed. This is a custom conference
demo; a working deployment is not certification of a Red Hat support matrix.
Other operator versions, vanilla Kubernetes, GPU sharing/MIG, disconnected clusters,
and multiple simultaneous game installations in one namespace are outside this
installer's current scope. Operator installation and cloud GPU provisioning are
prerequisites, not work performed by the installer.

Current integration candidate: `2.0.0-rc.6`, using UI `v2.12.0-rc.2` with a
default-enabled tournament toggle, anonymous standalone play and reliable save retries.
This candidate is on `codex/consolidate-modes`; it is not yet the accepted main release. See the
[cleanup verification](validation/CLEANUP-2026-10-23.md) and the
[architecture fix verification](validation/ARCHITECTURE-2026-10-23.md).
The [username-mode acceptance report](validation/USERNAME-2026-10-23.md) records
the earlier `v2.11.0` version; the report below records the `v2.10.0` live baseline.
The installation changes require explicit language selection. Live results and
remaining checks are recorded in [the RHDP validation report](validation/RHDP-2026-10-23.md).
Choose a published image matching the feature: username-only registration requires
`v2.11.0` or newer. Configuration changes after that require no rebuild.
Offline regression tests validate rendering and error handling. Live RHDP
acceptance must separately verify image pulls, KServe behavior, model quality,
route TLS, storage permissions, upgrades, and backup/restore. Do not equate passing
local tests with verified cluster compatibility.

Local verification on 2026-10-23: **84 offline regression tests passed**, Helm lint
passed, and ShellCheck 0.10.0 passed for the installer and all shell helpers.
Test host: macOS, Bash 3.2.57, Helm 3.15.4, Python 3.14.2. See
[local test instructions](../tests/README.md). No GitHub Actions workflow is
required. The live acceptance checklist below is supplemented by dated validation
reports.

## Owner decisions and prerequisites

Before deployment, decide:

1. **First challenge language.** Czechia usually uses `cs`, Slovakia `sk`, Austria
   `de`; `en` is English. The owner chooses explicitly, regardless of country or
   laptop locale. Later rounds remain multilingual according to difficulty pools.
2. Destination namespace (default `whisper`).
3. Whether stopping RHDP's bundled Llama is authorized. On SNO it normally owns
   the only GPU. The opt-in flag affects only
   `my-first-model/llama-32-3b-instruct`, never arbitrary GPU workloads.
4. Who operates the off-cluster backup laptop and holds the admin credential.
5. Tournament mode: enabled by default; false selects [anonymous standalone play](customization/game-mode.md).
6. Registration mode: `full` (default) or `username`, when tournament is enabled. See below.

No conference name is required. Keep the default application branding;
`conference.name` remains an optional customization for the game and TV headings.

Installer workstation: Bash, `oc` logged in as cluster-admin, Helm **3**, curl, Python
**3.9+** (standard library only). No pip packages or container engine are needed
unless building a new UI image. Use `./deploy.sh --help` to inspect options without
contacting a cluster. The script works from any current working directory and pins oc/Helm to the
context it inspects, so another terminal switching contexts cannot redirect it.

Cluster: OpenShift AI/KServe and GPU Operator configured and healthy, a Ready
schedulable node with an allocatable NVIDIA GPU, enough CPU/RAM for the configured
model (default requests 2 CPU and 24Gi **system RAM**, plus 1 GPU), and a working
StorageClass for the tournament PVC. The tested hardware baseline is L4 with 24GB
VRAM; do not extrapolate the old 12GB claim to arbitrary models.

The cluster must pull both `registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.2.4` and
`registry.redhat.io/rhai/modelcar-openai-whisper-large-v3:3.0`. Cluster-admin access
is not registry entitlement. RHDP normally supplies credentials; verify the actual
pull if pods report ImagePullBackOff. A registry login on your laptop does not
configure cluster pulls. The published UI must also be reachable from the cluster.

## Fresh installation

```bash
git clone --branch codex/consolidate-modes --single-branch \
  https://github.com/agiertli/redhat-whisper-voice-challenge.git
cd redhat-whisper-voice-challenge

# Authenticate against the NEW cluster using its supplied oc login command.
oc whoami
oc whoami --show-server

cp docs/examples/values-conference.yaml values-conference.yaml
# Edit values-conference.yaml: choose game.requiredLanguage.

# Read-only: no node labels, model scaling, Helm upgrade or data writes.
./deploy.sh --values values-conference.yaml --free-rhdp-gpu --preflight

# Same configuration; now release demo Llama and install.
./deploy.sh --values values-conference.yaml --free-rhdp-gpu
```

For a quick English installation without a venue file:

```bash
./deploy.sh --language en --free-rhdp-gpu --preflight
./deploy.sh --language en --free-rhdp-gpu
```

For Czech, pass `--language cs`. For a different namespace, add
`--namespace booth` to both commands. The installer makes that namespace consistent
across chart resources. The first language is mandatory; there is no silent
default. Command-line language overrides the venue file when both are present.

The default path uses the versioned published UI image in `values.yaml`. It does
not build or push to Anton's registry. `--skip-build` remains a compatible alias
for this default behavior. On a cluster without the bundled Llama, omit
`--free-rhdp-gpu`. An absent demo model is safe to repeat; API failures are not
mistaken for absence, and remaining pods fail the operation.

Installer sequence: validate inputs/chart, discover cluster and GPU/storage,
back up an existing installation, enable monitoring, release the exact opted-in demo model, label
NVIDIA nodes, install/upgrade Helm, wait for model/UI, and run an internal real-audio
smoke test. Default Helm timeout is 1200 seconds. `--timeout 1800` increases it and
also adjusts the warmup Job deadline. A failed operation keeps resources and data
for inspection and prints diagnostic commands/events; it never automatically
uninstalls or deletes storage. GPU preflight is a snapshot; actual scheduling is
the final availability check.

The chart sets `GUNICORN_CMD_ARGS=--preload` so SQLite initialization/migrations run
once before the four workers fork. Live testing caught a first-boot database lock
race without this setting. Keep preloading enabled for this SQLite deployment.

## Game mode

`tournament.enabled: true` is the default. Set it to false to bypass registration
and play without persistent competition. Storage and credentials remain present,
so switching back preserves historical results. Monitoring stays mandatory. See
[game mode and upgrade compatibility](customization/game-mode.md).

## Registration mode

Choose `registration.mode` in `values-conference.yaml` and reuse it on upgrades:

```yaml
registration:
  mode: "username"  # full is the default
```

- `full` retains the existing New Player / Returning Player tabs. New players
  provide a nickname, full name and email.
- `username` uses one form with one public username field. The same action creates
  a new player or resumes the exact existing username (case-sensitive). Names and
  emails are not requested, and submitted personal fields are ignored server-side.
  Use this for third-party conferences where those details are not collected.

Usernames use 2–20 ASCII letters, numbers, underscores or hyphens. Returning by
username is the accepted game behavior; it is not identity verification. Username
mode applies to both `/` and the legacy `/register` entry point.

Both modes share player IDs, scoring, leaderboards, exports, backups and SQLite
storage. New username-only players have empty name/email columns. Switching modes
preserves existing players, scores and signing credentials; it does not delete
previously collected personal data. Start with a fresh event database if a venue
requires that no historical personal data be present. Never clear an active
conference's database as part of switching a setting.

## Choose the admin password

`tournament.adminToken` is the admin dashboard password. Leave it unset to generate
one on first installation, or choose a memorable value such as `whisper@r3dh4t!`.
There is no shared default. Create a private file without a trailing newline:

```bash
umask 077
read -r -s -p 'Choose admin password: ' ADMIN_PASSWORD; printf '\n'
printf '%s' "$ADMIN_PASSWORD" > admin-token
unset ADMIN_PASSWORD
```

For the automated installer, add `--admin-password-file ./admin-token` to the
preflight and installation commands. For direct Helm, add
`--set-file tournament.adminToken=./admin-token` to the Helm command. This file is
ignored by Git; keep the password out of the versioned venue YAML. Omit the
password override on ordinary upgrades to retain the installed password. Supplying
a different value intentionally changes the password and requires updating the
backup laptop's credential file. It does not change the player signing key.

After successful verification, the installer prints the game URL, admin URL and
actual installed admin password. The direct Helm procedure calls the same summary
helper. This output intentionally contains the admin password: use a private
terminal and do not publish its transcript or put it in CI logs.

## Credentials and tournament storage

On first installation, Helm generates independent signing/admin credentials.
Ordinary upgrades reuse the installed `whisper-tournament-secret`. Setting a
non-empty `tournament.secret` or `tournament.adminToken` explicitly rotates it.
Changing the signing secret invalidates player tokens; do not rotate mid-event.
Existing deployments keep their installed credentials, including old shared ones;
plan intentional rotation outside a live tournament.

Get the admin token privately on the installer workstation:

```bash
umask 077
oc get secret whisper-tournament-secret -n whisper \
  -o 'go-template={{index .data "ADMIN_TOKEN" | base64decode}}' > admin-token
```

Transfer that file securely to the backup laptop. Never commit it or paste it into
chat/issue logs. For `/admin`, enter its contents in the UI. A conference laptop
needs the URL and admin token only, not cluster-admin credentials.

SQLite is stored on a ReadWriteOnce PVC, with one UI replica and Recreate
rollouts. This means brief downtime during upgrades; it does not provide HA.
Do not delete `whisper-tournament-db`. The PVC has a Helm keep annotation as an additional
guard against accidental removal; still never use uninstall as recovery. The chart uses a default StorageClass unless
`tournament.storageClass` is specified before initial creation. An existing PVC's
storage class cannot be changed in place. Backup files contain attendee PII and
must be protected and retained according to the event's policy.

## Enable OpenShift user workload monitoring

Monitoring is always enabled as a standard installation step. The wrapper invokes
`scripts/enable-monitoring.sh` before deploying and waits for readiness before
completion. The [direct Helm procedure](HELM-INSTALLATION.md) invokes the same
helper explicitly. It preserves unrelated ConfigMap settings, leaves an enabled
configuration unchanged, and refuses invalid YAML or concurrent conflicting edits.
The helper uses the existing Helm YAML parser; no pip/YAML package is needed.
GPU gauges use DCGM, while persistent AI counters use user workload Prometheus and
Thanos. Both are part of acceptance; do not treat zero counters as verified
monitoring before a scrape cycle and a real request.

## Conference laptop: standalone backups

Copy **only `scripts/backup.sh`** and the admin-token file to the laptop. There is
no repository, Python, `oc`, `jq`, SQLite CLI, package-manager, or pip requirement.
It is Bash 3.2-compatible and uses `curl` plus standard macOS/Linux utilities
(`mkdir`, `mktemp`, `chmod`, `date`, `wc`, `od`, `mv`, `rm`, `sleep`). These are checked
at startup. Bash cannot implement HTTPS on its own. Windows needs an existing
Bash/curl environment such as Git Bash or WSL; plain PowerShell is not supported.

```bash
chmod 600 admin-token
WHISPER_URL=https://YOUR-GAME-HOST ADMIN_TOKEN_FILE=./admin-token \
  BACKUP_DIR=./conference-backups ./backup.sh

# Confirm the first snapshot was saved, then keep this terminal running:
WHISPER_URL=https://YOUR-GAME-HOST ADMIN_TOKEN_FILE=./admin-token \
  BACKUP_DIR=./conference-backups INTERVAL=300 ./backup.sh --loop
```

If neither token variable is set, the script prompts silently in an interactive
terminal. `ADMIN_TOKEN` remains accepted for compatibility, but a protected file
avoids secrets in shell history. No token goes in the URL or curl process arguments.
HTTPS certificate verification is mandatory. For an approved private CA, supply
`CURL_CA_BUNDLE=/path/to/ca.pem`; do not add `-k`.

Each download goes to a private temporary file. HTTP errors, bad SQLite signatures
and truncated page counts are rejected before atomic rename. Only a successful
new snapshot permits pruning; failed downloads never displace the last good
snapshot. Defaults are one snapshot every 300 seconds (plus download/retry time)
and 288 retained snapshots (approximately one day). Run one loop on one laptop. Loop failures remain visible and retries continue;
one-shot failure exits nonzero. Watch for `last success ... NONE` or a stale last
success timestamp. Keep the laptop awake, powered and connected; on macOS use
`caffeinate -i env ... ./backup.sh --loop` if desired.

The existing `/api/admin/backup` endpoint provides a SQLite online-backup snapshot;
it accepts the bearer token used by this script. No application/API changes are
required. The script checks format/completeness, not full SQLite integrity or
arbitrary internal page corruption. A backup is not proven recoverable until a restore drill
passes. A PVC plus periodic snapshots reduces risk; it cannot promise zero loss
of changes since the last successful snapshot. The backup interval is an explicit
recovery-point choice. Keep another protected copy outside the laptop as well.

## Upgrades and recovery

Use the **same venue values file, namespace and explicit language overrides** on
every upgrade. Keep that non-secret file in your team's Git/configuration store.
An omitted first language fails validation rather than silently reverting it.
ConfigMap/credential changes trigger a UI rollout so environment changes take
effect. Do not upgrade an active booth without planning the brief interruption.

```bash
git pull --ff-only
./deploy.sh --values values-conference.yaml --free-rhdp-gpu
```

Before changing an existing installation, the installer downloads and validates a
fresh off-cluster backup to `backups/NAMESPACE/` (or `BACKUP_DIR`). Failure blocks
the upgrade before cluster mutations. For the planned upgrade, pause the laptop loop while the installer downloads
its pre-upgrade snapshot; resume it afterwards. This keeps the one-downloader
operating model. The installer snapshot does not replace the laptop loop. The signed-in installer can retrieve the installed admin credential
without printing it. If the UI/route is broken and cannot serve a backup, fix the
underlying issue first. Recovery may explicitly use an already saved snapshot:

```bash
./scripts/backup.sh --validate /safe/path/tournament-snapshot.db
./deploy.sh --values values-conference.yaml --backup-file /safe/path/tournament-snapshot.db
```

`--backup-file` is an owner assertion that this is the correct, sufficiently recent
snapshot from this event. It is validated but **not restored automatically**. It
allows repair without pretending a fresh backup succeeded. It does not guarantee
that changes newer than that file are protected. Never choose an unrelated or old
snapshot just to bypass a backup failure.

Restore drill: use a disposable installation on a separate cluster/GPU before the
event, register a test player, finish a game,
back up, then restore through its `/admin` dashboard and verify player/game counts
and scores. A one-GPU SNO cannot schedule a second predictor beside the live game. Never
rehearse restore against the live event. For incident recovery,
stop admitting players, preserve the existing database/PVC and external backups,
select the correct snapshot, restore through `/admin`, and verify before reopening.
For a safe application-level restore drill without a second GPU, use the tested
helper against a snapshot on stdin. It starts a separate Python process in the UI
pod and redirects `DB_PATH` to a new temporary database before importing the app:

```bash
oc exec -i deployment/whisper-ui -n whisper -- python3 -c \
  "$(cat tests/live_restore_check.py)" < /safe/path/tournament-snapshot.db
```

It exercises the published restore handler and verifies SQLite integrity, table
counts and scores. It never restores into the running server's database. This is
an isolated application test, not a complete cluster-loss recovery rehearsal.

The signing secret is not inside the database snapshot: preserve it separately in
your approved secret store to keep existing player tokens valid after cluster loss.

The [direct Helm installation](HELM-INSTALLATION.md) is a supported repository
procedure for humans and Bash scripts. Helm itself does not perform the wrapper's
preflight, external backup or smoke checks; the documented sequence supplies them. Always provide the same
venue file/namespace and a timeout longer than `warmup.deadlineSeconds`. Do not use
`helm uninstall` or delete the PVC as a generic retry procedure.

## Troubleshooting

- **Preflight finds no GPU:** inspect `oc get nodes`, GPU Operator/device plugin,
  node readiness and allocatable `nvidia.com/gpu`. It does not provision hardware.
- **GPU occupied:** inspect `oc get pods -A -o wide`; only the named RHDP demo Llama
  is eligible for the opt-in. Do not scale down arbitrary customer workloads.
- **Pending pod/PVC:** `oc describe pod ... -n whisper` and `oc describe pvc
  whisper-tournament-db -n whisper`; check RAM/CPU, taints, GPU requests and CSI.
- **ImagePullBackOff:** inspect pod events and cluster registry credentials; verify
  image tags and registry entitlement. Do not print pull-secret contents.
- **Warmup/inference failure:** inspect `oc logs job/whisper-vllm-warmup -n whisper`
  and predictor logs. Warmup errors now fail the Job instead of claiming success.
  Do not copy the old low GPU-memory examples or change vLLM flags blindly.
- **First language wrong:** verify the venue file, `REQUIRED_CHALLENGE_LANGUAGE` in
  `whisper-ui-config`, completed UI rollout and a fresh browser page. The first
  challenge changes; later challenges remain drawn from multilingual pools.
- **Route/microphone:** require valid HTTPS trusted by the laptop/browser and grant
  microphone permission. Internal smoke tests do not exercise the browser or DNS.
- **Metrics missing:** monitoring is mandatory. Run `./scripts/enable-monitoring.sh
  --wait`; it preserves existing settings and never silently disables monitoring.
  Check the user-workload Prometheus pod, `whisper-metrics` ServiceMonitor,
  Thanos/DCGM access, and allow a scrape cycle after actual requests.
- **Backup errors:** confirm the exact HTTPS URL, token and CA, disk space, network
  and last-success timestamp. Keep the last good snapshots; do not reset scores.

## Building a UI patch and running local checks

Chart/configuration changes do not require rebuilding the UI. Application source
changes do. Authenticate to your own writable registry first, then choose a new
semver tag; do not overwrite a published version. Podman or Docker is used only
with `--build`, targeting linux/amd64 even on Apple Silicon.

```bash
IMAGE_REGISTRY=quay.io/YOUR-ORG VERSION=v2.11.0-rc.1 \
  ./deploy.sh --build --values values-conference.yaml --free-rhdp-gpu

python3 -m pip install -r tests/requirements.txt
python3 -m unittest discover -s tests -v
helm lint helm/whisper --set game.requiredLanguage=en
bash -n deploy.sh scripts/*.sh
```

## Live acceptance checklist (before sharing with the next owner)

- Fresh clone and blank installer environment with no `now.env` or prior memory.
- Preflight read-only; correct cluster; named Llama releases the only GPU.
- Runtime/modelcar/UI images pull; PVC binds under the normal OpenShift SCC.
- Warmup succeeds and real-audio smoke test produces sensible English text.
- Owner-selected first language, registration, complete game, leaderboard, TV/admin.
- Same-config upgrade preserves credentials, player token, scores and language.
- Language change takes effect after rollout; then restore venue configuration.
- UI pod restart preserves results; backup works during active games.
- Standalone backup on a blank macOS/Linux laptop; invalid download keeps last good file.
- Restore drill in a disposable namespace recovers counts/scores and preserves live data.
- Record exact OCP/RHOAI/runtime/modelcar/UI/chart versions and remaining limitations.
