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

Tell the agent the conference name, namespace, required **first** language, and
whether it may stop the bundled RHDP Llama. The language is an owner decision;
German is `de`, Czech `cs`, Slovak `sk`, English `en`. Later rounds remain multilingual.

## Copyable prompt

Replace the event name/language/namespace with your decisions:

> Read AGENTS.md and docs/INSTALLATION.md on the tournament-mode branch. You are
> logged into the intended RHDP OpenShift AI 3 SNO cluster as cluster-admin.
> Install the Whisper tournament game for "Our Conference", namespace whisper,
> with German (de) as the first required challenge language. You are authorized to
> scale my-first-model/llama-32-3b-instruct to zero to release the only GPU.
> Enable monitoring as a required prerequisite, preserving existing monitoring
> settings; do not ask whether it should be enabled. Verify GPU gauges and AI
> counters. Use the published image and repository installer without rebuilding.
> Create a non-secret venue values file, run read-only preflight, then install.
> Preserve existing tournament data and credentials; take a verified external
> backup before any upgrade. Verify the first language, real audio transcription,
> player/game/leaderboard behavior and persistence. Do not claim browser microphone
> validation from an API test. After successful verification, report the game URL,
> admin URL and installed admin password. Explain how the owner starts the
> standalone five-minute Bash backup on a separate laptop.
> Fix installation gaps in the repository, run the regression checks, and report
> what was verified and what remains untested. Never uninstall/delete the PVC or
> reset results as a troubleshooting shortcut.

## What the agent should execute

The venue file should contain the chosen conference and first language. Example:

```yaml
conference:
  name: "Our Conference"
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
