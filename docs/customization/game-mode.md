# Tournament or anonymous standalone play

Available on **`main`**, using the tested **v2.12.0-rc.4** image. The older
`tournament-mode` release v2.11.2 does not have this toggle. That branch remains
temporarily available for external-team handover; see the
[acceptance and retirement plan](../BRANCH-CONSOLIDATION-PLAN.md).

The same image and Helm chart support both modes. Tournament is the default:

```yaml
tournament:
  enabled: true
registration:
  mode: username  # full or username; used only when tournament is enabled
game:
  requiredLanguage: de  # owner chooses explicitly in either mode
```

To run without registration or persistent competition, change only:

```yaml
tournament:
  enabled: false
```

Use YAML booleans `true`/`false`, not quoted strings or yes/no. Reuse the same
owner values file with the [installer](../INSTALLATION.md) or
[direct Helm upgrade procedure](../HELM-INSTALLATION.md#6-upgrade-directly-with-helm).
No rebuild is needed to change the mode. The UI restarts, so change modes between
games, outside an active booth session. Monitoring is required in both modes.

## What changes

With tournament enabled, full or username registration, server scoring, persistent
leaderboards, `/tv` and authenticated administration work as before.

With tournament disabled, `/` opens directly to difficulty selection. There is no
registration form or public leaderboard; `/tv`, the public leaderboard API and
player/game APIs return 404, even with a previously valid player token. Anonymous
games display their own accuracy and win/loss without saving player/game/attempt
rows. The required first language, difficulty pools, five rounds by default,
80% winning threshold and one Hard-only Swap remain. No Skip is reintroduced.

Authenticated `/admin`, exports, backups and operational settings remain available
for managing historical data. Standalone play does not create tournament results
for the backup script to save.

## Switching back preserves the tournament

The PVC, database, Secret and credentials stay present in both modes. Disabling
tournament does not delete players, remove previously collected personal data,
reset scores or rotate player signing keys. The browser ignores its stored player
session while disabled; re-enabling validates the same token against the existing
player. A deleted player must register again.

A backup is still required before upgrading or switching. Keep the external
conference backup loop for any installation containing results you must preserve.
Do not uninstall or remove storage to switch modes.

## Upgrade compatibility and saving results

The candidate adds a nullable `games.round_count` column. New games store their
required number of rounds when created, so a later configuration change does not
change an existing game's completion requirement. Older rows retain NULL and
historical completion/scoring behavior, including skipped attempts. No existing
scores are recalculated. Restoring an older snapshot runs the same additive
migration. Older tournament releases ignore the extra column; rollback must still
be verified with your release and database copy before an event.

New games require every configured round in order before server completion. An
identical attempt/completion retry returns the saved result without another row
or a new score/time; conflicting attempt content returns 409.

If saving fails, the UI keeps the pending round or final result, blocks a new game
and shows **Retry save**. Keep the page open and restore connectivity before
retrying. A local result is never presented as a saved tournament result. Reloading
or closing the tab with an unconfirmed save prompts a browser warning; this is not
an offline queue or a promise to recover unsent data after a laptop/browser crash.
Previously confirmed results remain in the database and backups.

Restore validates SQLite integrity, required schema and foreign-key references before
replacing the target database. Rejected uploads leave existing results untouched.
Use a known backup from your event and pause game admission before an intentional
restore; schema validation does not establish that you selected the right event.
