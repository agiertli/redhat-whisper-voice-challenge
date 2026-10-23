# Venue customization

Use [INSTALLATION.md](INSTALLATION.md) for installation, backup and upgrade safety.
Keep non-secret venue settings in a values file and pass the same file on every
upgrade. Do not edit baked application defaults to configure an event.

```yaml
conference:
  name: "Your Conference"
game:
  requiredLanguage: "cs"  # Required owner choice; FIRST challenge only.
  challengeCount: "5"
  winThreshold: "4"
```

The owner chooses the first language explicitly. Later rounds draw from
`difficultyPools` in `values.yaml`. Add languages to those JSON pools and
`languageInfo` only when corresponding non-empty phrase arrays exist in
`helm/whisper/challenges.json`. The chart rejects unknown/missing languages and
malformed JSON. Each round selects a phrase from its selected language; the number
of phrases in one language need not equal the total number of game rounds.

Edit `challenges.json`, then upgrade with the venue file: a changed ConfigMap
rolls the UI automatically. No UI rebuild is needed for configuration changes.
Changing branding in `src/templates/` does require a new UI image/tag.

Keep the runtime/modelcar combination in the chart unless a replacement has been
tested on the target operator/GPU. `model.resources.memory` is **system RAM**, not
GPU VRAM. `gpu.memoryUtilization` controls the vLLM allocation fraction; old examples
using 0.2–0.3 are not valid for the current baseline and are rejected by the chart.
Do not change model-length arguments based on older documentation; verify the
specific model/runtime in a live transcription test.

`route.host` is optional: OpenShift assigns a host when empty. `clusterDomain` and
`supportedLanguages` are obsolete and are not installation inputs.
`tournament.storageClass` can select an existing StorageClass on first installation.
Do not change it on an existing PVC or scale the SQLite UI above one replica.

Credential rotation is explicit and is described in the runbook. Do not put
signing/admin keys in committed venue files. The display name is a UI label;
inspect the modelcar/runtime to verify the actual loaded model and quantization.
