# Using chrona from an AI coding agent

Chrona ships an agent skill: a short, tested guide that teaches an AI coding agent
(Claude Code and any host that reads the same `SKILL.md` layout) how to plan with
chrona. It is for a user who wants an agent to draft or revise a project plan and
render it, with the dates computed by the `chrona` command and not by the model.

## What the skill is for

- It teaches the authoring model (the Project is the semantic truth, a View selects, a
  Theme paints, a Layout composes, the CLI renders), the draft path that exists today
  (`chrona init`, edit `project.yaml`, `chrona render` with a preset) and the working
  loop (`validate`, `schedule`, `render`, read the diagnostics).
- It lists the diagnostic codes an agent meets and what to change for each, and says when
  Mermaid or a hand-drawn picture is the better tool.
- It does not replace the specification, and it does not add behaviour: it only uses the
  commands the CLI already has.

The skill lives in the repository at [`skills/chrona/`](../../skills/chrona/SKILL.md)
and in the installed package, so it always matches the installed version. Every command
in it is run by the repository's documented-command check, and every diagnostic code it
names is checked against the source, so it cannot rot unnoticed.

## Install it

Copy the packaged skill into the skills directory your agent host reads. The target must
be empty or absent; the command never overwrites. For Claude Code, the project scope is
`.claude/skills/chrona` and the user scope is `~/.claude/skills/chrona`:

```bash
chrona skill copy --output my-agent-skill/chrona
```

## Refresh it after upgrading chrona

The command refuses a non-empty directory (`E_SKILL_OUTPUT_EXISTS`), so a refresh is a new
copy that you compare with the installed one and then move into place:

```bash
chrona skill copy --output my-agent-skill/refreshed
```

Compare `my-agent-skill/chrona` with `my-agent-skill/refreshed` with your usual directory
diff (`diff -r` on macOS and Linux), keep any local edits you want, and replace the old
directory with the new one.

## Use chrona from an MCP client

The same plan-and-draw loop is also available as a small MCP server for a host that speaks the
[Model Context Protocol](https://modelcontextprotocol.io/) over standard input and output (a chat client or an
agent host that has no shell). It is read-only unless you start it with `--allow-write` (see below). The server is
optional: install the extra with the SDK it needs, and add `render` for PNG previews.

```bash
pip install 'chrona[mcp,render]'
```

`chrona mcp --list-tools` prints the tool registry as JSON and needs neither the extra nor a workspace:

```bash
chrona mcp --list-tools
```

Point the host at the server and name the one directory it may read. The command is `chrona mcp` (or
`python -m chrona mcp`, which works without `Scripts` on `PATH` on Windows):

```json
{"mcpServers": {"chrona": {"command": "chrona", "args": ["mcp", "--workspace", "."]}}}
```

<!-- chrona:doc-check skip: starts a server that reads standard input until the host closes it -->
```bash
chrona mcp --workspace .
```

Without `--workspace` the current directory is the workspace. A filesystem root is refused.

### Letting the agent write a Store

By default the server writes nothing. Two tools take a Store command, an Actual intake batch or a named baseline
capture: `check_command` previews one and never writes, and `apply_command` applies it. `apply_command` is refused with
`E_MCP_WRITE_DISABLED` unless you start the server with `--allow-write`. That flag is configuration, not approval: chrona
adds no approval step of its own, so the agent applies a command the moment it calls the tool, and whether your host
asks you first is the host's setting. Start it only for a workspace whose Store you are willing to let the agent change:

<!-- chrona:doc-check skip: starts a server that reads standard input until the host closes it -->
```bash
chrona mcp --workspace . --allow-write
```

What protects the Store is not authorization but integrity, and it is the same as `chrona command-apply`:

- a stale `baseRevision` is rejected (compare-and-set), so two agents cannot silently overwrite each other;
- a command is identified by its `commandId`: sending the same command again is a no-op that returns the first result
  (`replayed: true`), and reusing the id for a different command is rejected;
- nothing is overwritten: an existing baseline name and different facts for an existing external key are rejected;
- every write is a new immutable Store revision, so an earlier one can be inspected and written back.

The Command Request (`command`) is an inline object with `version: chrona/command/v0.3`
or `version: chrona/command/v0.4`, or a path to a file in the workspace. Both forms
use the same validation, revision and replay rules. The Store is named by a configuration file (`storeConfig`,
default `.chrona/store.yaml`), and every Store root in that file must lie inside the workspace. The result carries the
same Automation Result the command line writes to `--result`.

