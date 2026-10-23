# Installation through an AI agent

Use this procedure with Claude Code, Codex, or another terminal-capable agent.
The agent needs the repository and authenticated cluster access; it needs no prior
conversation, personal memory, `now.env`, image build engine or registry push access.
[AGENTS.md](../AGENTS.md) is the shared entry point; [CLAUDE.md](../CLAUDE.md)
points Claude to the same instructions. The execution path is `deploy.sh`.

## Before starting

Order the RHDP OpenShift AI 3 GPU environment and obtain its `oc login` command.
On the installer workstation provide Git (for cloning), Bash, oc, Helm 3, curl,
and Python 3.9+ (no pip packages for installation). Log in as cluster-admin.
Check the current server; do not hand an agent credentials from an expired cluster.

```bash
git clone --branch tournament-mode --single-branch \
  https://github.com/agiertli/redhat-whisper-voice-challenge.git
cd redhat-whisper-voice-challenge
oc whoami
oc whoami --show-server
```

Tell the agent the registration mode, namespace, required **first** language, and
whether it may stop the bundled RHDP Llama. The language is an owner decision;
German is `de`, Czech `cs`, Slovak `sk`, English `en`. Later rounds remain multilingual.

## Copyable prompt

**Edit the five lines under OWNER SETTINGS, then copy the entire block into your
agent.** Replace every `<...>` placeholder. Language examples: `de` = German,
`cs` = Czech, `sk` = Slovak, `en` = English. Later rounds remain multilingual.

For a chosen admin password, either use a private file as described in
[Choose the admin password](customization/admin-password.md), or enter it directly (for example `Admin password: whisper@r3dh4t!`)
or provide the private file path. A directly entered password remains in chat history.

```text
OWNER SETTINGS — EDIT THESE FIVE LINES
First required language: <language name or code, e.g. German or de>
Registration mode: <full or username>
Namespace: whisper
May stop bundled RHDP Llama to free the GPU: <yes or no>
Admin password: <chosen password, private file path, or "generate on first install; preserve on upgrade">

INSTALLATION INSTRUCTIONS — KEEP THESE
Read AGENTS.md and docs/INSTALLATION.md on the tournament-mode branch.
You are logged into the intended RHDP OpenShift AI 3 SNO cluster as cluster-admin.
Install the Whisper tournament game using the OWNER SETTINGS above.

- Use the published image and repository installer without rebuilding.
- Normalize language names and obvious spelling mistakes (e.g. Germand -> de)
  to a supported language code; confirm only if the intended language is ambiguous.
- Read docs/CUSTOMIZATION.md for task-specific guides when an owner requests
  custom difficulty groups, phrases, scoring details or other configuration.
- Save non-secret owner choices in values-conference.yaml and reuse that file.
  Set registration.mode to the selected full or username value. Full collects
  nickname, name and email; username presents one field to join or resume.
- If a literal admin password is supplied, write it to a private temporary file
  with mode 600, use --admin-password-file, and remove the temporary file afterwards.
  Keep it out of shell tracing, command arguments and the versioned values file.
- If an existing private admin-password file is specified, pass it directly with
  --admin-password-file. For the generate/preserve choice, omit that override.
- Stop my-first-model/llama-32-3b-instruct only if the setting above says yes.
  If no GPU is available and stopping Llama is not authorized, report the blocker.
- Always enable monitoring, preserving existing settings. Do not ask whether
  monitoring should be enabled. Verify GPU gauges and persistent AI counters.
- Run read-only preflight, then install. Preserve tournament data and credentials;
  take a verified external backup before any upgrade.
- Verify the first language, real audio transcription, player/game/leaderboard
  behavior and persistence. API tests do not prove browser microphone capture.
- After successful verification, report the game URL, admin URL and installed
  admin password. Never disclose the player signing key.
- Explain remaining manual checks and how to start the standalone five-minute
  Bash backup on one separate laptop before admitting players.
- Fix installation gaps in the repository, run regression checks, and report
  what was verified and what remains untested. Never uninstall/delete the PVC
  or reset results as a troubleshooting shortcut.
```

## What the agent should execute

Save the first language and registration mode together. Example for third-party
conferences (one username field, no name/email collection):

```yaml
registration:
  mode: "username"
game:
  requiredLanguage: "de"
```

To choose a memorable admin password, follow the [private password file
procedure](INSTALLATION.md#choose-the-admin-password) and add
`--admin-password-file ./admin-token` to both commands below. Leave the override
out of ordinary upgrades to preserve the installed password.

Then:

```bash
./deploy.sh --values values-conference.yaml --namespace whisper --free-rhdp-gpu --preflight
./deploy.sh --values values-conference.yaml --namespace whisper --free-rhdp-gpu
```

The script validates chart inputs, freezes the current Kubernetes context, checks
GPU/storage/operator readiness, enables monitoring, releases only the opted-in demo Llama, labels GPU
nodes, deploys via Helm and runs the internal real-audio smoke test. Reuse the same
venue file/namespace on upgrades. A language/config change rolls the UI; ordinary
upgrades preserve installed signing/admin keys.

## Handoff to the technical owner

Require a report containing the game URL, deployed versions, selected language,
verification results and remaining manual checks. Keep the venue file in your
team's configuration store, with no admin/signing keys. `now.env` is local state,
not a prerequisite for another owner. The owner requests the admin password in the final handoff; never include the
player signing key. Keep credentials out of Git and public logs.

Before admitting attendees, the owner must open trusted HTTPS in the booth browser,
grant microphone access, complete a real game, check TV/admin views, and start
[scripts/backup.sh](../scripts/backup.sh) on one external laptop. The backup script
needs only Bash/curl and standard OS utilities; its interval defaults to 300 seconds.
A successful install is not proof of a recoverable backup: rehearse restore on an
isolated database before the event. See the shared [operations runbook](INSTALLATION.md).

For installation without an agent, use [direct Helm installation](HELM-INSTALLATION.md).

## Common customization tasks

See the [customization index](CUSTOMIZATION.md) for dedicated guides to registration,
languages/phrases, default and custom difficulty groups, scoring, admin passwords
and conference backup/recovery.
