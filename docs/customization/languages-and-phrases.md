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

### 1. Verify Whisper support

The game uses `openai/whisper-large-v3`, which supports 99 languages. Before
any configuration changes, confirm the language is in the model's supported set.
If it is not, the language **cannot** be added — Whisper will not transcribe it.

Languages with known low accuracy in Whisper (low-resource languages with poor
WER scores on the Fleurs benchmark) are technically supported but may make the
80% win threshold unreachable for players. Test before committing to a live event.

### 2. Prepare challenge phrases

Add a nonempty phrase array to `helm/whisper/challenges.json`. Nine phrases per
language is the baseline; more variety improves replay value. Follow this style:

- **Theme:** Red Hat, open source, cloud, AI, Kubernetes, containers, DevOps,
  automation, security — the same tech topics used across all existing languages.
- **Length:** 4–8 words, natural spoken sentences.
- **Script:** use the language's native writing system (Cyrillic, Georgian, CJK,
  Arabic, Devanagari, Thai, etc.). Do not transliterate.
- **Quality:** correct grammar, diacritics, and word order. Avoid abbreviations
  or jargon that a native speaker would not say aloud. Have a native speaker
  review if possible.

### 3. Add language metadata

Add the flag emoji and English display name to `languageInfo` in your values
file. Copy the complete default object from
[helm/whisper/values.yaml](../../helm/whisper/values.yaml) first — overriding
`languageInfo` replaces the whole object. Example entry:
`"de": {"flag": "🇩🇪", "name": "German"}`. Preserve metadata for all other
languages still referenced by the pools.

### 4. Assign to difficulty pools

Include the new language code in the appropriate difficulty pool:

- **Latin script** → add to `easy` (it propagates to `medium` and `hard`
  automatically since pools are nested subsets).
- **Non-Latin script** (Cyrillic, Georgian, Arabic, CJK, Devanagari, Thai,
  etc.) → add to `hard` only.

If your values file does not yet override `difficultyPools`, copy the full
default before adding the new code. Maintain the subset invariant:
easy ⊂ medium ⊂ hard. If it is the first required language, also set
`game.requiredLanguage` to its code.

### 5. Validate and deploy

Helm validates matching metadata and phrase arrays; it does not evaluate
linguistic quality.

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
