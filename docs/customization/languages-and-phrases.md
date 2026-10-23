# Choose the first language and customize phrases

## First required language

Set the language explicitly in `values-conference.yaml`:

```yaml
game:
  requiredLanguage: "de"
```

Examples: `de` German, `cs` Czech, `sk` Slovak, `en` English. No country is inferred
from the workstation. The agent prompt accepts names such as German and normalizes
them to codes; the script and Helm require a supported two-letter code.

Only the first challenge is forced to that language. Later challenges draw from
[difficulty groups](difficulty-groups.md). If the admin enables Mainstage mode,
the first challenge uses that language's Mainstage phrase when one exists.

Keep the chosen language in the same values file on all upgrades. The chart's
default is deliberately empty, so an omitted choice fails instead of resetting
silently to another language.

## Change existing challenge phrases

Edit [helm/whisper/challenges.json](../../helm/whisper/challenges.json), retaining
its object of language codes and nonempty arrays of strings. The chart loads
this JSON into environment configuration. There is no separate phrase list per
difficulty: the difficulty chooses languages, and the selected language's array
supplies a random phrase. Repeated phrases are possible.

A language needs at least one usable phrase; it need not have five phrases for a
five-round game. More varied phrases make repeated play more interesting. Use
phrases suitable for the audience and microphone conditions.

## Add a language

1. Add its nonempty phrase array to `helm/whisper/challenges.json`.
2. Add its flag/display name to `languageInfo` (a JSON string) in your values file.
   Copy the complete default object first: overriding the string replaces it.
3. Include the code in any desired difficulty pools. If it is the first required
   language, also set `game.requiredLanguage` to its code.
4. Confirm the chosen Whisper model transcribes it acceptably in a real speech test.

Inspect the existing `languageInfo` format in
[helm/whisper/values.yaml](../../helm/whisper/values.yaml), for example
`"de": {"flag": "🇩🇪", "name": "German"}`. Preserve metadata for all other languages
still referenced by the pools. Helm validates matching metadata and phrase arrays;
it does not evaluate linguistic quality.

## Deploy and verify

```bash
helm lint helm/whisper -f values-conference.yaml
./deploy.sh --values values-conference.yaml --namespace whisper --free-rhdp-gpu
```

For direct Helm, use its [backup/upgrade procedure](../HELM-INSTALLATION.md#6-upgrade-directly-with-helm).
The changed ConfigMap restarts the UI; no image rebuild is needed. Start a fresh
game at each difficulty, verify the first language/phrase, then test speech.
Commit phrase changes and the non-secret values file to your owner's configuration
repository so the same setup can be reproduced.
