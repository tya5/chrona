# Agent Tool Interface

**Status:** Proposed; the tool core is implemented in `chrona.app.agent_tools` (#142, slice I142-S3; the Store command
tools, #813; the Store read tools, #812) and served over MCP by `chrona mcp` (`chrona.app.mcp_server`, slice I142-S4).
**Owns:** the agent tool set `chrona/agent-tools/v0.7`, the shape of a tool result, the workspace path rules, the
write gate, the determinism contract of a tool call, the MCP binding rules of section 7, and the `E_MCP_*` diagnostic
codes.
**Does not own:** the meaning of a Project or a schedule (Spec 05, Spec 04), the render pipeline (Specs 06, 07,
33), the Store and the meaning of a command (Spec 09, Spec 10), the wire protocol of any transport, or the text of
the agent skill (`skills/chrona/`).
Design rationale, alternatives and review:
[`docs/design/issue-142-agent-interface-design-2026-10-01.md`](../design/issue-142-agent-interface-design-2026-10-01.md),
[`docs/archive/reviews/issue-142-agent-interface-architecture-review-2026-10-01.md`](../archive/reviews/issue-142-agent-interface-architecture-review-2026-10-01.md);
the Store command tools: [`docs/archive/planning/issue-813-mcp-mutating-tools.md`](../archive/planning/issue-813-mcp-mutating-tools.md);
the Store read tools: [`docs/archive/planning/issue-812-mcp-store-read-tools.md`](../archive/planning/issue-812-mcp-store-read-tools.md).

## 1. Principle

A tool is a use case with a typed envelope. The tool set adds no behavior: for the same files it returns the verdict,
the diagnostic code and the bytes the command of the same name returns, and a disagreement is a defect in one of
the two. The tool core imports use cases, the shared Store address guard and the shared Store functions
(`chrona.operational.store_commands` and `chrona.operational.store_reads`, which the command line calls too),
the shared authoring transaction, and the opaque exclusive workspace initializer only.
It imports no transport SDK and prints nothing. `apply_command`,
`apply_authoring_command` and `create_workspace` write only behind the write gate (sections2.1/2.3).

## 2. Tool set `chrona/agent-tools/v0.7`

Every tool takes paths relative to one workspace root (section 4). A change to any input or output schema, or to the
set, changes the tool-set version. `v0.2` (#782) added the optional `count` and `occurrences` properties of a
diagnostic and nothing else; `v0.3` (#813) added `check_command` and `apply_command`; `v0.4` (#812) added `render_review` and `compare_baseline`.
`v0.5` (#902 item3) admits Command v0.4 Actual revert/redo through the existing
Store tools; their path arguments, result envelope and write gate are unchanged.
`v0.6` (#902 item2) adds `apply_authoring_command` for the guided workspace.
`v0.7` (#1725) adds the workspace lifecycle below and permits an inline
authoring-command object through the same validated mutation use case.

| Tool | Command equivalent | Use case |
| --- | --- | --- |
| `validate_project` | `chrona validate` | `usecases.project_checks.validate_project_file` |
| `schedule_project` | `chrona schedule` | `usecases.project_checks.schedule_project_file` |
| `render_draft` | `chrona render` | `usecases.draft_render.render_draft` |
| `list_presets` | `chrona preset list` | `usecases.preset_library.list_builtin_presets` |
| `render_review` | `chrona render-review --store-config` | `usecases.context_review.render_context_closure` |
| `compare_baseline` | `chrona baseline-compare` | `operational.store_reads.compare_store_baseline` |
| `check_command` | `chrona command-check` | `operational.store_commands.run_store_command` |
| `apply_command` | `chrona command-apply` | `operational.store_commands.run_store_command` |
| `apply_authoring_command` | `chrona authoring-command-apply` | shared authoring use case and operational transaction of Spec51 §4.2 |
| `create_workspace` | initialization library entry | Spec51 initialization and exclusive publication |
| `validate_workspace` | workspace validation library entry | complete guided source/resource closure validation |
| `workspace_revision` | `chrona workspace revision` | existing validated workspace revision query |
| `render_workspace` | `chrona render-workspace` | shared guided-render use case |

The first four tools are read-only. `render_review` and `compare_baseline` are read-only too and read a Store
(section 2.2); the two command tools are section 2.1.

Inputs are closed objects (`additionalProperties: false`). A tool accepts no integrity override, no system-font
switch, no font-metrics or icon-catalog path, no typesetter descriptor, no rendered-output path, no Store root and no
`allow-missing-content-identity`. The registry (`registry_document()`, served as the tool list) carries the exact
JSON Schema 2020-12 input and output schema of each tool, and its annotations: for a read-only tool `readOnlyHint:
true`, `destructiveHint: false`; for mutating tools `readOnlyHint: false`, `destructiveHint: true` (the metadata does
not understate a write, whatever it overwrites); `idempotentHint: true` and `openWorldHint: false` for every tool.

- `validate_project {project}`: result `projectIdentity` (the SHA-256 of the file bytes) when the file was read.
  Mirrors `chrona validate`: it reports the dependency cycles the reference scheduler cannot place (`E_UNSUPPORTED_CYCLE`,
  or `E_UNSATISFIABLE_DEPENDENCIES`; Spec 04 section 16) and computes no dates, so a fixed date that contradicts its
  dependencies is found only by `schedule_project`.
- `schedule_project {project}`: result `placements` (object id to `{start, end}` or `{at}`, ISO dates, `end`
  exclusive), `analysis` (`criticalObjectIds` in Project object order,
  `totalFloat` records `{value, unit, calendar}` as defined by
  [Spec 57](57-public-schedule-analysis.md): `calendar-days` with null calendar
  or `working-days` with the effective object's calendar identifier) and `warnings`
  (a `W_DEADLINE` per object planned after its `deadline`, Spec 04 Section 10; empty when none; the plan is still
  scheduled).
- `render_draft {project, actual?, preset?, view?, theme?, scheme?, layout?, storeConfig?, viewport?, locale?, format?, inline?}`:
  `preset` is a builtin id or a workspace path ending `.yaml` or `.yml` (a value that contains `/` and ends
  otherwise is `E_MCP_PATH_SYNTAX`); `viewport` defaults to `1600xauto`, `locale` to `en-US`, `format` (`svg` or `png`, the artifact
  that `contentIdentity` and `byteLength` describe) to `svg`, `inline` to `image`. Result: `format`, `contentIdentity`
  (`sha256:` of the artifact bytes), `byteLength`, `pngAvailable`, `warnings`.
  Declared extension package references use the same pinned Store reader as
  immutable rendering. `storeConfig` has the Store tools' existing workspace-path
  shape and defaults to `.chrona/store.yaml`; it is opened only when a
  non-package reference is read. All roots must pass the same workspace
  containment check before any Store bytes are read. Packaged references need
  no workspace configuration; Projects without extensions remain unchanged.
- `list_presets {}`: result `presets` (`id`, and `gallerySet` when a gallery set shows the preset, in the order of `chrona preset list`) and `default`
  (`chrona-default-draft`).

### 2.1 The Store command tools

`check_command {command, storeConfig?}` and `apply_command {command, storeConfig?}` run the revision-bound Store
commands of Spec 10 through the one dispatch the command line uses (`operational.store_commands.run_store_command`):
`check_command` is `chrona command-check` and writes nothing; `apply_command` is `chrona command-apply`.

- `command` is a workspace path to a Command Request (`chrona/command/v0.3` or `v0.4`), parsed and validated as the command line
  does. `storeConfig` is a workspace path to a Store configuration (`chrona/store-config/v0.1`); omitted it is
  `.chrona/store.yaml` at the workspace root (no ancestor search, no working-directory lookup). Every Store root in the
  configuration is resolved with symlinks followed and must lie strictly inside the workspace, otherwise the call is
  `failed` with `E_MCP_PATH_CONTAINMENT` (`sourceRef` `/storeConfig`) before any file is read from or written to a root.
- Accepted command types: `applyActualIntakeBatch`, `captureSnapshot`,
  `revertActualCommand` and `redoActualCommand`. The latter two follow Spec35 §4.3
  and use the same Store transaction as an ordinary write. History diagnostics
  identify `/payload/commandId` or `/payload/revertCommandId` as appropriate.
  Any other type is `rejected` with
  `E_AUTOMATION_OPERATION_UNSUPPORTED` (`sourceRef` `/type`) and no Store is touched.
- Result: the envelope plus `automationResult`, the Automation Result (`chrona/automation-result/v0.2`) exactly as the
  command line writes it to `--result` (a replay carries `replayed: true`). Serialized with sorted keys it is byte-equal
  to that file for the same Store state. `automationResult` is present also when the status is `rejected`. An accepted
  result is `ok`; a rejected one is `rejected`, with one diagnostic per code of the Automation Result, component
  `operational`. The command line exits 2 for a rejected Automation Result; the tool reports `rejected`, the document
  having been understood and refused.
- **No approval step.** `apply_command` executes directly: it takes no confirm token and no proposal or decision
  exchange, and says so in its description. The exchange of Spec 10 section 9.1 is specified for a deployment with an
  authenticated principal and a policy and is not implemented here (owner decision on #813). The safeguards that remain
  protect data integrity, not authorization: compare-and-set on `baseRevision` (a stale one is `rejected`:
  `E_AUTOMATION_BASE_REVISION` when it differs from the target reference, `E_AUTOMATION_TARGET_CLOSURE` when the target is
  no longer the Store's current revision), the replay ledger (the same `commandId` and request is a no-op that returns the
  first result; the same `commandId` with another request is `E_COMMAND_ID_REUSE`), exclusive creation (an existing
  baseline name is `E_BASELINE_EXISTS`, different facts for an existing external key are `E_ACTUAL_EXTERNAL_CONFLICT`;
  nothing is overwritten) and revisions (every accepted Actual write is a new immutable Store revision; the previous one
  stays readable and can be written back through the Store's compare-and-set write).
- **Write gate.** `apply_command` writes only when the server was started with `--allow-write` (section 7). Otherwise a
  call is `failed` with `E_MCP_WRITE_DISABLED` before any file is opened. The flag is configuration, not approval: it is
  read once at start and no argument, file or environment variable changes it. Both tools are listed whatever the flag is,
  so the registry is one document; `check_command` works without the flag.
- Cooperating local Actual/snapshot writers (a command line and a server) share
  the Store transaction lock of Spec15 §7. Replay lookup, fresh-tip CAS,
  publication and replay recording cannot interleave across them.
  `E_STORE_LOCK_UNAVAILABLE` is a rejected Automation Result before canonical
  mutation. This advisory local lock is not protection against arbitrary file
  edits, a distributed lock or crash-atomic publication plus replay recording.

### 2.2 The Store read tools

`render_review {contextReference, storeConfig?, inline?}` is `chrona render-review --store-config`, and
`compare_baseline {baselineReference, candidateReference, storeConfig?}` is `chrona baseline-compare`. Both are
read-only (`readOnlyHint: true`), need no `--allow-write` and write no file, and both call the functions the command
line calls (`usecases.context_review`, `operational.store_reads`), so for the same Store they return the bytes the
command line returns.

- `contextReference`, `baselineReference` and `candidateReference` are workspace paths to resource-reference YAML files
  (the files `--context-reference`, `--baseline-reference` and `--candidate-reference` take). `storeConfig` is as in
  section 2.1: a workspace path, default `.chrona/store.yaml`, no ancestor search; every Store root in it is resolved
  with symlinks followed and must lie strictly inside the workspace, otherwise the call is `failed` with
  `E_MCP_PATH_CONTAINMENT` (`sourceRef` `/storeConfig`) before any file is read from a root.
- **Integrity.** The reference's Store must be declared by the configuration (`E_STORE_CONFIG_REQUIRED`). Every
  reference the closure reads is verified against its pinned `contentIdentity` (a mismatch is refused), and the
  configuration's `integrity` for that Store applies exactly as on the command line: `optional` (the default; an
  absent identity is accepted, Spec 42) or `required` (demands an identity on every reference), the configuration owner's setting. No argument can lower it:
  there is no snapshot-root, store-identity, integrity or `--allow-missing-content-identity` input.
- `render_review` renders the immutable Render Context, which fixes its own target format and viewport, so neither is an
  input. Result: `format` (the Context's target: `svg`, `png`, `pdf`, `typst`, `tikz`), `contentIdentity` (`sha256:` of the
  artifact bytes the command line writes to `--output`), `byteLength`, `inlined` and `warnings` (as `render_draft`). With
  `inline: artifact` (the default) an `svg` target travels as an `svg` payload and a `png` target as an `image`; any other
  target is not inlined. An inline SVG over 1 MiB or PNG over 1.5 MiB is `E_MCP_RESULT_TOO_LARGE` (use `inline: none` or
  the command line). A closure or render failure carries the code the command line reports (for example
  `E_CONTENT_IDENTITY`, `E_CONTENT_IDENTITY_REQUIRED` or `E_STORE_REFERENCE` from the closure); an unschedulable Project is `rejected`.
- `compare_baseline` result: the envelope plus `automationResult`, the Automation Result
  (`chrona/automation-result/v0.2`, `operation: baseline-compare`) exactly as the command line writes it to `--result`
  (a date is its ISO text); serialized with sorted keys it is byte-equal to that file. Accepted is `ok` (it carries
  `comparison`); a refused comparison is `rejected` with one diagnostic per code of the result (component `operational`,
  `sourceRef` `/`, the engine's message, which names the reference and the mismatch) and `automationResult` kept. A
  result that serializes to more than 1 MiB is `E_MCP_RESULT_TOO_LARGE`. The command line exits 2 for a rejected result;
  the tool reports `rejected`.
- A Store read has no size cap beyond the file system: Store content is identity-bound and an asset such as a font is
  legitimately large. A reference or configuration file over 2 MiB is `E_MCP_INPUT_TOO_LARGE`.

### 2.3 The guided authoring write tool

`apply_authoring_command {workspace, command}` takes a workspace-relative
workspace path and either a contained command-file path or an inline closed
`authoring-command/v0.1` object. Both command forms use the same schema and
mutation dispatcher. Resolve all paths through the containment guard after
the write gate and before opening any file. Its shared use case/transaction and exact CLI-equivalent
`authoringResult` follow Spec51 §4.2; no separate tool mutation policy or approval.
The tool core may import the same named operational authoring transaction port
as the CLI; schema/intent preparation stays in the use case. It does not call
individual CAS/file writers or add a second authoring command dispatcher.

It is always listed, with `readOnlyHint: false`, `destructiveHint: true` and
`idempotentHint: true`: a durable exact retry returns the original accepted
result without writes. Without `--allow-write`, fail `E_MCP_WRITE_DISABLED`
before opening any file. An understood accepted result is `ok`, a logical
refusal is `rejected` with the authoring result retained, and preflight/runtime
failures use the existing failed envelope. Diagnostics identify command fields
(`/baseRevision`, `/commandId`, `/target/path`) or the workspace/command path as appropriate.
Command/result versions remain v0.1; the new tool changes the tool-set version.

### 2.4 Workspace lifecycle (#1725)

- `create_workspace {directory, project, preset?}` initializes the Spec51
  bundle. `project` is the compact workspace-project object (id, optional
  title, tasks with id/title/planned start/finish), not a second Project format;
  `preset` is a builtin ID returned by `list_presets`, default
  `chrona-default-draft`. The destination must not exist and its parent must
  already be a real directory inside the server workspace. Validate syntax,
  reserved names, symlinks and containment before reading preset bytes.
  Return `workspace` (the relative workspace.yaml path) and `workspaceRevision`.
  It is a mutating, gated tool; collisions leave existing content unchanged.
- `validate_workspace {workspace}` validates the complete guided workspace and
  pinned resource closure, returning `workspaceRevision` on success without
  writing. `workspace_revision {workspace}` returns the same canonical CAS
  precondition through the existing query. Neither requires the write gate.
- `render_workspace {workspace, viewport?, locale?, format?, inline?}` shares
  guided rendering with the CLI, including `{expr}` tokens and effective font
  resolution. Its options, artifacts, warning/size policy and read-only
  annotations match `render_draft`; the latter remains a raw-Project tool.
- The command description and inline schema expose the existing five command
  types and payloads. An agent carries creation/query `workspaceRevision` and
  accepted `authoringResult.resultRevision` into the next command base; it
  never has to read files or provoke a stale-base error to discover a revision.
  Reverting a source edit is its inverse command at the new revision, not a
  second undo engine. MCP recovery guidance names tools, not shell commands.

Only initialization accepts a nonexistent destination directory. Its explicit
destination guard retains the syntax/containment/device rules of section4;
the existing-file guard is unchanged for every read and command-file input.

## 3. Result

Every result is the envelope `{status, diagnostics, omittedDiagnostics?}` plus the tool's own fields, which are
present only when `status` is `ok` (a field a call had already produced, such as `projectIdentity` or
`automationResult`, is kept on a `rejected` result).

- `status` follows the exit code of the command: `ok` (0), `rejected` (1: the input was understood and refused) and
  `failed` (an adapter-level refusal, or exit 2). One exception: a missing rasterizer
  (`E_RENDER_RASTERIZER_UNAVAILABLE`) is `failed` even though the command exits 1, because nothing is wrong with the
  plan. A transport sets its error flag only for `failed`; a `rejected` plan is a result.
- A diagnostic is `{code, severity, component, sourceRef, message}` with the optional `revisionRefs`,
  `resourceKind`, `resourceIdentity`, `phase`, `rule` (as the command reports them), `count` and, for a render
  warning or info record, `detail`: the record's remaining ledger fields, keys sorted. The `message` of an error row
  is never empty and never only its code: it is the producer's text when that names something, else a curated
  sentence for the code, else a derived sentence that says no further detail is recorded for the code
  (`usecases.diagnostic_messages.error_message`, applied by `usecases.failure_report.diagnostic_record`, so the
  command prints the same text). `count` (2 or more) is present only when equal rows were merged into one
  (`usecases.failure_report.collapse_records`); no `count` means once. `sourceRef` is a JSON pointer, or the
  ledger's own reference for a render warning, or `/`.
- Presentation failures preserve the owner's stable code separately from its
  bounded detail. Theme color-scale slot failures identify
  `/body/colorScales/<escaped-id>/slots` and missing/extra keys; View annotation
  anchor failures identify `/body/annotations/<index>/anchor` and the missing
  facet, mark or endpoint. Transport does not derive ownership from messages
  or put a formatted message in `code`.
- A render warning has a `message` too, `<cause>: <subject>` (`usecases.diagnostic_messages.describe_warning`,
  applied by `usecases.warning_ledger`). Warnings of one code, severity and cause are one row, however many
  placements raised them (`usecases.diagnostic_messages.collapse_warnings`, applied by
  `usecases.draft_render.warning_payloads`, so the command prints the same rows in its stdout success envelope): the row keeps
  the fields and `sourceRef` of the first occurrence, `count` is the exact number (2 or more), `occurrences` lists
  the distinct `diagnostic` identities in order (at most 20), and the message names the first subject and "and N
  more". The Scene keeps every per-placement fact; for each code the counts of the rows add up to the number of
  Scene `diagnostics` of that code. An info record is never merged, and its own `count` (labels left out) stays in
  `detail`.
- Successful `render`, `render-review` and `render-workspace` print one stdout
  JSON envelope `{status: "ok", diagnostics: [], warnings: [...]}` after output
  publication, including an empty warnings array when appropriate. Warnings do
  not fail the render (exit 0) and are not duplicated on stderr. Failures retain
  their existing stdout envelope and exit mapping. Consumers of the former
  stderr JSON lines migrate to `stdout.warnings`; artifact bytes are unchanged.
- A Layout/Scene warning about an explicitly identified Project object carries
  its escaped `/objects/<id>` pointer and known title in the message. Producers
  capture this provenance; transport never parses a placement ID to guess it.
  Multi-owner findings name known subjects in stable order and retain additional
  subjects in detail; `sourceRef` identifies the first. Non-object sources are
  not assigned a fictional Project owner. Provenance does not affect diagnostic
  identity, collapse cause, occurrence order/count or serialized Scene facts.
- A file that is empty or parses to a list or a scalar is a rejected Project (`E_SCHEMA`, `sourceRef` `/`, status
  `rejected`) for `validate_project` and `schedule_project`, as it is for `chrona validate`, `schedule` and `render`.
- The tool layer applies three transforms the command does not: it merges rows that scrubbing made equal (their
  counts add), keeps at most 50 and reports the rest in `omittedDiagnostics`, and scrubs host paths from every
  message and `detail` string.
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

A tool call reads files below one directory, resolved once when the server starts, the Store tools read a Store below
it, and mutating tools modify only a contained Store or guided workspace bundle.
A filesystem root is refused (`E_MCP_WORKSPACE_TOO_BROAD`).

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
5. The Store roots named by a Store configuration are held to the same rule (sections 2.1 and 2.2): inside the workspace,
   symlinks followed.
6. The check and the open are separate steps. The guard is a safety rail for a local process the user started, not a
   sandbox against an agent that has its own shell.

## 5. Determinism

A result is a pure function of the workspace file bytes, the arguments, the chrona version and the pinned renderer
versions: no timestamp, duration, process id or host path; locale is `en-US` unless given; installed fonts are consulted only for a Theme family the workspace's declared fonts do not
cover (#1281), so a workspace that declares every font it uses is host-independent; every mapping the tool returns is sorted by key (`placements`, `totalFloat`, `detail`), and a result does
not depend on the hash seed. The SVG bytes equal those of the command's output file. PNG bytes depend on the pinned
rasterizer of the `render` extra.

## 6. Codes owned by the tool layer (component `mcp`)

| Code | When |
| --- | --- |
| `E_MCP_PATH_SYNTAX` | A path argument fails the syntax rules or names a reserved device. |
| `E_MCP_PATH_CONTAINMENT` | A path resolves outside the workspace. |
| `E_MCP_INPUT_TOO_LARGE` | An input file exceeds 2 MiB. |
| `E_MCP_RESULT_TOO_LARGE` | An inline payload, or a `compare_baseline` result, exceeds its cap; lower the viewport (`render_draft`), use `inline: none`, or use the command line. |
| `E_MCP_WORKSPACE_TOO_BROAD` | The workspace is a filesystem root. |
| `E_MCP_WRITE_DISABLED` | A write tool is called on a server started without `--allow-write` (status `failed`). |
| `E_MCP_UNAVAILABLE` | `chrona mcp` is run without the optional SDK; the message says `pip install 'chrona[mcp]'` (exit 2). |

## 7. The MCP binding

`chrona mcp [--workspace DIR] [--allow-write] [--list-tools]` serves the tool set over MCP on standard input and output;
it is the only transport. `--allow-write` enables mutating tools (sections2.1/2.3/2.4); without it the server is read-only
and the registry is unchanged. The binding is the one module that imports the SDK (`chrona.app.mcp_server`, optional extra
`chrona[mcp]`, `mcp>=2.0,<3`); `chrona mcp --list-tools` prints the registry and needs no SDK.

- `tools/list` is the registry: names, titles, descriptions, input and output schemas and the annotations of section 2.
  `tools/call` is `call_tool` with its result in content blocks: block 0 is the structured result as JSON text; an
  `image` block carries the PNG preview; an embedded resource carries the SVG. The structured content equals block 0.
- The error flag is set only when `status` is `failed`. Unknown tool names and malformed arguments are protocol errors
  (`INVALID_PARAMS`), never an envelope.
- Calls are handled one at a time (a render cannot be cancelled) in a worker thread; the server holds no state between
  calls and writes nothing to standard output but protocol frames. Logging goes to standard error.
- `initialize` carries `instructions` (under 1 KB: the model in three sentences, that a rejection is a result, whether writes are on, and that
  `schedule_project` is the tool that computes dates). Two read-only resources serve the packaged skill, `chrona://guide/authoring`
  (the body of `SKILL.md`) and `chrona://guide/diagnostics` (`references/diagnostics.md`); without a packaged skill they
  are omitted. No prompts, subscriptions, sampling or other capability is offered.
- There is no HTTP transport, listener, authentication or background task.

## 8. Command-line surface (#1304)

- `chrona --version` prints the package version, the Project format and the visual profiles it supports, one per line, and exits 0.
- `chrona` with no arguments prints the usage text (commands grouped by task) to standard error and exits 2; there is no JSON. A
  wrong or missing argument elsewhere stays a typed `E_COMMAND_SYNTAX` result.
- `chrona --help` groups the commands by task (author, render, reviewed history, agents, maintenance). Every command has a
  description and every flag a help text, in user terms; none names a milestone (`M26`) or stage. `docs/guides/cli-reference.md` is
  generated from the same definitions.
- A command that succeeds prints one JSON object that states what it did: `{"status": "ok", ...}`. `validate` prints
  `{"status": "ok", "diagnostics": []}`; `init`, `preset copy` and `skill copy` add `directory` and the sorted `created` files;
  the store commands (`command-check`, `command-apply`, `actual-intake`, `actual-resolve`,
  `baseline-capture`, `baseline-compare`) print `{"status": <result status>, "result": <path>}` before their exit code.
  Commands whose result is the artifact itself (`compile`, with or without `--output`, `schedule`, `render`) are unchanged.
