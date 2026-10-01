# Agent Tool Interface

**Status:** Proposed; the tool core is implemented in `chrona.app.agent_tools` (#142, slice I142-S3) and served over
MCP by `chrona mcp` (`chrona.app.mcp_server`, slice I142-S4).
**Owns:** the read-only agent tool set `chrona/agent-tools/v0.1`, the shape of a tool result, the workspace path
rules, the determinism contract of a tool call, the MCP binding rules of section 7, and the `E_MCP_*` diagnostic
codes.
**Does not own:** the meaning of a Project or a schedule (Spec 05, Spec 04), the render pipeline (Specs 06, 07,
33), the Store and any mutating command (Spec 09, Spec 10), the wire protocol of any transport, or the text of
the agent skill (`skills/chrona/`).
Design rationale, alternatives and review:
[`docs/design/issue-142-agent-interface-design-2026-10-01.md`](../design/issue-142-agent-interface-design-2026-10-01.md),
[`docs/reviews/current/issue-142-agent-interface-architecture-review-2026-10-01.md`](../reviews/current/issue-142-agent-interface-architecture-review-2026-10-01.md).

## 1. Principle

A tool is a use case with a typed envelope. The tool set adds no behavior: for the same files it returns the verdict,
the diagnostic code and the bytes the command of the same name returns, and a disagreement is a defect in one of
the two. The tool core imports use cases (and the shared Store address guard) only, imports no transport SDK, prints
nothing and writes nothing.

## 2. Tool set `chrona/agent-tools/v0.1`

All four tools are read-only and take paths relative to one workspace root (section 4). A change to any input or
output schema, or to the set, changes the tool-set version.

| Tool | Command equivalent | Use case |
| --- | --- | --- |
| `validate_project` | `chrona validate` | `usecases.project_checks.validate_project_file` |
| `schedule_project` | `chrona schedule` | `usecases.project_checks.schedule_project_file` |
| `render_draft` | `chrona render` | `usecases.draft_render.render_draft` |
| `list_presets` | `chrona preset list` | `usecases.preset_library.list_builtin_presets` |

There is no mutating tool, no Store-based tool and no `compare_baseline`: no runtime approval model exists for a
write (review F3), and a Store tool would need `operational/` (review F2).

Inputs are closed objects (`additionalProperties: false`). A tool accepts no integrity override, no system-font
switch, no font-metrics or icon-catalog path, no typesetter descriptor, no output path and no
`allow-missing-content-identity`. The registry (`registry_document()`, served as the tool list) carries the exact
JSON Schema 2020-12 input and output schema of each tool, and the read-only annotations
(`readOnlyHint`, `idempotentHint`, `destructiveHint: false`, `openWorldHint: false`).

- `validate_project {project}`: result `projectIdentity` (the SHA-256 of the file bytes) when the file was read.
  Mirrors `chrona validate`: it reports the dependency cycles the reference scheduler cannot place (`E_UNSUPPORTED_CYCLE`,
  or `E_UNSATISFIABLE_DEPENDENCIES`; Spec 04 section 16) and computes no dates, so a fixed date that contradicts its
  dependencies is found only by `schedule_project`.
- `schedule_project {project}`: result `placements` (object id to `{start, end}` or `{at}`, ISO dates, `end`
  exclusive), `analysis` (`criticalObjectIds` in Project object order, `totalFloat` in calendar days) and `warnings`
  (a `W_DEADLINE` per object planned after its `deadline`, Spec 04 Section 10; empty when none; the plan is still
  scheduled).
- `render_draft {project, actual?, preset?, view?, theme?, scheme?, layout?, viewport?, locale?, format?, inline?}`:
  `preset` is a builtin id or a workspace path ending `.yaml` or `.yml` (a value that contains `/` and ends
  otherwise is `E_MCP_PATH_SYNTAX`); `viewport` defaults to `1600xauto`, `locale` to `en-US`, `format` (`svg` or `png`, the artifact
  that `contentIdentity` and `byteLength` describe) to `svg`, `inline` to `image`. Result: `format`, `contentIdentity`
  (`sha256:` of the artifact bytes), `byteLength`, `pngAvailable`, `warnings`.
- `list_presets {}`: result `presets` (`id`, `gallerySet`, in the order of `chrona preset list`) and `default`
  (`chrona-default-draft`).

## 3. Result

Every result is the envelope `{status, diagnostics, omittedDiagnostics?}` plus the tool's own fields, which are
present only when `status` is `ok`.

- `status` follows the exit code of the command: `ok` (0), `rejected` (1: the input was understood and refused) and
  `failed` (an adapter-level refusal, or exit 2). One exception: a missing rasterizer
  (`E_RENDER_RASTERIZER_UNAVAILABLE`) is `failed` even though the command exits 1, because nothing is wrong with the
  plan. A transport sets its error flag only for `failed`; a `rejected` plan is a result.
- A diagnostic is `{code, severity, component, sourceRef, message}` with the optional `revisionRefs`,
  `resourceKind`, `resourceIdentity`, `phase`, `rule` (as the command reports them) and, for a render warning or
  info record, `detail`: the record's remaining ledger fields, keys sorted. A render warning carries no message
  today (except `W_DEADLINE`, which has one), so `message` is otherwise `""`; its meaning is in `skills/chrona/references/diagnostics.md`. `sourceRef` is a JSON
  pointer, or the ledger's own reference for a render warning, or `/`.
- The tool layer applies three transforms the command does not: it drops exact duplicate diagnostics, keeps at most
  50 and reports the rest in `omittedDiagnostics`, and scrubs host paths from every message and `detail` string.
- Warnings and info records of a successful render, and the `W_DEADLINE` warnings of a successful schedule (which carry
  a `message`), are `warnings`, in the order of the render, never dropped or
  invented. `diagnostics` is empty when `status` is `ok`.
- A failure that is not one of the typed families is `E_TOOL_FAILURE` with the fixed message
  `internal error: <ExceptionClass>`; the traceback goes to the log (standard error), never to the result.
- Unknown tool names and arguments that do not satisfy the input schema (a wrong type, a missing or extra property,
  an enum or `viewport` mismatch, an empty or over-long path string) are protocol errors, never an envelope.
- The `render_draft` payloads that travel beside the structured result are an `image` (PNG bytes) for `inline:
  image` and an `svg` (UTF-8 text with the URI `chrona://render/<sha256 of the svg>.svg`) for `inline: svg`. A PNG
  preview without the `render` extra is omitted and `pngAvailable` is `false`. An inline SVG over 1 MiB or PNG over
  1.5 MiB is `E_MCP_RESULT_TOO_LARGE`.

## 4. Workspace rules

A tool call reads files below one directory, resolved once when the server starts. A filesystem root is refused
(`E_MCP_WORKSPACE_TOO_BROAD`).

1. Every path argument passes `resolve_store_address(workspace, value, charset="file-name")` of
   `core/store_address.py`: `/`-separated, no backslash, colon, drive, anchor, control character, empty or all-dot
   segment (`E_MCP_PATH_SYNTAX`); the resolved path, symlinks followed, lies strictly inside the workspace
   (`E_MCP_PATH_CONTAINMENT`). Non-ASCII file names are accepted.
2. A segment whose stem is a Windows reserved device name (`CON`, `PRN`, `AUX`, `NUL`, `COM1` to `COM9`, `LPT1` to
   `LPT9`, any extension) is refused on every OS (`E_MCP_PATH_SYNTAX`).
3. The target must be an existing regular file (`E_INPUT_IO` otherwise, as the command reports an unreadable file)
   no larger than 2 MiB (`E_MCP_INPUT_TOO_LARGE`).
4. References inside a document (preset members, Theme `extends`, assets) keep the guard against the document's own
   directory; the tool adds nothing there.
5. The check and the open are separate steps. The guard is a safety rail for a local process the user started, not a
   sandbox against an agent that has its own shell.

## 5. Determinism

A result is a pure function of the workspace file bytes, the arguments, the chrona version and the pinned renderer
versions: no timestamp, duration, process id or host path; locale is `en-US` unless given; system fonts are never
consulted; every mapping the tool returns is sorted by key (`placements`, `totalFloat`, `detail`), and a result does
not depend on the hash seed. The SVG bytes equal those of the command's output file. PNG bytes depend on the pinned
rasterizer of the `render` extra.

## 6. Codes owned by the tool layer (component `mcp`)

| Code | When |
| --- | --- |
| `E_MCP_PATH_SYNTAX` | A path argument fails the syntax rules or names a reserved device. |
| `E_MCP_PATH_CONTAINMENT` | A path resolves outside the workspace. |
| `E_MCP_INPUT_TOO_LARGE` | An input file exceeds 2 MiB. |
| `E_MCP_RESULT_TOO_LARGE` | An inline payload exceeds its cap; lower the viewport, use `inline: none`, or use the command line. |
| `E_MCP_WORKSPACE_TOO_BROAD` | The workspace is a filesystem root. |
| `E_MCP_UNAVAILABLE` | `chrona mcp` is run without the optional SDK; the message says `pip install 'chrona[mcp]'` (exit 2). |

## 7. The MCP binding

`chrona mcp [--workspace DIR] [--list-tools]` serves the tool set over MCP on standard input and output; it is the
only transport. The binding is the one module that imports the SDK (`chrona.app.mcp_server`, optional extra
`chrona[mcp]`, `mcp>=2.0,<3`); `chrona mcp --list-tools` prints the registry and needs no SDK.

- `tools/list` is the registry: names, titles, descriptions, input and output schemas and the read-only annotations.
  `tools/call` is `call_tool` with its result in content blocks: block 0 is the structured result as JSON text; an
  `image` block carries the PNG preview; an embedded resource carries the SVG. The structured content equals block 0.
- The error flag is set only when `status` is `failed`. Unknown tool names and malformed arguments are protocol errors
  (`INVALID_PARAMS`), never an envelope.
- Calls are handled one at a time (a render cannot be cancelled) in a worker thread; the server holds no state between
  calls and writes nothing to standard output but protocol frames. Logging goes to standard error.
- `initialize` carries `instructions` (under 1 KB: the model in three sentences, that a rejection is a result, and that
  `schedule_project` is the tool that computes dates). Two read-only resources serve the packaged skill, `chrona://guide/authoring`
  (the body of `SKILL.md`) and `chrona://guide/diagnostics` (`references/diagnostics.md`); without a packaged skill they
  are omitted. No prompts, subscriptions, sampling or other capability is offered.
- There is no HTTP transport, listener, authentication or background task.
