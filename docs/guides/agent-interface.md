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

The same plan-and-draw loop is also available as a small, read-only MCP server for a host that speaks the
[Model Context Protocol](https://modelcontextprotocol.io/) over standard input and output (a chat client or an
agent host that has no shell). The server is optional: install the extra with the SDK it needs, and add `render`
for PNG previews.

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

### What the server offers

| Tool | Same as | What it returns |
| --- | --- | --- |
| `validate_project` | `chrona validate` | `ok`, or typed diagnostics. It does not detect dependency cycles. |
| `schedule_project` | `chrona schedule` | The computed placements and the critical path; a cycle is rejected here. |
| `render_draft` | `chrona render` | A PNG preview (or the SVG text with `inline: svg`), the content identity and any warnings. It writes no file. |
| `list_presets` | `chrona preset list` | The builtin preset ids `render_draft` accepts. |

Every result carries a `status`: `ok`, `rejected` (the plan is refused: read each diagnostic's `code` and
`sourceRef`) or `failed` (the call could not run, for example a path outside the workspace). A rejection is a
normal result, so read `status`, not only the tool's error flag. The server also serves the agent skill's text as
two resources, `chrona://guide/authoring` and `chrona://guide/diagnostics`, so a client without skill support gets
the same guidance.

### Limits

- Every path is relative to the workspace and must name an existing file inside it: no `..`, no absolute path,
  no symlink that leaves the workspace, no input over 2 MiB. The server never writes a file.
- The first release has no tool that changes anything (no authoring command, no baseline) and no tool that reads a
  Store. Use the command line for those.
- A render cannot be cancelled and takes a few seconds for a large plan; calls are handled one at a time. An inline
  image over 1.5 MiB (SVG over 1 MiB) is refused: lower the viewport or render to a file with `chrona render`.
- PNG needs the `render` extra. Without it `render_draft` still answers and reports `pngAvailable: false`.
- The contract of the tools and their results is [Spec 66](../specification/66-agent-interface.md).
