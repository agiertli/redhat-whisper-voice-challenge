# Traditional installation with Helm

This is the human-operated path: explicit Bash/oc commands and **Helm directly**.
It deploys the same chart used by the agent and `deploy.sh`. It needs no agent,
workstation Python, image build engine, registry push access or personal memory.
For automated preflight/backup/error handling, `deploy.sh` remains an optional
convenience wrapper; it is not required by the commands below.

## 1. Prerequisites and owner choices

Use the prepared RHDP OpenShift AI 3 SNO GPU environment. Install Git (to clone),
Bash, oc and Helm 3 on the deployment workstation. Backups also need curl and
standard macOS/Linux utilities. The cluster needs configured KServe/GPU operators,
a Ready NVIDIA GPU, registry pull access, enough RAM/CPU and persistent storage.
See [the shared runbook](INSTALLATION.md) for the exact target and limitations.

Log into the intended cluster as cluster-admin using RHDP's supplied command:

```bash
oc whoami
oc whoami --show-server
oc auth can-i '*' '*' --all-namespaces
oc get crd inferenceservices.serving.kserve.io servingruntimes.serving.kserve.io
oc get nodes -l nvidia.com/gpu.present=true
oc get storageclass
```

Confirm that this is the correct environment before changing workloads. Check
OpenShift AI/GPU Operator status in the console. A StorageClass must be default,
or select `tournament.storageClass` in the venue file before first deployment.
Cluster-admin permissions do not supply Red Hat registry entitlement.

```bash
git clone --branch tournament-mode --single-branch \
  https://github.com/agiertli/redhat-whisper-voice-challenge.git
cd redhat-whisper-voice-challenge
```

The owner **must decide the first challenge language**. The example below uses
German; change `de` to `cs`, `sk`, `en`, etc. before running it. Later rounds remain
multilingual. Keep this non-secret file and reuse it on every upgrade:

```bash
cat > venue.yaml <<'VALUES'
conference:
  name: "Our Conference"
game:
  requiredLanguage: "de"
VALUES
```

The chart's default language is deliberately empty; omitting the decision fails
validation. No cluster domain or hardcoded route URL is required.

## 2. Release the RHDP demo GPU

Inspect the bundled model. On the usual one-GPU RHDP SNO it must stop before
Whisper can schedule. Only do this when you own/are authorized to stop that model:

```bash
oc get inferenceservice llama-32-3b-instruct -n my-first-model
./scripts/free-gpu.sh my-first-model llama-32-3b-instruct
oc get deployment llama-32-3b-instruct-predictor -n my-first-model
oc get pods -n my-first-model \
  -l serving.kserve.io/inferenceservice=llama-32-3b-instruct
```

The helper is plain Bash/oc: it patches predictor `minReplicas` to zero, scales the
Deployment to zero and fails if the API errors or pods remain. An absent demo
model is a no-op. Do not stop unrelated GPU consumers. Then add the role label
required by the chart's default node selector:

```bash
oc label nodes -l nvidia.com/gpu.present=true \
  node-role.kubernetes.io/gpu-worker=true --overwrite
```

## Required monitoring

Monitoring is mandatory for every game installation. GPU gauges come from DCGM;
persistent request/token counters also require OpenShift user workload monitoring.
Enable it as a standard prerequisite, without a separate owner-permission step:

```bash
./scripts/enable-monitoring.sh
```

This helper needs only Bash, oc and Helm (already required here). It uses Helm's
YAML parser to set `enableUserWorkload: true`, retaining all other monitoring
settings, ConfigMap data, labels and annotations. It creates a missing ConfigMap,
leaves an already-enabled one unchanged, and uses its resource version to reject
concurrent edits safely. Invalid existing YAML fails rather than being overwritten.
It does not install a second Helm release or tie cluster monitoring to the game's
uninstall lifecycle. Keep monitoring enabled after the game is removed.

After installing the game, wait for monitoring readiness as well:

```bash
./scripts/enable-monitoring.sh --wait
```

KServe creates the `whisper-metrics` ServiceMonitor. Allow a scrape cycle after
real requests before judging persistent counters. Verify GPU gauges and AI
counters in the main screen before opening the booth.

## 3. Validate and install directly with Helm

```bash
helm lint helm/whisper -f venue.yaml

helm upgrade --install whisper helm/whisper \
  --namespace whisper --create-namespace \
  --values venue.yaml \
  --wait --timeout 20m
```

