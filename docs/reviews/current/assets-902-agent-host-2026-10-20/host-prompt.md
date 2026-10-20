Perform a real manual agent-host trial of the connected `chrona` MCP server.
This is not a development task. Work only in the current scratch directory.
Do not use Git, change server code/configuration, install packages, call Chrona
Python functions/CLI directly, or use an SDK/raw-pipe client in place of MCP.
The coordinating developer has published the evidence plan on issue902.

1. Call `validate_project` on `project.yaml` through MCP. Observe its actual
   cycle diagnostic. Use the host's file-edit tool to remove only the relation
   `cycle-back` from this scratch Project; use apply_patch, not a shell rewrite.
   Call MCP validation again, then `schedule_project` and `render_draft` with
   `format: png`, `inline: image`, `viewport: 1000xauto`. Inspect the actual
   returned image and describe what you can see; do not infer an image from
   JSON alone. Report honestly if this host cannot view it.
2. Use MCP `create_workspace` to create directory `guided` with project id
   `host-guided`, title `Guided host trial`, tasks:
   - id `design`, title `Design`, planned start `2026-11-03`, finish `2026-11-06`;
   - id `build`, title `Build`, planned start `2026-11-09`, finish `2026-11-13`.
   Use the default preset. Validate the returned workspace and obtain its
   revision via MCP. Render it as PNG/image at `1000xauto`; inspect the image.
3. Through `apply_authoring_command`, change build to title `Build extended`,
   planned start `2026-11-09`, finish `2026-11-16`. Use an inline command of the
   current authoring-command schema, commandId `host-edit`, and the observed
   revision. Render and inspect again. Carry actual returned resultRevision,
   never invent a revision or write the workspace by hand.
4. Revert through another MCP authoring command, commandId `host-inverse`,
   restoring Build and its original dates, at the fresh revision. This is the
   existing inverse-command path, not a request for a new undo mechanism.
   Validate and render/view again. Compare the first and reverted guided PNG
   contentIdentity/byteLength; report whether they actually match.

End with a concise English transcript: ordered actual tool calls, statuses,
cycle code, placements, observed revisions, render hashes/lengths, what the
images visibly show, any failures/workarounds and any suspected defects.
Never claim unexecuted steps passed. Do not file issues or publish anything;
the coordinating developer preserves evidence and files confirmed defects.