A workspace with no Store needs none made by hand. `create_store` writes `.chrona/store.yaml` (one local Store, root
`.chrona/store`, `integrity: required`) and `publish_resource {kind, path | document}` seeds it with an immutable resource
and returns its `reference`: that object is the `target` of a `captureSnapshot`, `applyActualIntakeBatch` or
`revertActualCommand` command (`baseRevision` is `reference.revision.token`), and the `project` and `batch` of an intake
payload. `kind` is `project` (a file that validates; changed bytes are a new revision, the same bytes a replay),
`actual-set` or `actual-intake-batch`; give the last two inline as `document`, since no other tool writes them. An Actual Set
is published once: it then changes only by command, and each accepted command's `automationResult.resultTarget` is the next
reference. A different document under an Actual Set's id is `E_STORE_RESOURCE_EXISTS`; a second `create_store` with another
identity is `E_STORE_CONFIG_EXISTS`. The whole loop is: `create_store`, `publish_resource` (project, actual-set, batch),
`apply_command` with `captureSnapshot` (the baseline), `apply_command` with `applyActualIntakeBatch`, and `apply_command`
with `revertActualCommand {commandId}` to undo the intake.

### Reading pinned evidence from a Store

Two read-only tools reach a Store, the same one `apply_command` writes, and work with or without `--allow-write`:

- `render_review` renders an immutable Render Context (the picture `chrona render-review` draws from a Store, not a
  draft). Its `contextReference` is a workspace path to the Context's resource reference. The Context fixes its own
  format and viewport, so the tool takes neither, and an SVG or PNG result travels inline (`inline: none` returns only
  the identity, length and warnings).
- `compare_baseline` compares a named baseline with a candidate Project (`chrona baseline-compare`): `baselineReference`
  and `candidateReference` are workspace paths to their references, and the result is the same Automation Result the
  command line writes to `--result`.

Both name the Store with `storeConfig` (default `.chrona/store.yaml`), and every Store root in that file must lie inside
the workspace. Integrity is the Store configuration's, as on the command line: a content identity a reference carries is
verified, a reference without one is accepted (Spec 42), a Store whose configuration says `integrity: required` refuses a
reference that has none, and no argument lowers either. That setting is its owner's explicit choice. Failures keep the codes the command line reports, so an identity mismatch on a render is
`E_CONTENT_IDENTITY` and one on a comparison is `E_BASELINE_REFERENCE` with a message that names the mismatch.

### What the server offers

The following table is checked directly against the server registry.

<!-- chrona:agent-tool-table -->
| Tool | Purpose | Writes |
| --- | --- | --- |
| `validate_project` | Validate a Project | no |
| `schedule_project` | Compute a Project's schedule | no |
| `render_draft` | Render a draft picture of a Project | no |
| `list_presets` | List builtin presets | no |
| `render_review` | Render pinned evidence from a Store | no |
| `compare_baseline` | Compare a named baseline with a candidate | no |
| `check_command` | Preview a Store command | no |
| `apply_command` | Apply a Store command | yes |
| `apply_authoring_command` | Apply a guided workspace command | yes |
| `create_workspace` | Create a guided workspace from a builtin preset | yes |
| `validate_workspace` | Validate a guided workspace and its pinned resources | no |
| `workspace_revision` | Read the current guided workspace revision | no |
| `render_workspace` | Render a guided workspace | no |
| `create_project` | Create a Project file | yes |
| `apply_project_command` | Apply a Project command | yes |
| `save_baseline` | Save a baseline copy of a Project | yes |
| `create_store` | Create a workspace Store | yes |
| `publish_resource` | Publish a resource into the Store | yes |
<!-- /chrona:agent-tool-table -->

Every result carries a `status`: `ok`, `rejected` (the plan is refused: read each diagnostic's `code` and
`sourceRef`) or `failed` (the call could not run, for example a path outside the workspace). A rejection is a
normal result, so read `status`, not only the tool's error flag. A call whose arguments break a tool's input schema is
also `rejected`, not a protocol error: `E_MCP_INPUT_INVALID` with the JSON pointer of the violating node in `sourceRef`
and the expected shape in `message`. `validate_project` checks a Theme, Scheme, Layout Profile, View, Style, Actual Set
or profile file by its `kind`, as `chrona validate` does. The server also serves the agent skill's text as
resources, `chrona://guide/authoring`, `chrona://guide/diagnostics` and `chrona://guide/references/<page>`, so a client
without skill support gets the same guidance. The diagnostics resource explains every code an MCP tool emits, with what
it means and what to change.

