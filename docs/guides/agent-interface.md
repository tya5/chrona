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
<!-- /chrona:agent-tool-table -->

Every result carries a `status`: `ok`, `rejected` (the plan is refused: read each diagnostic's `code` and
`sourceRef`) or `failed` (the call could not run, for example a path outside the workspace). A rejection is a
normal result, so read `status`, not only the tool's error flag. A call whose arguments break a tool's input schema is
also `rejected`, not a protocol error: `E_MCP_INPUT_INVALID` with the JSON pointer of the violating node in `sourceRef`
and the expected shape in `message`. `validate_project` checks a Theme, Scheme, Layout Profile, View, Style, Actual Set
or profile file by its `kind`, as `chrona validate` does. The server also serves the agent skill's text as
two resources, `chrona://guide/authoring` and `chrona://guide/diagnostics`, so a client without skill support gets
the same guidance.

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

### Limits

- Read paths name existing files inside the server workspace: no `..`, absolute
  paths, escaping symlinks or inputs over2 MiB. Only `create_workspace` accepts a
  new directory, under an existing real parent; it never overwrites a destination.
- The three writing tools require `--allow-write`. Initialization copies a local
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