This uses the already-published UI image pinned in `values.yaml`; it does not build
or push anything. The chart creates the UI, route, model runtime/InferenceService,
RBAC, tournament PVC and independently generated credentials. Its post-install/
post-upgrade Job waits for vLLM and performs warmup. The default warmup deadline
is 1140 seconds, so keep the Helm timeout longer (20 minutes here).

No `--atomic`/automatic uninstall is used: failures retain resources for diagnosis.
If installation fails, inspect pods, events and warmup logs, correct the cause,
then repeat the same Helm command. Do not delete the PVC or reset tournament data.

For another namespace, use the same new namespace consistently in every command.
The chart inherits Helm's namespace. Do not set a different `namespace` value in
the venue file; it is retained only for legacy configurations.

## 4. Verify before admitting players

```bash
oc wait --for=condition=Ready inferenceservice/whisper -n whisper --timeout=600s
oc rollout status deployment/whisper-ui -n whisper --timeout=300s
./scripts/enable-monitoring.sh --wait
./scripts/verify-install.sh whisper de
oc get route whisper-ui -n whisper -o jsonpath='{.spec.host}'
```

The verification helper is Bash/oc and runs Python **inside the deployed UI image**;
no Python installation is needed on this workstation. It checks the configured
first language, pages, leaderboard/database and real-audio UI-to-vLLM transcription.
Pass the same language chosen in `venue.yaml`.

Open `https://HOST/` with trusted TLS, grant browser microphone permission and
complete a real game. Check `/register`, `/tv`, `/admin` and scores. API/audio-file
checks do not prove that the laptop microphone/browser capture path works.

Retrieve the admin token into a private file, not terminal/chat output:

```bash
umask 077
oc get secret whisper-tournament-secret -n whisper \
  -o 'go-template={{index .data "ADMIN_TOKEN" | base64decode}}' > admin-token
```

Use it in `/admin` and transfer it securely to the backup laptop. The tournament
signing secret must also be protected separately if you need player tokens to
survive a cluster-loss restore. No credential belongs in the venue YAML or Git.

## 5. Start the separate conference backup

Copy only `scripts/backup.sh` and the protected admin-token file to one laptop:

```bash
WHISPER_URL=https://HOST ADMIN_TOKEN_FILE=./admin-token \
  BACKUP_DIR=./conference-backups ./backup.sh

WHISPER_URL=https://HOST ADMIN_TOKEN_FILE=./admin-token \
  BACKUP_DIR=./conference-backups INTERVAL=300 ./backup.sh --loop
```

Confirm the first snapshot, keep the laptop awake/connected and watch for failures.
The standalone script requires no oc, Helm, Python, jq or SQLite CLI. It verifies
TLS and rejects failed/truncated downloads. It does not run full SQLite integrity
checks. Rehearse restore on an isolated database before the event. Operations,
retention and recovery limitations are in [INSTALLATION.md](INSTALLATION.md).

## 6. Upgrade directly with Helm

Schedule an interruption and stop admitting players. Pause the laptop loop so only
one downloader runs. Before any changes, take a fresh external backup using that
script. On the installer workstation (which has oc), this complete sequence keeps
the token out of command arguments:

```bash
umask 077
oc get secret whisper-tournament-secret -n whisper \
  -o 'go-template={{index .data "ADMIN_TOKEN" | base64decode}}' > admin-token
GAME_HOST=$(oc get route whisper-ui -n whisper -o jsonpath='{.spec.host}')
WHISPER_URL="https://$GAME_HOST" ADMIN_TOKEN_FILE=./admin-token \
  BACKUP_DIR=./pre-upgrade-backups ./scripts/backup.sh

# Continue ONLY if the backup succeeded. Reuse the same venue file.
./scripts/enable-monitoring.sh
helm upgrade --install whisper helm/whisper \
  --namespace whisper --create-namespace \
  --values venue.yaml --wait --timeout 20m

./scripts/enable-monitoring.sh --wait
./scripts/verify-install.sh whisper de
```

When putting these commands in your own Bash script, use `set -euo pipefail` so a
failed backup stops execution. Direct Helm does not automatically take the backup
or run the smoke check; the human/script must do both. The supplied `deploy.sh`
wrapper enforces those steps if preferred.

Ordinary upgrades reuse the installed signing/admin Secret. Only explicit non-empty
`tournament.secret`/`tournament.adminToken` values rotate credentials. Configuration
changes roll the UI so env settings take effect. Keep first-language selection in
the same venue file: never replace it with a minimal values file that omits the
owner's choices. Verify existing player login, score persistence and the first
language, then resume the backup loop and reopen the booth.
