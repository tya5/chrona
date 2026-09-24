# Guided authoring revision recovery

Guided authoring commands use an optimistic-concurrency precondition. Read the
current workspace revision before creating the first command; do not hash the
YAML file yourself.

<!-- chrona:doc-check skip: requires an author-created guided workspace -->
```console
$ chrona workspace revision workspace.yaml
sha256:9cc81954eeb06b4fd7cc90c7383bf28bc204f76e0a81ae79ee805c0c2774f715
```

Use that exact value as `baseRevision` in an `authoring-command/v0.1` document:

```yaml
version: chrona/authoring-command/v0.1
commandId: rename-first-task
type: setWorkspaceTask
target: {kind: authoring-workspace, path: workspace.yaml}
baseRevision: sha256:9cc81954eeb06b4fd7cc90c7383bf28bc204f76e0a81ae79ee805c0c2774f715
payload:
  task:
    id: first-task
    title: Updated title
    planned: {start: '2026-04-01', finish: '2026-04-10'}
```

Apply it with a new result destination:

<!-- chrona:doc-check skip: requires the guided workspace and command document created in the preceding example -->
```console
chrona authoring-command-apply --workspace workspace.yaml \
  --command rename.yaml --result rename-result.json
```

An accepted result contains `resultRevision`. Use it as the next command's
`baseRevision`. A rejected result contains `commandBaseRevision` and
`workspaceRevision`; for `E_AUTHORING_BASE_REVISION`, the diagnostic also
names the expected and received values. Read the revision again and retry with
the current value rather than retrying a stale command.

This workflow is specific to local `authoring-workspace/v0.1` files. Immutable
Store commands use their Store-issued opaque revision tokens instead.

## Inspecting other declared identities

Use the identity form that matches the declaration.  Immutable resource
`contentIdentity` values pin exact bytes, while replay records use Chrona's
canonical document identity:

<!-- chrona:doc-check skip: requires author-provided identity input files -->
```console
chrona identity bytes assets/catalog.yaml
chrona identity document command-request.yaml
```

These commands are read-only.  They do not replace `chrona workspace
revision`, which first validates a guided workspace and is the only correct
producer for an authoring command's `baseRevision`.
