# Customization Guide

This guide explains how to adapt the Red Hat Whisper Voice Challenge for a different conference, language, or environment.

## Challenge Phrases

**File:** `challenges.json` (repo root)

This is the most important customization file. It contains the phrases that attendees must speak during the voice challenge. The default phrases are Red Hat / OpenShift / DevOps themed — designed for Red Hat conferences.

### Structure

```json
{
  "en": [
    "Phrase one in English",
    "Phrase two in English",
    "Phrase three in English"
  ],
  "sk": [
    "Fráza jedna po slovensky",
    "Fráza dva po slovensky"
  ]
}
```

- Each key is an [ISO 639-1 language code](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)
- Each value is an array of phrases in that language
- You need at least as many phrases per language as `game.challengeCount` (default: 5)
- The game randomly picks phrases from the array — more phrases = more variety

### Tips for writing good phrases

- Keep phrases **5-10 words** long — short enough to remember, long enough to challenge
- Use clear, commonly-known words — Whisper struggles with highly technical jargon
- Avoid punctuation-heavy phrases — accuracy scoring compares raw text
- Test your phrases against Whisper before the conference to catch recognition issues
- Include product names (OpenShift, RHEL, Ansible) — they're fun and attendees enjoy saying them

### Adding a new language

1. Add the language code and phrases to `challenges.json`
2. Add the language to `supportedLanguages` in `helm/whisper/values.yaml`:
   ```yaml
   supportedLanguages: |
     {
       "en": "English",
       "ja": "日本語"
     }
   ```
3. Rebuild and redeploy: `./deploy.sh`

## Conference Settings

All set via Helm values — no code changes needed.

```bash
helm upgrade whisper helm/whisper \
  --set conference.name="DevConf.cz 2026" \
  --set game.requiredLanguage="cs" \
  --set game.challengeCount="3" \
  --set game.winThreshold="2"
```

| Value | What it does |
|-------|-------------|
| `conference.name` | Displayed in the UI header |
| `game.requiredLanguage` | Default language for challenges (attendees can switch) |
| `game.challengeCount` | How many challenges per game session |
| `game.winThreshold` | Minimum correct answers to "win" |

Lower `challengeCount` for busy booths (faster turnover), raise it for dedicated demo areas.

## Branding

### Colors

Edit `src/templates/index.html`, find the `:root` CSS block:

```css
:root {
    --red-hat-red: #ee0000;    /* Primary accent color */
    --ux-black: #151515;        /* Background */
}
```

### Fonts

The UI loads Red Hat brand fonts from Google Fonts. To use different fonts, change the `@import` URL and `font-family` declarations in the template.

### Logo

Replace `docs/logo.png` with your event's logo. The README references this file.

### Title

The page title is set from `conference.name` via the Helm value — it renders as "Red Hat Whisper Voice Challenge | {conference.name}" in the browser tab.

The heading "Red Hat Whisper Voice Challenge" is hardcoded in the HTML template at line ~553. Edit `src/templates/index.html` if you need a different game name.

## GPU Configuration

### Different GPU types

The default config targets NVIDIA L40S. For other GPUs, change the node selector and memory settings:

```yaml
# values.yaml
model:
  nodeSelector:
    nvidia.com/gpu.product: NVIDIA-A100-SXM4-40GB   # Match your GPU
  resources:
    limits:
      memory: 24Gi        # Adjust based on GPU VRAM
      nvidia.com/gpu: "1"

gpu:
  memoryUtilization: "0.2"  # Fraction of VRAM for KV cache
```

**GPU memory utilization guidelines:**
- L40S (48GB): `0.2` is fine (allocates ~9.6 GB for KV cache)
- A100 (40GB): `0.2-0.3` works well
- T4 (16GB): `0.4-0.5` — tighter, but works for low-concurrency demos
- Consumer GPUs (RTX 3060 12GB): `0.5` — minimal headroom

Higher values allow more concurrent KV cache entries but leave less VRAM for model weights.

## Container Registry

The default registry is `quay.io/agiertli/whisper-ui`. To use your own:

```bash
# Option 1: Environment variables with deploy.sh
IMAGE_REGISTRY=quay.io/your-org IMAGE_NAME=whisper-ui ./deploy.sh

# Option 2: Helm values
helm upgrade whisper helm/whisper \
  --set image.repository=quay.io/your-org/whisper-ui \
  --set image.tag=v1.0.0
```

## Model Variants

The default model is `RedHatAI/whisper-large-v3-turbo-quantized.w4a16` pulled as an OCI modelcar from the Red Hat registry. No S3 or Data Connection needed.

To use a different model, you have two options:

### Option 1: OCI modelcar (recommended)

If a modelcar image exists in `registry.redhat.io`, set the `storageUri`:

```yaml
model:
  storageUri: "oci://registry.redhat.io/rhelai1/modelcar-<model-name>:<version>"
```

### Option 2: HuggingFace direct download

For models without a modelcar, use `hf://` to download from HuggingFace at deploy time:

```yaml
model:
  storageUri: "hf://RedHatAI/whisper-large-v3-FP8-dynamic"
```

This downloads model weights during pod startup (slower first deploy, but no registry setup needed).

After changing the model, also update `whisperApi.displayName` for the UI label and redeploy.

## Monitoring

### Prometheus metrics (persistent)

The app queries OpenShift's built-in Prometheus (via Thanos querier) for cumulative request counts and latencies that survive pod restarts. This requires:
- User Workload Monitoring enabled on the cluster
- The ServiceAccount has `cluster-monitoring-view` ClusterRoleBinding (created by the Helm chart)

### DCGM GPU metrics (real-time)

GPU temperature, utilization, and VRAM usage come from the NVIDIA DCGM exporter. The app auto-discovers the exporter service in the `nvidia-gpu-operator` namespace.

If your DCGM exporter is in a different namespace or uses a different service name:
```yaml
dcgmExporterUrl: "http://your-dcgm-service.your-namespace.svc:9400/metrics"
```
