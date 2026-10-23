# Consolidation candidate acceptance — 2026-10-23

**Owner-authorized promotion to main.** Work was developed on
`codex/consolidate-modes`. After the checks recorded below, the owner explicitly
authorized merging [PR #2](https://github.com/agiertli/redhat-whisper-voice-challenge/pull/2)
and removing that temporary branch. Installation now uses `main`; the tested
release-candidate image/chart version labels are retained. The temporary and
tournament remote branches are retired; main contains their history. Both recovery
tags remain, and the tournament tip was independently restored from a complete
offline Git bundle. External teams must switch branch references to main. The wider browser
matrix and independent-owner walkthrough remain follow-up checks;
they are not represented as completed.

## Scope and recoverability

One chart/image now supports `tournament.enabled: true` (default) and anonymous
standalone play with `false`. Registration remains independently configurable as
`full` or `username`. Switching modes retains the PVC, Secret and historical data.
Disabled tournament routes reject calls, including previously valid player tokens.
Protected administration and backup remain available in both modes.

The only schema addition is nullable `games.round_count`. New games require all
their configured rounds before completion; legacy rows retain their historical
rules and scores. Save retries are idempotent, conflicting retries fail, and the
browser retains pending saves rather than silently advancing. Restore validates
the SQLite schema/integrity before replacing data. Historical scores are not
recomputed.

Recovery tags were pushed and cloned independently:

- `archive/main-before-consolidation-20261023`: `b1c38ed493e90ffdb1aa2105c84f20320e765990`.
- `archive/tournament-before-consolidation-20261023`: `8e0292432afdb85398ee4fe9a03978171950d67d`.

## Local checks

91 automated regression tests passed on macOS, Python 3.14.2, Bash 3.2.57 and
Helm 3.15.4. Tests cover both modes, explicit false/default/invalid configuration,
registration, endpoint guards, additive legacy migration, scoring, concurrent
attempt retries, completion retries, malformed requests, restore rejection and
rendered frontend save/session transitions. Node's built-in VM exercises the
actual rendered JavaScript functions; these are not microphone/browser tests.
Focused restore tests also reject corrupt, truncated and incompatible snapshots.
Helm lint, shell syntax, ShellCheck 0.10.0 and architecture JavaScript syntax pass.
No GitHub Actions workflow was introduced.

The additional legacy-installer cases verify private Helm-state capture for the
known stateless main release, read-only legacy preflight, and refusal to treat an
unknown/stateful installation with a missing Secret as a safe migration.

## Fresh RHDP cluster checks

Environment: OpenShift 4.20.42, RHOAI 3.5.2, NVIDIA GPU Operator 25.3.4, single
node and NVIDIA L4. German (`de`), username registration, tournament enabled is the
final intended owner configuration. Cluster credentials and snapshots remain
private outside Git. The previously used cluster was not modified.

Completed checks during candidate iteration:

- Standard wrapper installation on the fresh cluster; authorized bundled Llama
  scaled to zero, monitoring enabled and verified, model warmup succeeded.
- Real WAV transcription through UI → model returned “That's one small step for
  man, one giant leap for mankind.” DCGM GPU gauges and persistent AI counters
  were verified. This proves inference independently of browser capture.
- Standard upgrade to standalone: public tournament surfaces return 404, no
  registration form, protected history/backup works; all database rows unchanged.
- Direct Helm upgrade to tournament/full registration: required fields and
  resuming an existing username player verified.
- Three five-round API games across Easy, Medium and Hard: 80% average wins,
  invalid/Skip/out-of-order requests fail, concurrent identical retries do not
  duplicate attempts, repeated completion returns the persisted result.
- Rollback with the independently cloned accepted `v2.11.2` release, followed by
  upgrade back to the candidate: PVC/Secret identity, credentials, existing token,
  historical scores and baseline player/game/attempt/settings rows preserved.
  The old release could create a legacy game with the added column present.
- Published restore endpoint exercised in a separate process against an isolated
  temporary database: a legacy-schema snapshot migrates, counts/scores/integrity
  match, and an incompatible restore fails without changing that temporary data.
  The running tournament database is not used as a restore target.
- A fresh Git clone and clean environment (no `now.env`, virtualenv or prior
  repository memory) completed standard preflight and repeat upgrade at `77910c5`.
- Browser HTTPS, the single username form, resume, required German first round,
  one Hard Swap and its absence on Easy/Medium verified.

Browser captures: [standalone play](integration-standalone.png) and
[tournament Hard Swap](integration-tournament.png).

Two earlier internal smoke executions encountered API exec TLS bad-record-MAC
transport errors after deployment. Verification correctly failed rather than
claiming success. The helper now streams its input and retries only recognized
transient transport failures up to three times; application assertions are not
retried. Live verification and the clean-clone repeat subsequently passed with
certificate verification enabled.

Final published candidate: chart `2.0.0-rc.7`, UI `v2.12.0-rc.4`, digest
`sha256:73f18b0c4c7f4ce19560b68438baf4f1c855eae18ab089375db7355399fdd13f`.
The final static architecture labels now match the 80% win rule and current VAD
constants; earlier mode/rollback checks used preceding candidate tags.

Final wrapper upgrade completed at Helm revision **8**: warmup hook `Succeeded`,
real-audio transcription and DCGM/persistent AI checks passed (12 requests and
121 tokens at verification). Published Python, game template and architecture
asset SHA-256 hashes matched the working source. PVC identity and both Secret
credential values matched the original fresh-install baseline. Both sets of
baseline scores, tokens and rows remained unchanged before cleanup.

At 1280×720 the architecture SVG retained identical bounds on all eight forward
steps and reverse navigation through steps 7–2: x=33, y=160, width=1214,
height=506. A deleted disposable player's stale browser session returned to the
single-field registration screen after the next game-start request. Only the
three identified acceptance players and their games were removed afterward;
unrelated records were compared and preserved. At that point the fresh cluster
had no players; the owner subsequently added the manual acceptance result below.

### Owner's subsequent manual Chrome acceptance

After automated fixture cleanup, the owner completed the requested manual
checklist and reported no issues. Their screenshots show a complete five-round
Hard game with microphone capture and a German first challenge, followed by the
same **128.3 points / 58.6%** result in the game, TV leaderboard and authenticated
admin. The checklist also covered the single username form, one Hard Swap,
refresh/resume, and no Swap on Easy/Medium. Treat the latter checks as owner
confirmation; the three screenshots alone do not show every interaction.

The owner's result was independently verified in an external SQLite snapshot
before the migration rehearsal. It is retained and is not a disposable fixture.
The fresh cluster therefore now contains the owner's player/result. Screenshots
containing unrelated browser tabs/account details are not copied into Git.

One external backup downloader ran with `env -i`, `PATH=/usr/bin:/bin` and
macOS Bash 3.2: no Python, `oc`, virtualenv or repository configuration. The default
300-second loop saved snapshots at **18:43:39Z** and **18:48:41Z**, sequentially.
Both passed script format/length checks and an independent SQLite integrity check;
files were mode 600. The test loop was stopped after the second snapshot. Before
admitting real players, the owner must start their conference laptop's backup
loop and keep that laptop awake; no ongoing backup service is claimed here.

![Final candidate ready for username registration](integration-final.png)

![Final architecture labels and layout](integration-architecture.png)

## Live migration from archived main

The archived chart `1.0.0` and published UI `v1.1.2` were installed in the separate
`whisper-main-migration` namespace. The old image digest was
`sha256:d7a62b6fa58bc820524bd6730c7b903d96ff68983010e6208891bbf3a6721344`;
its Python and game template hashes matched the archived main source.

Both the old and new configurations explicitly selected the already validated
RHOAI 3-compatible modelcar `registry.redhat.io/rhai/modelcar-openai-whisper-large-v3:3.0`
and runtime `registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.2.4`. This is a migration
of the old application/chart with compatible owner settings, not validation of
the obsolete quantized-model/runtime defaults or a RHOAI 2 operator upgrade.

Old main passed trusted HTTPS, the configured German language and real WAV
inference. The standard wrapper then performed read-only preflight and upgrade
to the consolidated chart with `tournament.enabled: false`, using reviewed values
without old UI-image overrides. This exposed and fixed an installer gap: old main
has no tournament backup API/Secret. Strict legacy detection now saves complete
Helm values, manifest and Deployment privately before this first migration;
unknown/stateful releases with missing credentials still fail safely.

The consolidated release reached Helm revision **2** with model warmup, real-audio
inference, DCGM and persistent AI checks passing. Deployment, Service and Route
UIDs remained identical, German was retained, the model API moved to the internal
service, a new PVC became Bound, and new independent credentials were generated.
No tournament data existed in this stateless source installation.

Two preliminary runs stopped on test-harness mistakes (upload field and SSE
chunk assembly), not application failures. The recovery guard restored the owner
installation after each; the corrected run passed. The separate rehearsal
installation is retained with UI/model scaled to zero, preserving its Helm state
and PVC. The single GPU is returned to the owner's original namespace.

After recovery, the owner's original installation again passed real WAV
inference and GPU/persistent AI monitoring. Every backed-up owner
player/game/attempt/settings row matched, the 128.3-point result remained,
username resume worked and snapshot integrity passed. Fresh-install PVC/Secret
UIDs and both credentials remained unchanged; published source hashes still
matched. No backup was restored over the owner's running data.

## Remaining acceptance gates

1. Owner manual Chrome acceptance for username-mode tournament play passed as
   recorded above. The broader planned Chrome/Edge, full-registration and
   standalone spoken-game matrix is not completely exercised. Agent-side real
   WAV/API checks remain separate evidence from the owner's browser game.
2. Archived-main migration passed with the explicitly compatible configuration
   above. Owners using other legacy models/runtimes still need to validate their
   intended configuration; the obsolete defaults remain outside this evidence.
   Follow [the migration guide](../customization/upgrading-existing-installations.md).
3. Have an independent technical owner follow the documentation without this
   chat, check their intended language/registration choice and rehearse recovery.
4. Promotion updates installation references to `main` and verifies the merged
   source from a fresh clone. The fresh clone passed installer help, Helm lint,
   audio-fixture presence and rendering both mode configurations using only
   standard-library Python. Keep recovery tags/images and the verified local
   bundle through external-team acceptance.

No finite test suite establishes zero risk. Promotion is the owner's acceptance
of the recorded scope and limitations. The retired tournament branch can be
recreated at its exact original tip; that does not remove the need to update
external branch references or complete the outstanding handover checks.
