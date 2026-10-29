# Choose or change the admin password

The dashboard password is `tournament.adminToken`. There is no shared default:
first installation generates one unless you choose it. Ordinary upgrades preserve
the installed password. The installer prints the installed game URL, TV/leaderboard
URL, admin URL, architecture URL and game admin password only after its
verification succeeds.

## Choose a memorable password

For an agent, the owner settings may contain a literal value:

```text
Admin password: whisper@r3dh4t!
```

The agent writes it to a mode-600 temporary file, passes `--admin-password-file`,
and removes the temporary file afterwards. A literal password remains in the chat
history. You may instead provide an existing private file path.

For a terminal/script installation, create the private file without a trailing
newline. This prompt avoids putting the password in shell history:

```bash
umask 077
read -r -s -p 'Choose admin password: ' ADMIN_PASSWORD; printf '\n'
printf '%s' "$ADMIN_PASSWORD" > admin-token
unset ADMIN_PASSWORD
```

Use at least 12 characters. Entering `whisper@r3dh4t!` satisfies the chart's minimum.
The local `admin-token` filename is ignored by Git. Do not put the password in a
versioned values file or run commands with shell tracing.

## Install or intentionally change the password

The same file option works for first installation and intentional password changes:

```bash
./deploy.sh --values values-conference.yaml --namespace whisper \
  --admin-password-file ./admin-token --free-rhdp-gpu --preflight
./deploy.sh --values values-conference.yaml --namespace whisper \
  --admin-password-file ./admin-token --free-rhdp-gpu
```

For direct Helm, add `--set-file tournament.adminToken=./admin-token` to the
[installation/upgrade command](../HELM-INSTALLATION.md). Follow its pre-upgrade
backup and post-upgrade verification steps. On ordinary upgrades, omit the password
override to keep the installed value. Choosing a new password restarts the UI;
coordinate a brief interruption and update the backup laptop's credential file.
Changing only the admin password does not rotate the player signing key.

## Retrieve current access details

```bash
./scripts/show-access.sh whisper
```

This intentionally prints the current password with the game/admin URLs. Keep the
terminal and transcript private. The helper itself does not install or verify the
application; normal installation calls it after successful verification.

For the backup laptop, save the actual installed password privately:

```bash
umask 077
oc get secret whisper-tournament-secret -n whisper \
  -o 'go-template={{index .data "ADMIN_TOKEN" | base64decode}}' > admin-token
```

Transfer that protected file using your normal secure method. Do not transfer
cluster-admin credentials to the conference backup laptop.
