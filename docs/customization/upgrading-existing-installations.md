# Upgrade an existing installation to the consolidated candidate

This guide applies to `codex/consolidate-modes`, UI `v2.12.0-rc.4` and chart
`2.0.0-rc.7`. The candidate has not yet replaced main. Read the
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

Compare your old values with the candidate defaults rather than carrying forward
an entire old chart values file unquestioned. In particular:

- Old UI tags such as `v1.1.2` and `v2.11.2` do not implement the new chart contract.
  Remove an old `image.tag` override to use the candidate's published image. Chart
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

A live old-main-to-candidate migration remains an acceptance gate. Rendered
Deployment/Service selectors and Route targets were checked for compatibility;
that check does not prove a live model/runtime migration. Keep the old Git tag,
image and values recoverable until this path is verified for your setup.

## Verify before reopening the booth

Check warmup, inference, monitoring, the owner language/mode and a complete spoken
browser game. Check historical scores/tokens and backup/restore where applicable.
Schedule upgrades and mode switches between games. A version/tag or Ready pod is
not sufficient evidence. The candidate leaves accepted branches in place while
manual acceptance and independent-owner handover remain outstanding.
