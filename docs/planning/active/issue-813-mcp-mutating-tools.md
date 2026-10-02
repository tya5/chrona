# Issue #813: MCP mutating tools (`check_command`, `apply_command`)

**Status:** Design plan (this revision). The design, architecture review and implementation plan are added to this
record by the next three documentation PRs, before any code.
**Public base:** `main` at `e4429030` (observed 2026-10-02).
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
moved to one successor issue (opened with the design PR): `resolveActualObservation`, `apply_authoring_command`
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

1. This PR: baseline and design plan.
2. Design (section 3, with the successor issue and the decision record on the issue).
3. Architecture review (section 4).
4. Implementation plan (section 5).
