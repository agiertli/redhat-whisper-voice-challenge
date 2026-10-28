---
name: whisper-operations
description: "Primary interface for the Whisper Voice Challenge conference game: install, upgrade, customize, diagnose, back up, and verify booth readiness on OpenShift. Covers all documented common tasks. Not for generic Whisper transcription, unrelated AI deployments, or ordinary application development."
---

# Whisper operations

Help the technical owner operate the conference game with evidence that it works
and that tournament data is protected. Use the current repository as the source
of truth, rather than prior chat memory or remembered cluster state.

## Start here

1. Resolve this skill folder's symlink to its real filesystem location before
   following relative links. The canonical folder is inside a Whisper checkout
   at `.agents/skills/whisper-operations`; three parent directories above that
   real folder is the repository root. This works when invoked from another
   directory through a personal/global skill link. Execute repository commands
   from that root, not from the chat's starting directory. If the owner names a
   different Whisper checkout, use its current instructions and runbooks instead.
   If the checkout cannot be accessed, ask for its location; do not operate on an
   unrelated project or claim that cluster checks ran.
2. Read [AGENTS.md](../../../AGENTS.md) and
   [the operations runbook](../../../docs/INSTALLATION.md). They define the safety
   contract, tested environment, commands and acceptance criteria. Follow their
   current contents; do not pin a second set of release versions here.
3. Select the workflow matching the request from the sections below. A readiness
   check or diagnosis does not authorize an upgrade, restoration, credential
   rotation or score reset. A customization task does not authorize unrelated
   changes.
4. For cluster work, discover the current identity, server and context using `oc`.
   Confirm the intended target from the request and current evidence. Reuse the
   installer's context protection; keep diagnostics on that same context. Never
   use `now.env` or old conversations as cluster credentials.
5. Ask for missing owner decisions early while continuing read-only discovery.
   Reuse choices and authorization already supplied in this session.

## Prepare or upgrade a conference

Read [the agent installation procedure](../../../docs/AGENT-INSTALLATION.md).
Use its owner settings and copyable prompt as the input contract.

- Establish fresh install versus upgrade from actual release and storage state.
  Reuse the existing venue values file and preserve choices on upgrades. The
  owner selects the first language explicitly; a country alone is insufficient.
- Follow the documented `deploy.sh` procedure on `main`: read-only preflight,
  then the same inputs without `--preflight`. Use direct Helm only when explicitly
  requested. Do not create another deployment mechanism.
- The installer owns backup-protected upgrades, monitoring setup, rollout and
  internal audio verification. Investigate failed gates instead of bypassing
  them. Stopping the named RHDP demo Llama needs owner authorization; unrelated
  GPU workloads are outside that authorization.
- Use [the customization index](../../../docs/CUSTOMIZATION.md) for the relevant
  configuration task. Prefer Helm/env changes over rebuilding images.
- Complete the readiness workflow before declaring the booth ready. After
  successful installation verification, use `scripts/show-access.sh` for the
  requested game URL, admin URL and installed admin password handoff. Never
  disclose the player signing key.

## Customize the game

Each task below corresponds to a dedicated guide in
[the customization index](../../../docs/CUSTOMIZATION.md). Read the relevant
guide before making changes. All configuration changes use the venue values file
and a Helm upgrade — no image rebuild required unless application source changes.

### Change language or phrases

Guide: [languages-and-phrases.md](../../../docs/customization/languages-and-phrases.md)

- Set the first required challenge language in `values-conference.yaml`
  (`game.requiredLanguage`). The owner chooses explicitly; never infer from
  locale. Normalize names/typos to supported codes (`German` → `de`).
- Edit existing challenge phrases in `helm/whisper/challenges.json`.

### Add a new language (end-to-end)

When the owner says "add language X", execute this complete workflow. Do not
skip steps or ask the owner to do them manually.

**Step 0 — Validate Whisper support.** The deployed model is
`openai/whisper-large-v3`. Before any file changes, confirm the requested
language is in Whisper large-v3's supported set (99 languages). Use the
canonical list from the Whisper documentation / model card. If the language
is NOT supported, stop immediately and tell the owner: the language cannot
be added because Whisper will not transcribe it. Do not proceed to phrase
generation. If the language is supported but known to have poor accuracy
in Whisper (e.g., low-resource languages with <50% WER on Fleurs), warn
the owner that players may struggle to reach the 80% win threshold.

