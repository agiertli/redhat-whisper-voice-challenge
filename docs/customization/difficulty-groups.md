# Configure difficulty groups

Change which languages belong to Easy, Medium and Hard in your own
`values-conference.yaml`. This is independent of full versus username-only
registration. Configuration changes need a Helm upgrade, not an image rebuild.

## Default groups

The authoritative defaults are `difficultyPools` in
[helm/whisper/values.yaml](../../helm/whisper/values.yaml). They are nested:
Easy has 11 languages, Medium has 21 and Hard has 29.

- **Easy:** Slovak (`sk`), Czech (`cs`), English (`en`), Polish (`pl`), Hungarian
  (`hu`), German (`de`), Spanish (`es`), French (`fr`), Croatian (`hr`), Serbian
  (`sr`), Slovenian (`sl`).
- **Medium:** all Easy languages, plus Turkish (`tr`), Italian (`it`), Portuguese
  (`pt`), Dutch (`nl`), Swedish (`sv`), Romanian (`ro`), Ukrainian (`uk`), Finnish
  (`fi`), Icelandic (`is`), Norwegian (`no`).
- **Hard:** all Medium languages, plus Bulgarian (`bg`), Georgian (`ka`), Japanese
  (`ja`), Korean (`ko`), Arabic (`ar`), Chinese (`zh`), Thai (`th`), Hindi (`hi`).

The number of languages is a pool size, not a number of game rounds. The default
is five rounds per game, and the owner explicitly chooses the first language.

## How the game chooses languages

The first round uses `game.requiredLanguage` at every difficulty, even if that
language is absent from the selected pool. For the later rounds the browser:

- **Easy:** randomly chooses from Easy, preferring languages not already used.
- **Medium:** draws from Medium and tries to include at least three languages
  belonging to Medium but not Easy across the five-round game.
- **Hard:** draws from Hard and tries to include at least two languages belonging
  to Hard but not Medium. It also aims for two to three languages from the
  application's non-Latin set: `bg`, `ka`, `ja`, `ko`, `ar`, `zh`, `th`, `hi`, `uk`.
  Ukrainian is already in the default Medium group and counts toward this target.

The required first language counts toward these targets when applicable. If a
filtered candidate list is empty, selection falls back to the full chosen pool,
which may repeat languages and relax these targets. Phrase selection is random
within the selected language. Default five-round games are the tested baseline;
these target counts do not scale automatically with `game.challengeCount`.

Hard also offers one **Swap**: it replaces the current challenge without recording
an attempt and tries to retain the same language-mix targets. This is separate
from the API's limit of one skipped attempt per game.

## Override the groups

Add the following to your existing values file. `difficultyPools` is a **JSON
string inside a YAML block**; keep the `|`, JSON quotes and square brackets.
Specify all three groups because this string replaces the whole default value.

```yaml
difficultyPools: |
  {
    "easy": ["cs", "sk", "en", "de", "pl"],
    "medium": ["cs", "sk", "en", "de", "pl", "fr", "es", "it", "uk"],
    "hard": ["cs", "sk", "en", "de", "pl", "fr", "es", "it", "uk", "bg", "ka", "ja", "ko", "ar", "zh", "th", "hi"]
  }
```

Keep `easy` a subset of `medium`, and `medium` a subset of `hard`. Provide at least
three distinct Medium-only languages and at least two Hard-only languages, with
enough non-Latin choices for Hard's target. Keep the required first language in
all groups for an intuitive setup. Avoid duplicate codes.

Use codes already present in both `languageInfo` and
[helm/whisper/challenges.json](../../helm/whisper/challenges.json). To introduce a
new language, follow [languages and phrases](languages-and-phrases.md).
Helm checks JSON, nonempty groups and matching language metadata/phrases; it does
not guarantee that your custom pool can satisfy every selection target.

## Apply and verify

Schedule the UI restart outside active games. Keep all existing owner choices in
the same file and take the required backup before upgrading:

```bash
helm lint helm/whisper -f values-conference.yaml
./deploy.sh --values values-conference.yaml --namespace whisper --free-rhdp-gpu
```

For the direct Helm path, use its documented
[backup and upgrade sequence](../HELM-INSTALLATION.md#6-upgrade-directly-with-helm)
with the same file. Then play Easy, Medium and Hard, checking the first language,
subsequent languages, phrases and Hard swap. Test several games because selection
is random. If pools were intentionally too small, expect repeats/fallbacks.

This config changes language membership, not phrase complexity, score multipliers,
win thresholds, non-Latin target counts or the three difficulty names. Those rules
are currently application code. UI difficulty descriptions use the original
examples; they are not generated from custom pools. See
[tournament scoring](tournament-scoring.md) for the exact scoring behavior.
