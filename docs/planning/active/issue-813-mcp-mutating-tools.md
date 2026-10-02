# Issue #813: MCP mutating tools (`check_command`, `apply_command`)

**Status:** Design (this revision). The architecture review and the implementation plan are added to this record by
the next two documentation PRs, before any code.
**Public base:** `main` at `e4429030` (observed 2026-10-02); design on `e11fd97d`.
**Issue:** [#813](https://github.com/tya5/chrona/issues/813), read with its owner comment of 2026-10-02 (the decision).
**Living contract:** [Spec 66](../../specification/66-agent-interface.md) (changed with the code slices, not here).
**Predecessor:** [#142](https://github.com/tya5/chrona/issues/142), whose
[acceptance review](../../reviews/current/issue-142-agent-interface-acceptance-review-2026-10-02.md) row 12 is this issue.

## 1. Baseline

### 1.1 Literal acceptance

The issue body (as split from #142) says: scope `check_command`, `apply_command` and `apply_authoring_command`,
write-gated by `--allow-write` with exclusive creation (`storage.publication.publish_exclusive`), tool annotations,
`E_MCP_WRITE_DISABLED`. Acceptance: "design correction first; a stale `baseRevision` is rejected; a replayed command
is idempotent; the write flag off refuses; nothing is overwritten. Depends on the Store-tools issue for the Store
path."

The owner comment replaces part of it. Its acceptance changes are: drop "design correction first" and the
confirm-token rows; keep stale `baseRevision` rejected, replay idempotent, write flag off refuses, nothing
overwritten, and add one test showing a write followed by a revert through the Store. Its scope order is actual
intake and baseline capture first, then guided authoring commands. The work plan's rows are:

| # | Row | Source |
| ---: | --- | --- |
| 1 | `check_command` exists as a read-only preview and is not a precondition of `apply_command` | owner comment |
| 2 | `apply_command` executes directly: no confirm token, no proposal or decision exchange; the tool description says the Spec 10 section 9.1 exchange is not implemented | owner comment |
| 3 | A stale `baseRevision` is rejected with a typed error | body, owner comment |
| 4 | A replayed command is idempotent (a no-op) | body, owner comment |
| 5 | With the write flag off a mutating call is refused (`E_MCP_WRITE_DISABLED`) and writes nothing | body, owner comment |
| 6 | Nothing is overwritten (exclusive creation) | body, owner comment |
| 7 | One test shows a write followed by a revert through the Store | owner comment |
| 8 | `--allow-write` is a server start option and configuration, not approval; documented | owner comment |
| 9 | Tool annotations are honest: `readOnlyHint: false`, `destructiveHint: true` for the mutating tool | owner comment |
| 10 | Scope order: actual intake and baseline capture first | owner comment |
| 11 | Guided authoring commands (`apply_authoring_command`) | body, owner comment (step 2) |
| 12 | "Depends on the Store-tools issue for the Store path" | body |
| 13 | "Design correction first" | body; dropped by the owner comment |

Rows 11 and 12 are expected to be `narrowed` with a successor (section 2.4). Row 13 is dropped by the owner and is
recorded as such in the acceptance review.

### 1.2 What is published (verified on `main` `e4429030`)

- The tool core `chrona.app.agent_tools` (`chrona/agent-tools/v0.2`) has four read-only tools; its registry
  document carries read-only annotations for every tool; `call_tool(scope, name, arguments)` returns a `ToolResult`
  whose `structured` mapping is the envelope `{status, diagnostics}` plus the tool's own fields. It imports no SDK
  and writes nothing. `WorkspaceScope` resolves one workspace root and turns a path argument into an existing
  regular file strictly inside it through `core.store_address`.
- `chrona.app.mcp_server` (the one SDK module) serves the registry over stdio, serializes calls with a lock and has
  no write flag; `chrona mcp [--workspace DIR] [--list-tools]` is the only entry.
- `tools/check_import_direction.py` limits `chrona.app.agent_*` and `chrona.app.mcp_server` to the `usecases` and
  `resources` packages and the module `chrona.core.store_address`.
- The mutating use cases exist and are tested through the command line: `command-check`, `command-apply`,
  `actual-intake`, `actual-resolve` and `baseline-capture` all go through `operational.command_engine`
  (`check_command`, `apply_actual_command`). The CLI dispatch (parse, required type per command, run, write the
  result file exclusively, exit 2 unless `accepted`) is inline in `chrona.app.cli._run`.
- `operational` imports `usecases`; `usecases` may not import `operational`. A `usecases` facade over the command
  engine would be an import cycle, so the tool core cannot reach the engine under today's import rules.
- Integrity safeguards, probed by running the engine on a scratch Store: `baseRevision` must equal the target
  reference's revision token (`E_AUTOMATION_BASE_REVISION`); the local Actual Store checks its own tip
  (a stale target with a new command id is `E_AUTOMATION_TARGET_CLOSURE`); the replay ledger
  (`command-replays.json` in the Store root) returns the recorded result with `replayed: true` for the same
  `commandId` and request, and refuses a reused id with a different request (`E_COMMAND_ID_REUSE`); a different
  fact for an existing external key is `E_ACTUAL_EXTERNAL_CONFLICT`; an existing baseline name is
  `E_BASELINE_EXISTS` (`publish_exclusive`); every accepted Actual write is a new immutable
  `revision-actual:<n>:<digest>` directory and a new tip pointer, and earlier revisions stay readable.
- `LocalActualStore.undo` and `redo` return `None` (no local revert exists); a revert today is a compare-and-set
  `write` of an earlier revision's content.
- No runtime approval exchange exists (#142 architecture review F3); the owner decided none is built.

### 1.3 Inferred and unverified

- Inferred: the Store root named by a Store configuration file may be any path, including one outside the workspace
  (an absolute path or `..`). Nothing in `load_store_config` contains it. A mutating tool must contain it; this is
  the largest new risk and gets its own tests (design plan question Q4).
- Unverified until the code slices: the exact `status`/diagnostic mapping for a command result, and the size of the
  new tool descriptions against the `INSTRUCTIONS` limit (Spec 66 section 7: under 1 KB).
- Not verified and not claimed: safety against two processes writing one Store at the same time (the command line
  and a server). The server serializes its own calls only.

## 2. Design plan

### 2.1 Use cases

- U1. An agent has a Command Request file in the workspace (an Actual intake batch, or a baseline capture) and a
  Store inside the workspace. It previews the command (`check_command`) and applies it (`apply_command`) without any
  human approval step, and receives the same Automation Result the command line writes.
- U2. A read-only deployment (the default) offers no write: a mutating call is refused with a typed code.
- U3. A client retries after a timeout: the replay ledger turns the retry into a no-op that returns the first result.
- U4. Two agents race on one target: the second command's base is stale and is rejected; nothing is overwritten.
- U5. A write was wrong: the owner inspects the earlier revision and reverts through the Store.

### 2.2 Open decisions (resolved in the design, section 3)

| # | Question |
| ---: | --- |
| Q1 | One generic pair of tools over any Command Request, or one tool per command-line command? |
| Q2 | How does the tool receive the command: a workspace file path or an inline object? |
| Q3 | How does the tool find the Store: a configuration path, discovery, or a fixed place? |
| Q4 | How is a write kept inside the workspace when the Store configuration names its own roots? |
| Q5 | Are the mutating tools listed when the write flag is off, or only refused when called? |
| Q6 | Which `status` and diagnostics does a command result map to, and what of the Automation Result travels? |
| Q7 | Where does the shared use case live so that the tool core and the command line call the same code under the import rules? |
| Q8 | Which command types does the first release accept? |
| Q9 | What is the default of the write flag, and what is "revert" in this release? |
| Q10 | Tool-set version and annotations. |

### 2.3 Responsibility boundaries

- The command engine (`operational`) owns the meaning of a command, the ledger and the Store writes. It does not
  change. Only its dispatch (currently inline in the CLI) moves to a small shared module that both adapters call.
- The tool core owns argument validation, the workspace path guard, the Store containment check, the write gate and
  the envelope. It imports use cases only (one deliberate module edge, decided in the design).
- The binding owns the `--allow-write` option, passes one boolean to the core, and sets annotations from the registry.
- No new Store format, schema or Command Request version is introduced; Spec 10 is unchanged.

### 2.4 Scope and successors

In scope: `applyActualIntakeBatch` and `captureSnapshot` through `check_command` and `apply_command`. Out of scope and
moved to one successor issue ([#902](https://github.com/tya5/chrona/issues/902)): `resolveActualObservation`, `apply_authoring_command`
over the guided authoring workspace, a revert tool, inline command objects, and a multi-process write lock.
Row 12 ("depends on the Store-tools issue") is met in the narrow sense that the Store path is a workspace-contained
configuration, and not by waiting for [#812](https://github.com/tya5/chrona/issues/812), which stays the read side.

### 2.5 Acceptance evidence

Per row: a unit test of the tool core on a scratch workspace and Store; a stdio test through the real server like
`tests/mcp/test_mcp_stdio_e2e.py`; byte equality with the command line's result file; one test per threat of the
design's threat model (path escape, write outside the workspace, overwrite, replay, stale revision, symlink); a
mutation check that removes each guard and shows a test failing; the three-OS run of the exact publishing commit with
the MCP tests confirmed on Windows and macOS.

### 2.6 Order of design slices

1. Baseline and design plan (published, PR #901).
2. Design (section 3; this PR), with the successor issue #902 and the decision record on the issue.
3. Architecture review (section 4).
4. Implementation plan (section 5).

## 3. Design

Decisions Q1 to Q10 and their reversal are also recorded as a [comment on the issue](https://github.com/tya5/chrona/issues/813#issuecomment-5946348970) (owner-level judgement calls made
by the implementing agent, with options, choice, reason and how to reverse).

### 3.1 Tool surface (Q1, Q8)

Two tools, generic over a Command Request, as the issue's table names them, not one tool per command-line command:

| Tool | Command equivalent | Writes | Gated by `--allow-write` |
| --- | --- | --- | --- |
| `check_command` | `chrona command-check` | no | no |
| `apply_command` | `chrona command-apply` (and `actual-intake`, `baseline-capture`, which run the same engine) | yes | yes |

Accepted command types in this release: `applyActualIntakeBatch` and `captureSnapshot`. Any other type
(`resolveActualObservation`, an unknown one) is a `rejected` result with `E_AUTOMATION_OPERATION_UNSUPPORTED`, the code
the command engine already uses for an unsupported type, and nothing is read from or written to a Store. Reason: the
owner asked for the narrowest write surface first; the type check is one set in one place, so widening it later is a
one-line change with its own tests.
Rejected alternative: five tools mirroring `command-check`, `command-apply`, `actual-intake`, `actual-resolve`,
`baseline-capture`. They differ only in the type the CLI requires, so they would add four tools with no new behavior.

### 3.2 Inputs (Q2, Q3)

`check_command {command, storeConfig?}` and `apply_command {command, storeConfig?}`, closed objects.

- `command`: a workspace path (the shared guard: relative, `/`-separated, inside the workspace, an existing regular
  file, at most 2 MiB) to a Command Request document (`chrona/command/v0.3`, Spec 10). The engine parses and validates it
  against its schema exactly as `chrona command-apply --command FILE` does. Rejected alternative: an inline object.
  It would save the agent a file write, but the document would then reach the engine by a second route with its own
  size and shape rules; the same input route as the command line is what keeps the result byte-equal. Inline commands
  belong with [#815](https://github.com/tya5/chrona/issues/815)'s inline project text.
- `storeConfig`: a workspace path to a Store configuration (`chrona/store-config/v0.1`). Omitted means
  `.chrona/store.yaml` at the workspace root. There is no ancestor search and no working-directory lookup: the command
  line discovers upwards from the current directory, a server with a fixed workspace must not.
- Neither input accepts an integrity override, a `--allow-missing-content-identity` switch, an output path or a Store
  root. The only way to name a Store root is the configuration file, which is contained (3.3).

### 3.3 Containment of the write surface (Q4)

The Store configuration names its own roots (an absolute path, or a path relative to the configuration file), and the
engine writes below them: `actual-tips/`, `revision-*/`, `snapshots/`, `command-replays.json`. The tool therefore
opens the configuration through `open_store_reader(config_path, contained_in=workspace_root)`: every configured root
is resolved (symlinks followed) and must lie strictly inside the resolved workspace root; otherwise the call is
`failed` with `E_MCP_PATH_CONTAINMENT`, `sourceRef` `/storeConfig`, before any file is read from or written to a root.
This applies to `check_command` too, so a configuration cannot make the read-only tool read outside the workspace.
Inside a root every address and identifier the engine turns into a file name already passes `core.store_address`
(segment charset, containment with symlinks followed; #731), which is unchanged.

The check and the write are separate steps; a symlink swapped in between is not detected, as for every tool
(Spec 66 section 4 rule 5). This is a safety rail for a local process the user started, not a sandbox against an agent
that has its own shell.

### 3.4 The write gate (Q5, Q9)

`ToolSpec` gains `mutating: bool`. The registry always lists both tools, whatever the server's configuration, so the
registry and `chrona mcp --list-tools` are one stable document. `call_tool(scope, name, arguments, *, allow_write=False)`:
arguments are checked against the schema first (a malformed call is a protocol error in every mode), then, for a
mutating tool with `allow_write` false, the result is `failed` with `E_MCP_WRITE_DISABLED` and the message says to
restart the server with `--allow-write`. The refusal happens before the command file, the configuration or any Store is
opened. `chrona mcp --allow-write` sets the flag; the default is off, so a read-only deployment stays the default and the
read-only tools behave as before. The flag is configuration and not approval: it is read once at start, no call, argument,
environment variable or file can change it, and the tool description says so. To flip the default (writes on unless
`--read-only`), change the option's default in `chrona.app.cli` and Spec 66 section 7; no other code reads it.
Rejected alternative: list the mutating tools only when the flag is on. A host would then show a tool list that depends
on a start option and the refusal code could never be returned; the typed refusal is what the issue asks for.

### 3.5 Result (Q6)

The envelope `{status, diagnostics, omittedDiagnostics?}` plus `automationResult`: the Automation Result mapping
(`chrona/automation-result/v0.2`) exactly as `chrona command-check` or `command-apply` writes to `--result`
(`operation` is `command-check` or `command-apply`; a replay carries `replayed: true`). Serialized with sorted keys it is
byte-equal to the command line's result file for the same Store state. `automationResult` is present when the engine
produced one, also for a `rejected` result.

- Result `accepted` is `ok`. Result `rejected` is `rejected`: one diagnostic per code of the Automation Result, component
  `operational`, `sourceRef` `/`, and a message that says what to change (`message` is never only the code). The tool
  layer owns messages for the integrity codes it can name: `E_AUTOMATION_BASE_REVISION` (the command's `baseRevision`
  is not the target reference's revision), `E_AUTOMATION_TARGET_CLOSURE` (a referenced resource is unreadable or the
  target is no longer the Store's current revision: read the current revision and build a new command with a new
  `commandId`), `E_CONFLICT` (a compare-and-set lost), `E_COMMAND_ID_REUSE`, `E_ACTUAL_EXTERNAL_CONFLICT`,
  `E_BASELINE_EXISTS` and `E_AUTOMATION_OPERATION_UNSUPPORTED`. Other codes get the shared derived sentence.
- A failure that is not a result of the engine (unreadable file, a schema error in the command, no Store configuration,
  a root outside the workspace, the write gate) goes through the shared failure report as for every tool.
- The command line exits 2 for a rejected Automation Result; the tool reports `rejected`, because the document was
  understood and refused (Spec 66 section 3).

### 3.6 Shared use case and import rules (Q7)

The CLI's dispatch of the five operational commands moves out of `chrona.app.cli._run` into a new module
`chrona.operational.store_commands`:

- `open_store_reader(config_path, *, contained_in=None)`: `load_store_config` plus the containment check of 3.3.
- `run_store_command(operation, command_text, reader, *, allowed_types=None)`: parse, the required type of the operation
  (`actual-intake`, `actual-resolve`, `baseline-capture`), the optional `allowed_types` narrowing, `check_command` or
  `apply_actual_command`, and the `operation` stamp. It returns the Automation Result; it reads no file, writes no result
  file and exits nothing.

The command line keeps reading the file, writing `--result` exclusively and choosing the exit code; its bytes do not
change (the characterization suite in `tests/fixtures/cli_characterization` pins them). The tool core calls the same two
functions, so a disagreement between the two front ends is a defect in the shared function.

A `usecases` module cannot hold this: `operational` imports `usecases`, so the reverse import is a cycle. The tool core
may reach `operational` through this one module only: `tools/check_import_direction.py` gains a `modules` entry
(`chrona.operational.store_commands`) in the rules of `chrona.app.agent_`, with the reason in the commit; every other
`operational`, `storage`, `commands` or `presentation` import from the tool core still fails. The binding
`chrona.app.mcp_server` gains no new edge. Rejected alternatives: relaxing the package rule to all of `operational`
(a tool could then import the engine's internals and bypass the facade), and injecting a runner from the binding
(the binding has the same module rule and the core would be untestable without a fake of the thing that matters).

### 3.7 Tool set version, annotations, descriptions (Q10)

`TOOL_SET_VERSION` becomes `chrona/agent-tools/v0.3` (new tools and new properties of the registry, no change to an
existing tool's schema; #782 D9: an additive change bumps the version). `ToolSpec.document()` derives annotations from
`mutating`: `check_command` is `readOnlyHint: true, destructiveHint: false, idempotentHint: true`; `apply_command` is
`readOnlyHint: false, destructiveHint: true, idempotentHint: true` (repeating the same call is a no-op through the
ledger), `openWorldHint: false` for both. `destructiveHint: true` is the owner's instruction: the metadata must be truthful
even though nothing is overwritten. The description of `apply_command` says plainly: it executes directly; there is no
approval step and no confirm token; the Spec 10 section 9.1 proposal and decision exchange is not implemented; it writes
only when the server was started with `--allow-write`; and the safeguards that remain (compare-and-set on
`baseRevision`, the replay ledger, exclusive creation, one new immutable Store revision per write).

### 3.8 Revert (Q9)

Every accepted Actual write is a new immutable revision; the previous revision stays byte-identical and readable by its
token. This release adds no revert command or tool. "A write followed by a revert through the Store" is shown by a test
that applies an intake through the tool, reads the previous revision back, writes its content as a new revision by the
Store's own compare-and-set write, and shows the tip and the content restored with the history intact. A revert command is
part of the successor issue.

### 3.9 Threat model

The writer is a local process the user started, driven by an agent that has the MCP tools and may or may not have a shell
(Spec 66 section 4). The guards below protect the workspace and the Store's integrity; none is an authorization.

| Threat | Guard | Result | Test |
| --- | --- | --- | --- |
| Path escape in `command` or `storeConfig` (`..`, absolute, backslash, drive, device name) | shared workspace guard | `failed`, `E_MCP_PATH_SYNTAX` | one per input, per shape |
| Symlink: `command` or `storeConfig` is a link leaving the workspace | shared guard, symlinks followed | `failed`, `E_MCP_PATH_CONTAINMENT` | one per input; skipped only where the OS cannot create a link |
| Write outside the workspace: a configured Store root is absolute, uses `..`, or is a symlink out | `open_store_reader(contained_in=)` | `failed`, `E_MCP_PATH_CONTAINMENT`; the outside directory stays empty | one per shape, asserting no file appeared |
| Overwrite: a baseline name exists; an external key exists with other facts | engine: `publish_exclusive`; `E_ACTUAL_EXTERNAL_CONFLICT` | `rejected`; bytes and tip unchanged | one each, comparing bytes before and after |
| Replay: the same command twice; the same id with another request | replay ledger | second call `ok`, `replayed: true`, no new revision; the other request `rejected`, `E_COMMAND_ID_REUSE` | one each |
| Stale revision: `baseRevision` behind the Store's tip | engine compare-and-set | `rejected`, typed code; Store unchanged | two shapes (base differs from the target reference; target behind the tip) |
| Write flag off | the gate (3.4) | `failed`, `E_MCP_WRITE_DISABLED`; nothing opened | one over the core, one over stdio |
| A command type outside the first release | `allowed_types` | `rejected`, `E_AUTOMATION_OPERATION_UNSUPPORTED`; Store untouched | one |
| Integrity override through an argument | closed input schema | protocol error | one |
| Two processes writing one Store | the server's call lock covers the server only; a revision directory is created exclusively | **not guaranteed**; a lost race is a failure, never an overwrite; documented | none (stated as a limit) |
| Edit of the Store configuration's `integrity` or the Store itself by an agent with its own file tools | none | out of the threat model; the workspace is the owner's | none (stated as a limit) |

A mutation check (a script that deletes each guard in turn and runs the guard's tests) is part of the implementation PR
that adds the guard and its output is recorded in the PR.

### 3.10 Determinism

`check_command` is a pure function of the workspace and Store bytes and the arguments. `apply_command` is a function of the
same plus the Store state; for the same state it returns the engine's result, and a repeat returns the recorded one. No
timestamp, process id or host path enters a result; host paths are scrubbed as for every tool.

### 3.11 Documents that change, and migration

Additive: the four read-only tools and their schemas are byte-identical; `registry_document()` and `chrona mcp --list-tools`
gain two tools and the version `v0.3`. Statements that become stale and change with the code slices that make them stale:

- Spec 66: status line, "Owns", section 1 ("writes nothing"), section 2 (all tools read-only, "no mutating tool",
  annotations), section 3 (fields only on `ok`), section 4 (workspace rules apply to Store roots), section 6 (new codes
  `E_MCP_WRITE_DISABLED`), section 7 (`--allow-write`, `instructions`, "read-only annotations").
- `docs/guides/agent-interface.md`: "small, read-only MCP server", the table, "The server never writes a file", "no tool that
  changes anything".
- `skills/chrona/SKILL.md` ("The tools never write the plan"; the table, pinned to the registry by
  `test_chrona_skill_mcp_tools.py`) and its card-sized limits (the skill stays at most 200 lines); `README.md` ("a
  read-only MCP server"); the `chrona mcp` help text; the `INSTRUCTIONS` string (under 1 KB, pinned).
- The one-page card `docs/guides/terse-plan.md` does not mention the server, so it does not change; its 120-line pin
  (`tests/unit/chrona/terse/test_card.py`) is unaffected.
- `tests`: the registry-equality tests, the skill-table test (`EQUIVALENT_COMMANDS`), `tests/cli/test_mcp_command.py`
  (`v0.2` literal), `tests/unit/chrona/app/test_agent_tools.py`.

The agent does not write the plan through these tools: the skill still says to edit `project.yaml` with the agent's own
file tools; the new tools change a Store, not a plan.

### 3.12 Successor

[#902](https://github.com/tya5/chrona/issues/902) covers `resolveActualObservation`, `apply_authoring_command`, a revert tool, inline
command objects and a multi-process write lock; each is a `deferred` or `narrowed` row of the acceptance review with that link.