**Step 1 — Normalize the language code.** Map the owner's input to the
correct ISO 639-1 two-letter code. Handle common variants: `German` → `de`,
`Mandarin`/`Chinese` → `zh`, `Brazilian Portuguese` → `pt`, `Farsi` → `fa`.
Reject ambiguous inputs and ask for clarification.

**Step 2 — Check for duplicates.** Read `helm/whisper/challenges.json` and
check if the language code already exists. If it does, inform the owner and
offer to add more phrases instead. Do not create duplicate entries.

**Step 3 — Generate challenge phrases.** Generate 9 phrases matching the
existing style in `challenges.json`:
- Theme: Red Hat, open source, cloud, AI, Kubernetes, containers, DevOps,
  automation, security — the same tech topics used in every other language.
- Length: 4–8 words, natural spoken sentences, no abbreviations or jargon
  that a native speaker would not say aloud.
- Ensure correct grammar, diacritics and script for the target language.
- Do NOT transliterate; use the language's native script (Cyrillic, Georgian,
  Arabic, CJK, Devanagari, Thai, etc. as appropriate).
- Show the generated phrases to the owner for approval before writing them.

**Step 4 — Write the phrases.** Add the new language code and its phrase
array to `helm/whisper/challenges.json`, preserving existing entries and
valid JSON formatting.

**Step 5 — Add language metadata.** Determine the correct flag emoji and
English display name. Add the entry to `languageInfo` in
`values-conference.yaml`. If the owner has no custom `languageInfo` override
yet, copy the full default object from `helm/whisper/values.yaml` first,
then add the new entry — overriding `languageInfo` replaces the whole object.

**Step 6 — Assign to a difficulty pool.** Use these rules:
- Latin script → add to the `easy` pool (and therefore also `medium` and
  `hard`, since pools are nested subsets).
- Non-Latin script (Cyrillic, Georgian, Arabic, CJK, Devanagari, Thai,
  Hebrew, Armenian, etc.) → add to `hard` only.
- If the owner specifies a different pool, use their choice.
- If `values-conference.yaml` does not yet override `difficultyPools`, copy
  the full default from `helm/whisper/values.yaml` before modifying it.
- Maintain the subset invariant: easy ⊂ medium ⊂ hard.

**Step 7 — Validate locally.** Run `helm lint helm/whisper -f values-conference.yaml`
to confirm Helm validation passes (phrases exist, languageInfo matches,
pools are consistent). Fix any failures before proceeding.

**Step 8 — Deploy and verify.** Deploy using `./deploy.sh` or Helm upgrade
as appropriate for the session context. After deployment, verify the language
appears in the game UI and advise the owner to perform a real speech test
in that language to confirm transcription quality.

### Configure difficulty groups

Guide: [difficulty-groups.md](../../../docs/customization/difficulty-groups.md)

- View the default Easy/Medium/Hard language pools (11/21/29 languages).
- Override difficulty pools in `values-conference.yaml` with a custom JSON
  string under `game.difficultyGroups`.
- Understand selection logic: required first language, per-difficulty language
  targets, non-Latin targets reserved for Hard.

### Change game mode

Guide: [game-mode.md](../../../docs/customization/game-mode.md)

- Tournament mode (`tournament.enabled: true`) is the default. Set `false` for
  anonymous standalone play (no registration, no leaderboard, no `/tv`).
- Switching modes preserves players, scores, credentials and PVC. It does not
  delete previously collected data.

### Change registration mode

Guide: [registration.md](../../../docs/customization/registration.md)

- Choose `registration.mode`: `full` (nickname + name + email) or `username`
  (single field to join or resume). Applies only when tournament is enabled.
- Switching modes preserves existing players/scores/credentials. Username-only
  mode ignores submitted name/email fields server-side.

### Choose or change the admin password

Guide: [admin-password.md](../../../docs/customization/admin-password.md)

- Choose a memorable password at install time via literal value or private file.
  For a literal value, create a mode-600 temporary file, pass
  `--admin-password-file`, then remove the file.
- Intentionally change/rotate the password on an existing deployment by
  supplying a new `--admin-password-file`. Omit on ordinary upgrades to
  preserve the installed password.
- Retrieve the current password and URLs via `scripts/show-access.sh`.

### Understand tournament scoring

Guide: [tournament-scoring.md](../../../docs/customization/tournament-scoring.md)

