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

The Command Request is a file in the workspace (`command`), the Store is named by a configuration file (`storeConfig`,
default `.chrona/store.yaml`), and every Store root in that file must lie inside the workspace. The result carries the
same Automation Result the command line writes to `--result`.

### Reading pinned evidence from a Store

Two read-only tools reach a Store, the same one `apply_command` writes, and work with or without `--allow-write`:

- `render_review` renders an immutable Render Context (the pinned, reproducible picture of `chrona render-review`, not a
  draft). Its `contextReference` is a workspace path to the Context's resource reference. The Context fixes its own
  format and viewport, so the tool takes neither, and an SVG or PNG result travels inline (`inline: none` returns only
  the identity, length and warnings).
- `compare_baseline` compares a named baseline with a candidate Project (`chrona baseline-compare`): `baselineReference`
  and `candidateReference` are workspace paths to their references, and the result is the same Automation Result the
  command line writes to `--result`.

Both name the Store with `storeConfig` (default `.chrona/store.yaml`), and every Store root in that file must lie inside
the workspace. Integrity is the Store configuration's, as on the command line: every reference is checked against its
pinned content identity, a Store with `integrity: required` (the default) refuses a reference that has none, and no
argument lowers either. A Store whose configuration says `integrity: optional` (the packaged example corpus does) is its
owner's explicit choice. Failures keep the codes the command line reports, so an identity mismatch on a render is
`E_CONTENT_IDENTITY` and one on a comparison is `E_BASELINE_REFERENCE` with a message that names the mismatch.

### What the server offers

| Tool | Same as | What it returns |
| --- | --- | --- |
| `validate_project` | `chrona validate` | `ok`, or typed diagnostics, including a dependency cycle (the objects on it, and the relation that closes it). It computes no dates. |
| `schedule_project` | `chrona schedule` | The computed placements, the critical path and any `W_DEADLINE` warnings; a fixed date or bound the dependencies contradict is rejected here, and a cycle as in `validate_project`. |
| `render_draft` | `chrona render` | A PNG preview (or the SVG text with `inline: svg`), the content identity and any warnings. It writes no file. |
| `list_presets` | `chrona preset list` | The builtin preset ids `render_draft` accepts. |
| `render_review` | `chrona render-review` | The pinned picture of an immutable Render Context from a Store: its format, content identity, warnings and the SVG or PNG inline. Read-only. |
| `compare_baseline` | `chrona baseline-compare` | What changed between a named baseline and a candidate Project in a Store. Read-only. |
| `check_command` | `chrona command-check` | Previews an Actual intake or baseline capture command against its Store; writes nothing. |
| `apply_command` | `chrona command-apply` | Applies it. Refused unless the server was started with `--allow-write`; no approval step. |

Every result carries a `status`: `ok`, `rejected` (the plan is refused: read each diagnostic's `code` and
`sourceRef`) or `failed` (the call could not run, for example a path outside the workspace). A rejection is a
normal result, so read `status`, not only the tool's error flag. The server also serves the agent skill's text as
two resources, `chrona://guide/authoring` and `chrona://guide/diagnostics`, so a client without skill support gets
the same guidance.

Schedule `analysis.totalFloat[id]` is `{value, unit, calendar}`, not an integer:
`calendar-days` uses a null calendar; `working-days` names the object's
effective calendar (its own, otherwise the Project's). Read the value and
basis together, never assume calendar days from a `d` amount. Critical objects
belong to a zero-float driving path to the one project finish; an isolated
fixed date is not critical. [Spec 57](../specification/57-public-schedule-analysis.md)
owns these rules; the MCP tool does not repeat scheduling analysis.

### Limits

- Every path is relative to the workspace and must name an existing file inside it: no `..`, no absolute path,
  no symlink that leaves the workspace, no input over 2 MiB. A Store root named by a configuration is held to the same
  rule. The only file the server writes is the Store that
  `apply_command` changes, and only with `--allow-write`; it never writes a plan, a picture or a path you name.
- `apply_command` takes an Actual intake batch and a baseline capture only. It has no authoring command, no resolve
  command and no revert command. Use the command line for those.
- One writer per Store: the server handles its own calls one at a time, but a command line and a server writing one
  Store at the same moment are not guaranteed to be safe.
- A `compare_baseline` result over 1 MiB is refused (`E_MCP_RESULT_TOO_LARGE`) and `chrona baseline-compare` writes it to a
  file; `render_review` has the same inline caps as `render_draft`, and reading a Store has no cap of its own (a Store's
  content is pinned by identity and may hold large assets such as fonts). `render_review` offers no `--format`,
  `--reject-unused-closure-inputs` or `--emit-scene` and no snapshot-root mode: use the command line for those.
- A render cannot be cancelled and takes a few seconds for a large plan; calls are handled one at a time. An inline
  image over 1.5 MiB (SVG over 1 MiB) is refused: lower the viewport or render to a file with `chrona render`.
- PNG needs the `render` extra. Without it `render_draft` still answers and reports `pngAvailable: false`.
- The contract of the tools and their results is [Spec 66](../specification/66-agent-interface.md).
