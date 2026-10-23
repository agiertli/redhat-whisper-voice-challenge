# Choose registration mode

Use the same chart and UI image for both modes. No separate branch is needed.
Username-only mode requires image `quay.io/agiertli/whisper-ui:v2.11.0` or newer.

Set this in your non-secret `values-conference.yaml`:

```yaml
registration:
  mode: "username"
game:
  requiredLanguage: "de"
```

- **`full` (default):** New Player / Returning Player tabs. A new player provides
  a nickname, full name and email. Returning players use their nickname.
- **`username`:** one form, one username field, one Join Tournament button. A new
  username creates a player; the exact existing username resumes that player.
  Enter submits the form. No extra returning-player tab or name/email fields.

Usernames are public on the leaderboard, case-sensitive, 2–20 characters, using
ASCII letters, numbers, underscores or hyphens. Returning by username is the
accepted behavior for this game; usernames are not identity verification.

In username mode the backend ignores any submitted name/email fields and creates
players with empty name/email columns. `/register` leads to the same one-field
screen. Player IDs, game tokens, scores, admin exports and backups work unchanged.

## Apply or switch mode

Save the choice alongside the first language and difficulty settings; reuse the
same file on every upgrade. After reviewing the target cluster and scheduling a
brief UI interruption:

```bash
./deploy.sh --values values-conference.yaml --namespace whisper --free-rhdp-gpu --preflight
./deploy.sh --values values-conference.yaml --namespace whisper --free-rhdp-gpu
```

The installer backs up before changing an existing installation. Direct Helm
owners use the [backup/upgrade sequence](../HELM-INSTALLATION.md#6-upgrade-directly-with-helm)
with the same file. An env/ConfigMap change rolls the UI, with no rebuild when
`v2.11.0` is already installed.

Switching modes retains existing players, scores and signing credentials. It does
not erase personal data collected earlier in full mode. Full-mode returning login
also works for players created in username mode. Avoid changing mode mid-game;
verify a new player, returning player, a completed game and the admin export before
opening the booth.