- Accuracy: Levenshtein similarity on normalized text, 80% win threshold.
- Final score: difficulty multiplier × average accuracy × 100 × speed bonus.
- Speed bonus: 1.2 at 0s → 1.0 at 120s → 0.8 at 240s+.
- Hard-only Swap replaces the challenge without recording an attempt; clock
  keeps running.
- Leaderboard ranks by best single score per player, not summed.

### Run backups and rehearse recovery

Guide: [backups-and-restore.md](../../../docs/customization/backups-and-restore.md)

- Start the standalone laptop backup loop: one-shot first, then `--loop`.
  Needs only Bash/curl on macOS or Linux. Verify the first snapshot before
  admitting players.
- Configure interval (`INTERVAL`, default 300s) and retention
  (`MAX_BACKUPS`, default 288).
- Rehearse a restore drill safely using `tests/live_restore_check.py` against
  a snapshot on stdin — it never touches the live database.
- Pause the laptop loop during planned upgrades; resume afterwards.
- Incident recovery: stop admitting players, preserve existing DB/PVC and
  external backups, select the correct snapshot, restore via `/admin`, verify.

### Upgrade from an older installation

Guide: [upgrading-existing-installations.md](../../../docs/customization/upgrading-existing-installations.md)

- Migrate from the retired `tournament-mode` branch to consolidated `main`.
- Migrate from the older stateless main to the consolidated candidate (add
  `tournament.enabled: false` to keep standalone behavior).
- Remove obsolete settings: `clusterDomain`, `supportedLanguages`,
  `game.winThreshold`, old image tags.
- Verify: warmup, inference, monitoring, language/mode, browser game,
  historical scores/tokens, backup/restore.

## Diagnose an incident

Use the troubleshooting section of the operations runbook. Establish whether
players are active, what fails, and what changed recently. Do not delay safe
read-only evidence collection while waiting for an answer.

Narrow the fault using the smallest useful checks:

- **Browser/audio:** trusted HTTPS, microphone permissions, device selection,
  capture and upload errors. Internal audio tests cannot prove browser capture.
- **Route/UI:** external reachability, route/service/endpoints, UI readiness and
  scoped logs. Compare installed configuration with intended venue values.
- **Inference/GPU:** warmup and predictor logs, pod events, GPU allocation,
  resource pressure and image pulls. Consult the tested runtime configuration
  before changing model flags or resource settings.
- **Storage/tournament:** PVC and database accessibility, registration mode,
  leaderboard behavior and the latest external backup. Preserve existing data.
- **Monitoring:** DCGM gauges, ServiceMonitor, user workload monitoring and
  persistent AI counters after real requests and a scrape interval.

State the evidence and working hypothesis before choosing a repair. Make a
scoped repair within the request, then verify the original symptom. Do not repeat
failed mutations without new evidence. If repair requires destructive recovery,
broader disruption or an owner decision required by the runbook, report evidence
and request that decision before proceeding. Never uninstall, delete the PVC,
reset results or rotate credentials as a retry.

## Check booth readiness

Use the live acceptance checklist in the operations runbook. Record each relevant
item as verified, failed or untested, with evidence and the time of the check.

- Verify installed versions and venue settings, including first language and
  tournament/registration modes. Test the surfaces applicable to the selected
  mode; standalone play intentionally has no public tournament.
- Use `scripts/verify-install.sh` with explicit namespace, language, registration
  mode and tournament flag from venue configuration. Inspect its current argument
  contract first. It sends real fixture audio and increases AI counters without
  creating tournament players. For strictly observational requests, report this
  active check as pending rather than silently sending inference traffic.
- Verify browser HTTPS, microphone capture and a complete game. In tournament
  mode, include registration/resume, score persistence, leaderboard, TV and admin.
  If browser/device access is unavailable, identify the exact owner checks still
  needed. Do not infer success from Ready pods or API checks. Use an owner-approved
  test player for game verification on an active event.
- Verify the first external laptop snapshot and running backup loop before
  admitting players. Check restore-drill evidence against
  [the backup/recovery guide](../../../docs/customization/backups-and-restore.md).
  An isolated application restore test is not a full cluster-loss rehearsal.
  Never rehearse restore against the live event database.

## Report the outcome

Lead with ready, blocked or partially verified, and the concrete reason. Include
cluster/namespace, relevant installed versions, venue choices, evidence and
remaining owner actions. Distinguish local, cluster, browser and restore checks.
Keep diagnostics secret-free; the installation admin-password handoff is the
specific documented exception. Describe a custom conference demo within the
repository's tested scope, not a verified Red Hat supported solution.
