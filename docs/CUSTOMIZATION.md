# Customize the game

Start with the task you need. Keep your non-secret settings together in
`values-conference.yaml` and reuse that file on every upgrade. Both installation
paths use the same chart; changes to Helm configuration need no image rebuild.
The registration feature requires UI `v2.11.0` or newer.

- [Choose registration mode](customization/registration.md): full registration or
  one username-only form, returning players, switching modes and existing data.
- [Choose languages and edit phrases](customization/languages-and-phrases.md): the
  first required language, adding a language, changing text and testing speech.
- [Configure difficulty groups](customization/difficulty-groups.md): exact default
  Easy/Medium/Hard pools, selection behavior and a complete override example.
- [Understand tournament scoring](customization/tournament-scoring.md): accuracy,
  multipliers, elapsed-time bonus, worked examples, Hard-only Swap and best-score ranking.
- [Choose/change the admin password](customization/admin-password.md): literal agent
  prompt or private file, password preservation/rotation and access summary.
- [Run backups and rehearse recovery](customization/backups-and-restore.md): the
  standalone five-minute laptop loop, retention, restore drills and upgrade handoff.

For prerequisites, backup-protected upgrades and incident handling, use
[the operations runbook](INSTALLATION.md). For direct Helm commands, use
[Helm installation](HELM-INSTALLATION.md); for the copyable owner prompt, use
[agent installation](AGENT-INSTALLATION.md).

## Runtime, routes and storage

Keep the tested runtime/modelcar combination unless a replacement has been tested
on the target operator/GPU. `model.resources.memory` controls system RAM;
`gpu.memoryUtilization` controls the vLLM GPU allocation. The current baseline uses
0.9; old examples using 0.2–0.3 are invalid and rejected. Verify changes with a real
transcription test rather than copying model-length flags from old documentation.

`route.host` is optional: OpenShift assigns a host when empty. `clusterDomain` and
`supportedLanguages` are obsolete installation inputs. Choose
`tournament.storageClass` only on first installation; it cannot change an existing
PVC. The SQLite UI uses one replica and Recreate updates, not HA.

`conference.name` remains optional branding for the main/TV headings; it is not a
required setup choice. Editing templates/branding assets requires a new image.
The model display name is only a UI label: inspect the runtime/modelcar to identify
the actual model and quantization. Keep credentials out of committed values files.
