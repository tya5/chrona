# Guided workspaces through MCP

Call `create_workspace` with a new `directory`, builtin `preset` ID and compact
`project` object. Validate and render the returned `workspace` path with
`validate_workspace` and `render_workspace`. Tool descriptions give input shapes.

Use `apply_authoring_command` for guided workspaces, never standalone plans or
Stores. Pass `workspaceRevision` as the inline command's `baseRevision`, then
carry each accepted `authoringResult.resultRevision` into the next edit.
Query `workspace_revision` when needed. An accepted result carries `inverse`, a
complete command: send it to restore the exact bytes (an added task is undone by
`removeWorkspaceTask`; `materializePresentationPreset` has none). Before editing,
`save_baseline` with the `workspace.yaml` path writes `baselines/<name>.yaml`
beside it; pass that as `render_workspace` `snapshot`. Stale bases and reused IDs with different requests are rejected; an
exact accepted `commandId` retry returns its durable result without writing.

Apply only the user's request. Writers require the server's `--allow-write`
configuration and have no approval step. Creation never overwrites a destination.
