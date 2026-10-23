# Upgrade an existing installation to consolidated main

This guide applies to `main`, UI `v2.12.0-rc.4` and chart
`2.0.0-rc.7`. The tested version labels are retained after promotion. Read the
[dated acceptance report and outstanding manual checks](../validation/CONSOLIDATION-2026-10-23.md)
before using it at an event.

## From tournament-mode

Reuse the same namespace, owner values file, required first language and credentials.
Keep `tournament.enabled: true` (the default) and retain your `registration.mode`.
Use the [standard installer](../INSTALLATION.md) or
[direct Helm upgrade sequence](../HELM-INSTALLATION.md#6-upgrade-directly-with-helm).
Both require a verified external backup before mutation. Do not uninstall or
remove the PVC. Omit password/signing-key overrides to preserve their installed
values.

The new nullable round-count column preserves old rows and historical scoring.
New games record their round requirement at creation. See
[mode and database compatibility](game-mode.md). A rollback to the accepted
`v2.11.2` tournament release was rehearsed on the fresh acceptance cluster, then
upgraded back; rehearse your own release/configuration before a conference.

## From the older main standalone game

The consolidated default is tournament, which introduces registration and
persistent competition. To retain anonymous standalone behavior, explicitly set:

```yaml
tournament:
  enabled: false
game:
  requiredLanguage: de  # choose your existing owner's language
```

Even standalone keeps a PVC and Secret so mode switching is reversible. Main's
older chart did not create tournament storage. Select a non-default StorageClass
before first creation if required; do not try to change it afterward.

`deploy.sh` recognizes the accepted stateless combination: chart `1.0.0`, published
UI `v1.1.2`, owned by Helm release `whisper`, with no database volumes, tournament
PVC or tournament Secret. Read-only preflight reports that detection. The actual
upgrade saves the old complete Helm values, manifest and Deployment privately
under `BACKUP_DIR` (or `backups/NAMESPACE`) before applying anything. There is no
SQLite database or backup endpoint in that old app. A missing Secret on any other
release fails rather than generating replacement credentials. Modified legacy
images/layouts need review; do not relabel them to force detection.

For direct Helm, first save that stateless installation's configuration yourself:

```bash
umask 077
mkdir -p legacy-main-state
helm get values whisper -n whisper --all -o yaml > legacy-main-state/values.yaml
helm get manifest whisper -n whisper > legacy-main-state/manifest.yaml
oc get deployment whisper-ui -n whisper -o yaml > legacy-main-state/deployment.yaml
```

Confirm the source really is the known stateless release, retain those files
outside Git and use the normal direct Helm upgrade/monitoring/smoke commands with
your reviewed new values. Only this first stateless migration has no SQLite
snapshot to download. Every later upgrade, even with tournament disabled, uses
the regular protected database backup.

Compare your old values with the current defaults rather than carrying forward
an entire old chart values file unquestioned. In particular:

- Old UI tags such as `v1.1.2` and `v2.11.2` do not implement the new chart contract.
  Remove an old `image.tag` override to use the chart's published image. Chart
  validation rejects those old versions before cluster access/mutations.
- The old main modelcar/runtime differs from the currently tested RHOAI 3 setup.
  Review explicit model/runtime/resource overrides and registry entitlements.
  Do not assume the newer defaults preserve an old quantized model. Validate the
  intended model with real audio on a disposable environment first.
- Keep your first language, custom phrases/pools and intentional route branding.
  `clusterDomain`, `supportedLanguages` and `game.winThreshold` are obsolete inputs.
  Do not use `--reuse-values` as a migration shortcut.
- Standalone now shares the current Hard-only Swap behavior; it does not restore
  old main's Skip implementation.

A live old-main-to-candidate migration passed on the fresh RHOAI 3 test cluster,
using the old chart/UI and explicit compatible model/runtime settings on both
sides. German and Deployment/Service/Route identities survived, new storage was
created and real-audio/monitoring checks passed. See the acceptance report for
exact versions. This does not validate the old quantized-model/runtime defaults
or every historical owner override. Keep the old Git tag, image and values
recoverable until the intended configuration is verified for your setup.

## Verify before reopening the booth

Check warmup, inference, monitoring, the owner language/mode and a complete spoken
browser game. Check historical scores/tokens and backup/restore where applicable.
Schedule upgrades and mode switches between games. A version/tag or Ready pod is
not sufficient evidence. The older tournament branch remains in place while
independent-owner handover and remaining acceptance checks are completed.
