# Red Hat Whisper Voice Challenge

Interactive voice transcription game for Red Hat conference booths. Attendees speak challenge phrases, AI transcribes them in real time, and accuracy is scored.

## Quick Reference

- **Main app**: `src/app_streaming.py` (Flask, single file — includes tournament API)
- **Frontend**: `src/templates/index.html` (single-page HTML/CSS/JS — registration, game, leaderboard)
- **TV leaderboard**: `src/templates/tv.html` (full-screen auto-refresh for booth monitor)
- **Admin dashboard**: `src/templates/admin.html` (player management, CSV export, score reset)
- **Challenge phrases**: `helm/whisper/challenges.json` (Red Hat/OpenShift themed, 20+ languages)
- **Helm chart**: `helm/whisper/` (deploys everything: UI, vLLM, RBAC, monitoring, tournament persistence)
- **Deploy script**: `./deploy.sh` (prerequisites + build + push + helm install + model readiness wait)

## Installation Playbook

This section is written so that a Claude session (or a human) can deploy the entire system from scratch on a fresh OpenShift cluster. Follow the steps in order.

### Prerequisites

**Cluster access**: You need **cluster-admin** on an OpenShift 4.14+ cluster. The Helm chart creates ClusterRole and ClusterRoleBindings.

**Recommended cluster (Red Hatters)**: Order **"RHOAI on OCP on AWS with NVIDIA GPUs"** from [RHDP](https://demo.redhat.com), enable **Open Environment**, select **g6.4xlarge** instance type. This comes with RHOAI and GPU nodes pre-configured. Open Environment lets you add more GPU nodes via the MachineSet API.

**Required operators** (install via OperatorHub if not present — RHDP clusters have these already):
1. **Red Hat OpenShift AI** (RHOAI) — provides KServe, ServingRuntime, InferenceService CRDs. Both RHOAI 2.x and 3.x are supported. When using RHOAI 3.x, update `vllm.image` in `values.yaml` to the RHOAI 3 image (e.g., `registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.2.4`). Find the correct image by inspecting existing ServingRuntimes: `oc get servingruntimes -A -o yaml | grep image:`
2. **NVIDIA GPU Operator** — manages GPU nodes and deploys DCGM exporter for metrics

**GPU nodes**: At least one worker node with an NVIDIA GPU (12+ GB VRAM). The node must have the label `node-role.kubernetes.io/gpu-worker=true`. The `deploy.sh` script labels GPU nodes automatically by detecting `nvidia.com/gpu.present=true`. If no GPU nodes exist, you need to create a MachineSet (cloud-specific — e.g., `g6.4xlarge` on AWS).

**SNO (Single-Node OpenShift)**: Fully supported. The single node serves as control plane, worker, and GPU node. The deploy script will auto-label it. Instance types like `g6.12xlarge` (4x L4 GPUs, 22 GB VRAM each) work well.

**Tools on your workstation**: `oc`, `helm`, `podman` (or `docker`)

**Registry access**: `registry.redhat.io` (Red Hat subscription required, for vLLM runtime and modelcar images)

### Step 1: Cluster Prerequisites

The `deploy.sh` script handles these automatically, but if deploying manually:

1. **Label GPU nodes** (required for SNO or clusters without the `gpu-worker` role):
   ```bash
   # Auto-detect and label all GPU nodes
   for node in $(oc get nodes -l nvidia.com/gpu.present=true -o name); do
     oc label "$node" node-role.kubernetes.io/gpu-worker=true --overwrite
   done
   ```

2. **Enable user workload monitoring** (optional, for persistent metrics):
   ```bash
   oc apply -f - <<EOF
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: cluster-monitoring-config
     namespace: openshift-monitoring
   data:
     config.yaml: |
       enableUserWorkload: true
   EOF
   ```

### Step 2: Configure values

Edit `helm/whisper/values.yaml`:
- `clusterDomain` — **REQUIRED**: your cluster's apps domain (find it with `oc get ingresses.config cluster -o jsonpath='{.spec.domain}'`)
- `conference.name` — your conference name
- `game.requiredLanguage` — default language code (e.g., `sk`, `cs`, `en`)
- `model.nodeSelector` — match your GPU type if not using the default
- `gpu.memoryUtilization` — fraction of GPU memory for vLLM (default: `0.9`). Do NOT set below `0.5` — the Whisper model's PyTorch activation peak (~10 GiB) will exceed the allocation and crash vLLM with "No available memory for the cache blocks"

Edit `challengePhrases` in `helm/whisper/values.yaml` if you want different challenge phrases.

### Step 3: Deploy

The Helm chart deploys **everything** — the UI app, the vLLM ServingRuntime, the Whisper InferenceService (with OCI modelcar), RBAC for Prometheus, and monitoring config.

A pre-built UI image is available at `quay.io/agiertli/whisper-ui` — no build needed unless you've modified the source code.

```bash
# Deploy using the pre-built image (no build needed)
helm upgrade --install whisper helm/whisper \
  --namespace whisper --create-namespace

# Or build your own image and deploy:
export IMAGE_REGISTRY=quay.io/your-org
./deploy.sh
```

The InferenceService will take a few minutes to start — it pulls the model weights from the Red Hat registry on first boot.

### Step 4: Verify

```bash
# Wait for the vLLM model to be ready
oc wait --for=condition=Ready inferenceservice/whisper -n whisper --timeout=600s

# Check all pods are running
oc get pods -n whisper

# Get the UI URL
oc get route whisper-ui -n whisper -o jsonpath='{.spec.host}'
```

Open the UI URL in a browser and test a voice challenge.

## Current Deployment

**Cluster**: SNO (Single-Node OpenShift 4.20) on AWS `g6.12xlarge` (4x NVIDIA L4 GPUs, 22 GB VRAM each)
**RHOAI version**: 3.4.3
**vLLM image**: `registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.2.4` (RHOAI 3.x image)
**Namespace**: `whisper`
**Language**: Polish (`pl`)
**UI URL**: `https://whisper-ui-whisper.apps.ocp.dghv9.sandbox258.opentlc.com`
**Whisper API URL**: `https://whisper-whisper.apps.ocp.dghv9.sandbox258.opentlc.com`
**User workload monitoring**: Enabled (cluster-monitoring-config ConfigMap created)

### Redeployment notes

- The SNO node was labeled `node-role.kubernetes.io/gpu-worker=true` manually (auto-detected via `nvidia.com/gpu.present=true`)
- RHOAI 3.x uses vLLM images from `registry.redhat.io/rhaiis/` (not `quay.io/modh/` as in RHOAI 2.x). Check the installed ServingRuntimes for the correct image tag: `oc get servingruntimes -A -o yaml | grep image:`
- The modelcar image `registry.redhat.io/rhelai1/modelcar-whisper-large-v3-turbo-quantized-w4a16:1.5` works with both RHOAI 2.x and 3.x
- KServe API versions (`ServingRuntime v1alpha1`, `InferenceService v1beta1`) are unchanged in RHOAI 3.4.3

## Tournament Mode

The `tournament-mode` branch adds day-long tournament support for conference booths: player registration, persistent scoring, a public leaderboard, a TV display, and an admin dashboard.

### Architecture

- **Persistence**: SQLite with WAL mode on a 1Gi PVC at `/app/data/tournament.db`
- **Auth**: HMAC-SHA256 tokens (stateless, no server-side sessions). `TOURNAMENT_SECRET` env var is the signing key.
- **Scoring**: Server-side Levenshtein similarity. Formula: `difficulty_mult * (avg_accuracy * 100) * speed_bonus`
  - Difficulty multipliers: easy=1.0, medium=1.5, hard=2.0
  - Speed bonus: `max(0.8, 1.2 - duration/600)` — range 0.8-1.2, neutral at 2 min, floor at 4 min
  - Skipped attempts are excluded from accuracy (no penalty), but cost time
  - Max 1 skip per game (server-enforced)
  - Only best score per player appears on leaderboard

### Additional Pages

- **`/tv`** — Full-screen auto-refreshing leaderboard for a booth monitor (top 15, 10s refresh). Conference name is configurable via `conference.name` in values.yaml.
- **`/admin`** — Admin dashboard (token-protected). Features: expandable player rows showing all games, "Export Best Scores" CSV, "Export All Games" CSV, "Reset All Scores" button (deletes games/attempts, keeps players).

### Tournament Helm Values

```yaml
tournament:
  storage: "1Gi"     # PVC size for SQLite
  secret: ""          # HMAC signing key (auto-generated if empty — PIN IT after first deploy)
  adminToken: ""      # Admin dashboard password (auto-generated if empty)
```

**Critical**: Pin `tournament.secret` after first deploy. `randAlphaNum` regenerates on every `helm upgrade` if not set, which invalidates all player tokens mid-conference:
```bash
# Get the current secret
oc get secret whisper-tournament-secret -n whisper -o jsonpath='{.data.TOURNAMENT_SECRET}' | base64 -d

# Pin it on all future upgrades
helm upgrade whisper helm/whisper -n whisper \
  --set tournament.secret=<value-from-above> \
  --set tournament.adminToken=<your-admin-token>
```

### Tournament API Endpoints

| Method | Route | Auth | Purpose |
|--------|-------|------|---------|
| POST | `/api/register` | none | Register new player (nickname, name, email) |
| POST | `/api/login` | none | Returning player login (nickname + email) |
| GET | `/api/player/me` | token | Current player info |
| POST | `/api/game/start` | token | Start game with difficulty |
| POST | `/api/game/<id>/attempt` | token | Submit attempt (server computes accuracy) |
| POST | `/api/game/<id>/complete` | token | Finalize game, get score + rank |
| GET | `/api/leaderboard` | none | Public leaderboard (best score per player) |
| GET | `/api/admin/players` | admin | Player list with PII |
| GET | `/api/admin/players/<id>/games` | admin | All games for a player |
| GET | `/api/admin/export` | admin | CSV: best scores (for prizes) |
| GET | `/api/admin/export-games` | admin | CSV: all games (for analysis) |
| POST | `/api/admin/reset-scores` | admin | Delete all games/attempts |

### Booth Hardware Requirements

Audio processing happens **client-side** in the browser (MediaRecorder API, WebAudio VAD). This means the **booth laptop matters**:

- **Recommended**: Apple MacBook Pro with M-series chip (M1/M2/M3/M4). Fast client-side audio encoding, minimal latency between speech and API submission.
- **Avoid**: Low-spec laptops (older Intel, <8 GB RAM). Slow audio processing causes delays and silence gaps in the audio chunks sent to vLLM, which makes Whisper hallucinate (repeat phrases, generate phantom text, produce garbage output).
- **External mic**: Use a decent USB microphone for noisy booth environments. The built-in laptop mic picks up too much background noise.
- **Browser**: Chrome/Edge recommended. Firefox MediaRecorder support varies.

## Container Image Tagging Policy

**Never use the `latest` tag.** Use semantic versioning (`v1.0.0`, `v1.1.0`, `v2.0.0`). Bump MAJOR for breaking changes, MINOR for new features, PATCH for fixes. The `deploy.sh` script accepts a `VERSION` env var — set it explicitly.

## 12-Factor App Principles

This app MUST follow cloud-native / 12-factor principles. Enforce these on every change:

1. **Config via env vars** — ALL configuration comes from env vars, injected via ConfigMap. Never hardcode URLs, names, or thresholds. Never read config from files baked into the image.
2. **Stateless processes** — The app must be share-nothing. No in-process state that breaks with multiple replicas. Caches are acceptable only if stale data is harmless.
3. **Backing services as attached resources** — Whisper API, Prometheus, DCGM are all accessed via URL env vars. Swapping any is a ConfigMap change.
4. **Logs as event streams** — Log to stdout only. No file-based logging.
5. **No config in container images** — Challenge phrases, supported languages, conference name, API URLs — all come from the ConfigMap/env vars. Changing config = `helm upgrade`, never rebuild.
6. **Explicit dependencies** — `requirements.txt` pins everything. No implicit system deps.

## Challenge Phrases

Defined in `helm/whisper/challenges.json` (a standalone JSON file loaded by the Helm chart via `.Files.Get` into the ConfigMap). Edit the JSON file, run `helm upgrade` — no image rebuild needed.

You need at least as many phrases per language as `game.challengeCount` (default: 5).

## Helm Chart

The chart in `helm/whisper/` deploys everything:
- UI Deployment + Service + Route
- ServiceAccount + ClusterRole + ClusterRoleBindings (for Prometheus access)
- ConfigMap (all app configuration)
- ServingRuntime (vLLM config)
- InferenceService (Whisper model with OCI modelcar)
- PersistentVolumeClaim (tournament SQLite database)
- Secret (tournament HMAC key + admin token)

### Key commands

```bash
# Install / upgrade
helm upgrade --install whisper helm/whisper \
  --namespace whisper --create-namespace \
  --set image.tag=$(git rev-parse --short HEAD)

# Change conference
helm upgrade whisper helm/whisper -n whisper \
  --set conference.name="DevConf 2026" \
  --set game.requiredLanguage="cs"

# Change GPU memory
helm upgrade whisper helm/whisper -n whisper \
  --set gpu.memoryUtilization=0.3
```

See `helm/whisper/values.yaml` for all parameters.

## Metrics Architecture

vLLM metrics are persisted via OpenShift user workload monitoring (Prometheus). The UI queries Thanos querier for cumulative counters (request counts, token totals) so they survive pod restarts. DCGM GPU metrics (VRAM, temperature, utilization) are scraped directly from the NVIDIA DCGM exporter for real-time data.

The ServiceMonitor for the vLLM pod is auto-created by KServe when the InferenceService is deployed.

## Model

Default model: `RedHatAI/whisper-large-v3-turbo-quantized.w4a16` (W4A16 quantized, pulled as OCI modelcar from `registry.redhat.io`). No S3 or Data Connection needed.

To use a different model, change `model.storageUri` in `values.yaml`. Supported URI schemes:
- `oci://` — OCI modelcar from a container registry (recommended)
- `hf://` — download from HuggingFace at deploy time (slower startup, no registry setup)
