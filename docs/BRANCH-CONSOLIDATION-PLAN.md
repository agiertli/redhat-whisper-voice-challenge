# Consolidating onto main: stability and acceptance plan

**Status: owner-authorized promotion to main, 2026-10-23.** Cleanup is complete in
`4316d07`. The toggle and reliability fixes were developed on
`codex/consolidate-modes`, with 91 local regression checks passing. Fresh RHDP acceptance includes both modes,
rollback/upgrade, owner manual Chrome username-mode play and a live archived-main
migration with compatible model/runtime settings. Independent-owner handover and
the wider browser matrix remain open. See [recorded checks and outstanding acceptance gates](validation/CONSOLIDATION-2026-10-23.md).
After reviewing these results and limitations, the owner explicitly authorized
merging [PR #2](https://github.com/agiertli/redhat-whisper-voice-challenge/pull/2)
into `main` and deleting the temporary integration branch. Installation references
now use `main`. Following the owner's confirmation that only a few teams use the
old branch, its remote pointer was retired after verifying complete containment
in main and exact recovery from an offline Git bundle. Both recovery tags and
the local tournament branch remain. External clone/automation references must
switch to main. The wider matrix and independent-owner walkthrough remain
follow-up checks; neither promotion nor retirement claims that every planned
matrix cell passed. The original conservative retirement proposal below is
retained as planning history, superseded by this recorded decision.

## What the branch comparison establishes

At inspection, `origin/main` is `b1c38ed493e90ffdb1aa2105c84f20320e765990`.
It is the merge base and an ancestor of cleanup commit
`4316d07a70c98ce1f9253e62b0a6e56097232810`: zero main-only commits, eighteen
commits ahead on tournament-mode. Re-fetch and repeat that comparison before any
future integration; these findings do not authorize discarding new main work.

Before consolidation, main was the older standalone game: no tournament database, registration,
leaderboard or admin API. Its chart is `1.0.0`, its default UI image is `v1.1.2`,
and its model/runtime configuration differs from the tested tournament chart.
The archived tournament-mode version has persistent SQLite, signed player tokens, both
registration modes, backup/restore, current monitoring/install safeguards and the
newer model configuration. Installation now uses consolidated main instead.

Git ancestry makes an eventual integration mechanically straightforward. The
unverified work is the mode boundary, old-main upgrades and operational handover.
Do not treat an empty Git conflict list as application acceptance.

## Proposed mode contract

Add **`tournament.enabled: true`** to Helm values/schema and pass a strictly parsed
boolean as `TOURNAMENT_ENABLED`. Missing configuration defaults to true; explicit
false must remain false through every chart/helper/script path. Invalid values
must fail. Do not use a Helm `default true` expression that turns false into true.
`registration.mode: full|username` remains a separate choice, relevant when the
tournament is enabled. One chart, one source tree and one versioned image serve
both modes.

- **Enabled (default):** preserve current registration, signed player sessions,
  server-persisted scoring, leaderboard, TV and admin/backup behavior. Both full
  and username registration remain available. Preserve the current difficulty
  pools, required first language and Hard-only Swap.
- **Disabled (standalone):** open directly to difficulty selection, without asking
  for identity. Play the shared audio/challenge experience; show this game's
  accuracy/result without creating players, games, attempts or leaderboard scores.
  No registration, public tournament leaderboard or tournament TV content is
  exposed. Tournament write endpoints reject calls even when a previously issued
  player token is supplied; hiding buttons is insufficient.
- **Shared in both:** real transcription, explicit first language, difficulty
  pools, five rounds by default, 80% winning threshold, Hard-only Swap, architecture
  and mandatory GPU/AI monitoring. Do not reintroduce legacy main's Skip behavior.
  Standalone means no persistent competition; it is not a byte-for-byte restoration
  of old main's UI. Document these deliberate differences in the release notes.
- **Administration while disabled:** retain protected access to historical data,
  exports, backups and operational settings. Mode switching itself must never
  reset data. Restore/deletion remain separate explicit operator actions, never
  automatic consequences of the flag.

Keep SQLite initialization, the PVC, Secret, volume mount, resource names and
existing schema in both modes. Do not Helm-condition these resources out when
false: removing resources from a release can remove access or storage unexpectedly.
Accept the small storage overhead for a fresh standalone installation in exchange
for reversible switching. Existing personal data remains stored when disabling
collection; the flag is not a data-erasure operation.

The browser must ignore stored player tokens in standalone mode without replacing
the signing key. Define and test session behavior after re-enabling: the same
valid token should still identify an existing player. Change mode only between
games and outside booth service hours; do not promise live in-game conversion.
Mainstage/operational settings must not become accidentally dependent on a player
session when registration is bypassed.

## Work sequence and release gates

### 1. Freeze recoverable baselines

Before implementation, fetch both branches and record exact commits, chart
versions and image digests. Create/push immutable archive/release tags for both
accepted tips without overwriting an existing tag. Verify each tag can be cloned.
Preserve old published images. Record current Helm values, PVC identity, model
configuration and independent credentials privately. Take and validate an external
SQLite snapshot, including the separately protected signing secret.

Use a short-lived integration branch based on the accepted tournament tip. Keep
main and tournament-mode available until acceptance and handover are complete.
Do not publish instructions that say main supports the flag before it does.

### 2. Implement the smallest mode boundary

Add the flag to the values schema, ConfigMap/checksum, backend route guards,
template context and shared frontend flow. Make disabled mode explicit rather
than simulating a fake registered player or silently failing server calls. Keep
one challenge-selection and audio implementation, not a second copy of the old
main template. Prefer an unchanged database schema. The candidate uses one additive nullable
`games.round_count` column to preserve each new game's completion contract; old
rows remain NULL and old application versions ignore the extra column. Verify
that compatibility during upgrade, restore and rollback tests.

Update the wrapper and direct Helm documentation together. Agent prompts must
put tournament mode alongside the visible owner choices, defaulting to enabled.
Do not change the mandatory language decision, monitoring defaults, credential
preservation, pre-upgrade backup or singleton SQLite deployment constraints.

### 3. Close reliability gaps exposed during source inspection

These existing behaviors need focused failure-path tests and fixes before
calling the consolidated application reliable for external owners:

- `recordAttempt()` advances the browser's round even when saving to the server
  fails; `finishGame()` can also show a local result without a successful server
  completion. A network error must not produce a success-looking game with lost
  results. Provide a visible retry/recovery path and prevent double submissions.
- The completion endpoint does not currently require five/configured rounds;
  attempts have no configured maximum/sequential-index contract. Define the
  contract before strengthening validation so historical games remain readable.
- Player tokens are verified cryptographically without checking that the player
  still exists. A deleted player can remain visible from session storage. Return
  a clear session-expired response and recover to registration when enabled.
- Validate attempt language/phrase and malformed request types consistently;
  test empty or unknown language/phrase combinations. Current phase must not
  quietly accept an invalid phrase as a perfect empty transcription.
- The Containerfile uses an unpinned `latest` UBI base. Record and pin the accepted
  base digest for reproducible builds; retain semantic application image tags.
  Revalidate a future base refresh instead of silently changing release inputs.

These are concrete source findings, not claims that normal browser games fail.
Do not silently broaden this cleanup release into those API changes. Address them
as focused, tested changes during integration. Keep Hard Swap's current accepted
trade-off; do not turn this into an unrelated anti-cheating redesign.

### 4. Offline and container acceptance

Keep checks runnable locally; no GitHub Actions pipeline is required. Record exact
commands and results against the integration commit, not a moving branch name.
The existing seventy tests are a baseline, not completion of this matrix.

Required cases:

- Flag omitted/true/false/invalid; chart and backend defaults agree. Config changes
  roll the UI; credentials, resource names, replica count and PVC remain stable.
- Enabled/full and enabled/username: registration/resume, all three difficulties,
  five attempts, scoring, best-score ranking, TV, exports, backup/restore.
- Disabled: anonymous game works and writes no players/games/attempts; public
  tournament surfaces and write APIs are unavailable, including with old tokens.
- True -> false -> true with a populated database: identical stored rows/scores,
  valid original player token, unchanged credentials and working backup/restore.
- Historical skipped rows, empty personal fields, old players without follow_up,
  incomplete games and stored mainstage settings survive opening and restoring.
- Bad/expired/deleted-player sessions, failed/duplicate/out-of-order requests,
  inference timeout, API errors, lost completion response and retry behavior.
- Both modes in the actual built linux/amd64 container, including logos,
  architecture, templates and startup on a writable PVC-equivalent directory.

Use isolated databases and compare schema, row contents, counts, score values,
foreign keys and `PRAGMA integrity_check`, not just HTTP 200 responses. Do not
write participant data or credentials into committed fixtures.

### 5. Cluster upgrade, recovery and manual acceptance

Use disposable installations/copies, not the live event database. On SNO, one GPU
cannot host two predictors simultaneously: schedule sequential tests or obtain a
second test environment. Do not stop a working booth to stage these experiments.

Exercise fresh enabled and disabled installs; old-main -> new-main upgrade;
old-tournament -> new-main upgrade; same-version repeat upgrade; mode switches;
pod recreation; and the documented rollback. Preserve PVC and Secret identities.
Old main has no tournament DB, so its upgrade must create storage safely while
preserving its owner's existing language/model settings where compatible. Any
necessary model/runtime migration must be explicit, tested and documented; do not
assume new chart defaults preserve the old model automatically.

Use both documented installation paths. Check readiness **and** warmup success,
real-audio inference, trusted route TLS, GPU gauges and persistent AI counters.
Run the standalone external backup loop, interrupt a download, verify the last
good snapshot survives, and restore a copy into an isolated database. A complete
cluster-loss rehearsal additionally restores PVC contents and signing credentials.

Manual browser checklist, performed for enabled/full, enabled/username and
standalone, at least in current Chrome and Edge:

- Fresh browser session; correct registration or immediate game entry.
- Select microphone, speak and complete all five rounds at Easy, Medium and Hard;
  first language correct, exactly one Hard Swap, none elsewhere, no Skip.
- Inspect win/loss, time/accuracy/score, replay and return flow; compare displayed
  results with persisted results when enabled and confirm no game writes when off.
- For enabled mode, verify leaderboard, TV and authenticated admin/export; for off,
  verify those public tournament views are absent while protected history remains.
- Test reload, browser/network interruption during attempt/completion and recovery.
- Navigate architecture steps 2-3-4 both ways and resize; no layout/animation jump.
- Upgrade and switch back on; a previous player's token and score still work.

Have a technical owner from another team perform at least one installation from
a fresh clone using only the released instructions and a new owner values file.
Treat missing instructions or intervention by the original author as a failed
handover check; fix and repeat the affected path. Record screenshots and outcomes,
with no credentials or attendee PII in public reports.

### 6. Integrate and hand over main

Only after the integration gates pass, review the complete diff and current branch
protection requirements. Re-fetch/rebase or merge any new main changes and rerun
affected checks. Publish the exact accepted image/chart and validation evidence.
Integrate to main while preserving history and both recovery tags. Update README,
AGENTS/CLAUDE guidance, clone commands, example values and prompt links to main in
the same release; explain both modes and the old-main migration.

Confirm remote main contains the accepted commit, clone it afresh, and smoke-test
the published installation instructions. A protected-main PR may be used if the
repository requires review. Do not bypass repository protections to save time.

### 7. Branch-retirement decision

Merge and deletion are separate decisions. Retain tournament-mode through a
recommended **one-week acceptance period including at least one representative
team rehearsal**, with the period starting after main handover. This period is a
proposal, not a claim that a week proves safety. Extend it if external owners have
not completed their rehearsal or a serious issue is unresolved.

Delete only after all of the following are recorded:

- Main contains the accepted functionality, with tournament enabled by default.
- The matrix and manual checks passed against the published release; failure and
  recovery cases have evidence, not merely an absence of complaints.
- A second owner completed the fresh-clone handover and accepts the migration.
- External teams have updated branch references; no documented install path,
  automation or consumer known to maintainers still depends on tournament-mode.
- Archive tags and old images are accessible; branch recreation and application
  rollback have been rehearsed; no recovery resource is stored only in that branch.
- A named maintainer records acceptance of the remaining limitations.

Then remove the redundant remote branch pointer, keeping the archive tag. Deleting
that pointer does not itself alter a cluster; deployments use images, Helm values
and PVCs. It can still break `git clone --branch tournament-mode` consumers, which
is why handover and reference checks are mandatory. No finite test set establishes
zero risk; retirement is a documented acceptance of bounded, recoverable risk.

## Rollback contract

Keep the accepted prior chart/image, owner values and credentials available. Before
rollback, stop admitting new games and take a new external backup so post-upgrade
results are protected. Rehearse returning from the integration release to the
accepted tournament release against the **same database copy**, then re-verify
scores, tokens, required language and monitoring. A Helm revision alone is not a
proven rollback: it does not reverse a destructive schema migration or recover lost
rows. Avoid schema changes in this feature; if unavoidable, require a separately
reviewed forward/backward compatibility strategy before proceeding.

Do not roll a populated tournament installation back to old main as a substitute
for setting the flag false: old main cannot expose or manage those results. Do not
restore an older snapshot over newer results automatically. Restore is an explicit
incident-recovery choice with an acknowledged recovery point.

If a branch was deleted, recreate it from the verified archive tag and push it;
this recovers source references, not deployment state. Never force-push main or
reset a live database as a shortcut.

## Scheduling

This is a multi-stage change requiring implementation, failure-path work and
independent owner acceptance. It cannot responsibly be completed by treating the
remaining minutes of a cleanup session as its testing window. Estimate the
implementation after agreeing the mode contract and test environments; branch
retirement additionally depends on external-team rehearsal and acceptance.