Schedule `analysis.totalFloat[id]` is `{value, unit, calendar}`, not an integer:
`calendar-days` uses a null calendar; `working-days` names the object's
effective calendar (its own, otherwise the Project's). Read the value and
basis together, never assume calendar days from a `d` amount. Critical objects
belong to a zero-float driving path to the one project finish; an isolated
fixed date is not critical. [Spec 57](../specification/57-public-schedule-analysis.md)
owns these rules; the MCP tool does not repeat scheduling analysis.

### Guided authoring without a shell

With writes enabled, call `create_workspace` using a builtin ID from
`list_presets` (omitting `preset` selects the default):

```json
{"directory":"plan","preset":"target-b","project":{"id":"launch","title":"公開計画","tasks":[{"id":"review","title":"レビュー","planned":{"start":"2026-01-05","finish":"2026-01-09"}}]}}
```

The result supplies `workspace` (`plan/workspace.yaml`) and `workspaceRevision`.
Pass that path to `validate_workspace`, `workspace_revision` or `render_workspace`;
the latter takes the same viewport/locale/format/inline options as `render_draft`.
It resolves the local copied preset exactly as the CLI does, including Theme
expressions. Japanese source text and author key order stay readable after edits.

`apply_authoring_command` accepts the workspace path and an inline command (or
a contained command file). The command carries `version`, `commandId`, `type`,
`target: {kind: "authoring-workspace", path: "workspace.yaml"}`, `baseRevision`
and `payload`. Its registry schema and description give the five operations:
`setWorkspaceTask`, `setWorkspaceActual`, `selectPresentationPreset`,
`setPresentationOverride` and `materializePresentationPreset`.
Use creation/query `workspaceRevision` as the first base, then carry each
accepted `authoringResult.resultRevision` into the next command. Revert an edit to
an existing task or Actual with its inverse command at the current revision (send
the previous values back). No CLI call, manual file read or deliberately stale
command is needed to discover a revision.

**Retrying a command.** Sending the same `commandId` and request again writes nothing and returns the first result
with `replayed: true` and `revisionIsCurrent`: `true` when `resultRevision` is still the workspace revision, `false`
when later commands changed it (take the next base from `workspace_revision`, not from the replay). A result without
`replayed` is a fresh application. If the same `commandId` is rejected with `E_AUTHORING_COMMAND_ID_REUSE` (for
example a resend at the latest revision after a crash), the earlier command was applied: the row carries
`firstApplied: true`, `appliedRevision` and `revisionIsCurrent`. Use a new `commandId` for a new edit.

**Switch preset.** `selectPresentationPreset` only re-pins the workspace to a
preset directory that is already inside it, and it checks the binding when you
send it: `id` and `version` must equal the `id` and `body.package.version` of the
file at `path`. For the workspace above that is
`{"id":"chrona-builtin-target-b","version":"1","path":"preset/preset.yaml"}`
(the id in the file, not the short `target-b` name from `list_presets`). A mismatch
such as `marquee` over the copied `target-b` file is rejected with
`E_AUTHORING_PRESET_IDENTITY`, the file is not touched and the revision does not
advance. No tool copies a second builtin preset into an existing workspace, so to
change the look call `create_workspace` again with the other builtin `preset`, a new
`directory` and the same `project`, then render that workspace.

**Undo an added task.** There is no delete operation: `setWorkspaceTask` adds a new
`id` or replaces the task with that `id`, and undoing an addition is not an inverse
edit. To drop a task, call `create_workspace` with a new `directory` and the project
without it (it never overwrites), and keep working in the new workspace. Until then
the old workspace is unchanged and still renders.

### Editing a full `project.yaml` without a shell

A guided workspace holds fixed-date tasks only. For gates, `Nwd` durations, constraints and deadlines edit the Project
file itself (the one `validate_project`, `schedule_project` and `render_draft` read), with writes enabled:

1. `create_project {file, project}` writes a new Project (`file` must not exist; `project` is the complete
   `timeline/v0.7` mapping) and returns `projectRevision`. For a file that already exists, `validate_project` returns
   its `projectRevision`.
2. `apply_project_command {project, command}` takes an inline command with `version: chrona/project-command/v0.1`,
   `commandId`, `type`, `target: {kind: "project", path: "<file name only>"}`, `baseRevision` (the revision from step 1
   or the last `projectResult.resultRevision`) and `payload`. Types: `setObject {id, object}` (add or replace
   one object; any schedule mode), `removeObject {id}` (refused while a relation, `parent`, `attachesTo` or an annotation anchor names it),
   `setRelation {relation}` (add a dependency, or replace the one with the same `id`; both endpoints must be existing
   objects), `removeRelation {id}`, `setCalendar {id, calendar}`, `removeCalendar {id}` (refused while the Project
   default, an object or a lag uses it), `setEntity {id, entity}`, `removeEntity {id}` (refused while an object or entity `fields` value names it),
   `setFieldRole {role, binding}`, `removeFieldRole {role}`, `setAnnotation {id, annotation}` (the anchor must be an
   existing object), `removeAnnotation {id}` and `setProjectMeta {title?, calendar?}` (edits the project header; `null`
   removes the member; the Project id cannot change).

```json
{"project":"plan/project.yaml","command":{"version":"chrona/project-command/v0.1","commandId":"add-gate-1","type":"setObject","target":{"kind":"project","path":"project.yaml"},"baseRevision":"sha256:...","payload":{"id":"go-live","object":{"type":"gate","schedule":{"mode":"scheduled-point","constraints":{"at":{"min":"2026-11-10"}}}}}}}
```

The candidate is checked with the Project schema and the Core rules before anything is written, and a rejection names
each finding at its command pointer (`/payload/object/schedule/amount`) with nothing written. A dependency cycle or a
date that contradicts a dependency is not refused here: run `schedule_project` and read the dates. Stale
`baseRevision`, retry (`replayed`, `revisionIsCurrent`) and `commandId` reuse behave as for `apply_authoring_command`.
The file is rewritten as canonical YAML, so comments in it are not kept.

To revert an accepted edit, send the `inverse` of its `projectResult` as the `command` of another `apply_project_command`.
It is a complete command (`commandId` is the original id plus `-inverse`, `baseRevision` is the result revision) that puts back
exactly what the edit changed, including the position of a removed key; for a file in canonical form (written by
`create_project` or an earlier command) the file is byte-identical to the one before the edit. Once another edit has changed
the file the inverse is refused as stale (`E_AUTHORING_BASE_REVISION`): read `validate_project` and make the opposite
edit yourself. The inverse's own result carries the inverse of the inverse, which redoes the edit.

To compare with the plan as it was, call `save_baseline {project, name}` before editing. It copies the file unchanged to
`baselines/<name>.yaml` next to the Project and returns that path and its `contentIdentity`; an existing name with other
content is refused (`E_BASELINE_FILE_EXISTS`), the same content again is a replay. After the edits, `render_draft` with
`snapshot` set to that path draws the baseline's ghosts and deltas. This is the file route; the Store route is separate.

### Limits

- Read paths name existing files inside the server workspace: no `..`, absolute
  paths, escaping symlinks or inputs over2 MiB. Only `create_workspace` accepts a
  new directory, under an existing real parent; it never overwrites a destination.
- The writing tools (`apply_command`, `apply_authoring_command`, `create_workspace`, `create_project`,
  `apply_project_command`, `save_baseline`) require `--allow-write`. Initialization copies a local
  bundle; authoring edits use durable CAS/replay; Store commands support Actual
  intake, snapshot capture, `revertActualCommand` and `redoActualCommand` through
  the same locked transaction as the CLI. No tool writes a rendered picture.
- Calls are serial and a render cannot be cancelled. Large dependency plans can
  take minutes when routing dominates; there is no fixed completion-time promise.
- An inline image over1.5 MiB or SVG over1 MiB is refused: lower the viewport or
  use `inline: none`. A `compare_baseline` result over1 MiB is refused too.
  Immutable Store assets themselves have no read-size cap. A pinned Context
  determines its own format and viewport; Draft tools offer SVG and PNG.
- PNG needs the `render` extra. Without it `render_draft` still answers and reports `pngAvailable: false`.
- The contract of the tools and their results is [Spec 66](../specification/66-agent-interface.md).
