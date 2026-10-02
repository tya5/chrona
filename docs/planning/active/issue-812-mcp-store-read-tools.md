# Issue #812: MCP Store read tools (`render_review`, `compare_baseline`)

**Status:** Design pack (baseline, design plan, design, architecture review, implementation plan) published in one PR
([#932](https://github.com/tya5/chrona/pull/932)) before any code, as the owner asked for fewer, larger units. Implemented:
S1 [#935](https://github.com/tya5/chrona/pull/935), S2 [#940](https://github.com/tya5/chrona/pull/940); S3 (real-stdio tests
and the [acceptance review](../../reviews/current/issue-812-mcp-store-read-tools-acceptance-review-2026-10-02.md)) in one PR.
**Public base:** `main` at `339d87d4` (observed 2026-10-02); design on `7c207760`.
**Issue:** [#812](https://github.com/tya5/chrona/issues/812), read with its owner comment of 2026-10-01 (teach the
pinned-evidence path in the skill).
**Living contract:** [Spec 66](../../specification/66-agent-interface.md) (changed with the code slices, not here).
**Predecessors:** [#142](https://github.com/tya5/chrona/issues/142) (the tool set), [#813](https://github.com/tya5/chrona/issues/813)
(the Store command tools; its [work record](issue-813-mcp-mutating-tools.md) and
[acceptance review](../../reviews/current/issue-813-mcp-mutating-tools-acceptance-review-2026-10-02.md) are the pattern and
the source of the containment rule). **Successor of #813 for the write side:** [#902](https://github.com/tya5/chrona/issues/902).

## 1. Baseline

### 1.1 Literal acceptance

The issue body: scope "read-only tools over an immutable Render Context / Store (`render_review`, `compare_baseline`),
through an explicit workspace Store config". Acceptance: "a design note first, then a slice; a Store root outside the
workspace is refused; no tool input can lower Store integrity; the tool-set version is bumped." The owner comment adds
"teaching the pinned-evidence path (Immutable Render Context, snapshots, Store config) in the skill", which #142 row 2
narrowed out on purpose (design D1.2b). The task adds requirements that are recorded as rows too (source `task`).

| # | Row | Source |
| ---: | --- | --- |
| 1 | `render_review` exists: a read-only tool over an immutable Render Context in a Store | body |
| 2 | `compare_baseline` exists: a read-only tool over a named baseline and a candidate Project in a Store | body |
| 3 | The Store is reached through an explicit workspace Store configuration | body |
| 4 | "A design note first, then a slice" | body |
| 5 | A Store root outside the workspace is refused | body |
| 6 | No tool input can lower Store integrity (content identity verification on read stays on, #723) | body, task |
| 7 | The tool-set version is bumped | body |
| 8 | The skill teaches the pinned-evidence path (Immutable Render Context, snapshots, Store config) | owner comment |
| 9 | Both tools call the same use cases as `chrona render-review` and `chrona baseline-compare`; results are byte-equal where the command line is deterministic | task |
| 10 | Both tools are read-only (nothing is written, and the annotations say so) | body ("read-only"), task |
| 11 | Path guard on every input; symlink and escape tests | task |
| 12 | Size caps with typed errors (`E_MCP_RESULT_TOO_LARGE`) | task |
| 13 | Mutation check of the new guards | task |
| 14 | Statements made stale are updated: the skill and its table (pinned to the registry), the guide, Spec 66, the `chrona mcp` help, `INSTRUCTIONS`; the card (`docs/guides/terse-plan.md`, at most 120 lines, pinned) | task |

### 1.2 What is published (verified on `main` `339d87d4`)

- The tool core `chrona.app.agent_tools` is `chrona/agent-tools/v0.3` with six tools; `call_tool(scope, name, arguments,
  *, allow_write=False)` returns a `ToolResult`; only `apply_command` is `mutating`. `WorkspaceScope` turns a path
  argument into an existing regular file strictly inside the workspace (syntax, device names, symlinks followed, 2 MiB).
- `operational.store_commands.open_store_reader(config_path, contained_in=)` loads a Store configuration and refuses a
  root that does not resolve strictly inside a directory; the command tools use it with the workspace root
  (`E_MCP_PATH_CONTAINMENT`, `sourceRef` `/storeConfig`). `tools/check_import_direction.py` lets `chrona.app.agent_*`
  import `usecases`, `resources`, `core.store_address` and that one module.
- `chrona render-review` (`cli._run_render_review`) loads the Context reference (`load_yaml`), builds a reader from
  `--store-config` (`cli._render_review_reader`: the reference's `store` must be declared by the configuration, else
  `E_STORE_CONFIG_REQUIRED`; the reader is `LocalSnapshotReader(root, identity, require_content_identity=integrity ==
  "required" and not --allow-missing-content-identity)`), resolves the closure
  (`presentation.model.closure.resolve_render_context`), negotiates the output target, renders through
  `usecases.render_review.render_review` and writes the artifact. All of that, but the render, is inline in the CLI.
- `chrona baseline-compare` (`cli._run`) loads both references, builds one reader with `load_store_config` and calls
  `operational.baselines.compare_baseline(reader, baseline, reader, candidate)`; the result is the Automation Result
  (`operation: baseline-compare`, `comparison` on success) written to `--result`; exit 2 unless `accepted`.
- Integrity (#723): `ConfiguredStoreReader` and `LocalSnapshotReader` verify a reference's `contentIdentity` against the
  stored bytes (`E_CONTENT_IDENTITY`), require one when the Store's `integrity` is `required` (the default;
  `E_CONTENT_IDENTITY_REQUIRED`), and resolve an address strictly inside the Store root with symlinks followed
  (`E_STORE_REFERENCE`). `integrity: optional` is an explicit setting of the Store configuration file; `chrona init
  --example` writes it for the halcyon corpus (ADR-0030).
- The render use case (`usecases.render_review`) may be imported by a tool; `operational` may not import `presentation`
  and `usecases` may not import `operational` (import-direction table), so no single existing layer can both open a
  configured Store and resolve a Render Context (the cycle named in the issue body, #142 review F2).
- The skill (`skills/chrona/SKILL.md`, 175 lines, at most 200 pinned) says "Immutable Render Contexts, snapshots and Store
  configuration are the pinned-evidence path; do not use them unless the user asks for pinned evidence" and has a tool
  table pinned to the registry (`tests/unit/chrona/skills/test_chrona_skill_mcp_tools.py`). `INSTRUCTIONS` and
  `WRITE_INSTRUCTIONS` are 937 and 934 bytes of a 1024 pin. The card `docs/guides/terse-plan.md` is 120 lines (pinned) and
  does not mention the server or the Store.

### 1.3 Inferred and unverified

- Inferred: a Render Context is immutable and fixes its target (`svg`, `png`, `pdf`, `typst`, `tikz`) and viewport, so
  unlike `render_draft` a tool cannot ask for another format; a PNG preview of an SVG Context is not available.
- Inferred: the Store holds fonts and other assets the render reads; a cap on Store reads could break a legitimate render
  (a CJK font is megabytes), so none is added (design 3.8).
- Unverified until the code slices: the exact diagnostics of a malformed Store configuration and of a non-mapping
  reference file through the tool (tested, section 5), the size of a real comparison result, and the new text against the
  `INSTRUCTIONS` pin.
- Not claimed: safety against a Store modified while a call reads it (a read sees either the old or the new bytes, and the
  identity check catches a mismatch).

## 2. Design plan

### 2.1 Use cases

- U1. An agent has a Render Context reference file in the workspace and the Store it points into, and wants the pinned,
  reproducible picture the command line renders (not a draft): `render_review`.
- U2. An agent compares a named baseline with a candidate Project in the Store: `compare_baseline`.
- U3. A reviewer wants to know that the bytes behind a result are the bytes the reference pins: a tampered file or a
  missing identity in a `required` Store is a typed refusal.
- U4. A Store configuration names a root outside the workspace, or a link leaves it: refused before anything is read.
- U5. A read-only deployment (the default, no `--allow-write`) can still read the Store: the tools never need the flag.

### 2.2 Open decisions (resolved in the design, section 3)

| # | Question |
| ---: | --- |
| Q1 | Which tools and which inputs: the CLI's options one to one, or the narrowest set? |
| Q2 | How does a tool receive a reference: a workspace file path, an inline object, or ids? |
| Q3 | How does it find the Store, and may a call name a snapshot root and a store identity directly (the CLI's other mode)? |
| Q4 | What stops an input from lowering integrity, given that a Store configuration may say `integrity: optional`? |
| Q5 | What does `render_review` return, given an immutable Context fixes the target format? |
| Q6 | Which `status` and diagnostics map to a comparison result and to a render rejection? |
| Q7 | Where does the shared code live so that the CLI and the tool core call the same functions under the import rules? |
| Q8 | Which size caps, and is there a cap on Store reads? |
| Q9 | Tool-set version, annotations, and the write flag. |
| Q10 | How is the pinned-evidence path taught, within the 200-line skill and the 120-line card? |

### 2.3 Responsibility boundaries

- The render pipeline and the comparison keep their owners (`usecases.render_review`, `operational.baselines`,
  `usecases.review_projects`). No render, schema, Store format or Automation Result change.
- A new use-case module `usecases.context_review` owns "resolve a Context closure from a reader and render it"; a new
  operational module `operational.store_reads` owns "pick the reader of the Store a reference names, with the
  configured integrity" and "compare a baseline in a configured Store". The command line and the tool core call both.
- The tool core owns argument validation, the workspace path guard, the Store containment check, the envelope, the caps
  and the attachment. The binding adds nothing (the registry already carries annotations).
- No new Store format, schema or Command Request version; Spec 10 is unchanged.

### 2.4 Scope and successors

In scope: the two tools, the shared modules, the CLI refactor onto them, tool set `v0.4`, Spec 66, the skill, the guide,
the help text and `INSTRUCTIONS`. Not in scope, with no acceptance row depending on it: the CLI's `--format`,
`--reject-unused-closure-inputs` and `--emit-scene` options, `render-review-gallery`, `review` (two snapshot files) and
`materialize`. Each is additive in a later tool-set version if wanted; none changes what this issue's rows ask. The write
side and `resolveActualObservation` remain [#902](https://github.com/tya5/chrona/issues/902).

### 2.5 Acceptance evidence

Per row: a unit test of the tool core on a scratch workspace and Store; a stdio test through the real server like
`tests/mcp/test_mcp_stdio_e2e.py`; byte equality with the command line (the SVG artifact and the result file); one test per
threat of the threat model; a mutation check that removes each guard and shows a named test failing; the three-OS run of
the exact commit that publishes the acceptance review, with the MCP tests confirmed on Windows and macOS.

### 2.6 Order of design slices

Baseline, design plan, design, architecture review and implementation plan are in this one record and one PR (the task
asks for them together, published before code).

## 3. Design

Decisions Q1 to Q10 and their reversal are also recorded as a comment on the issue (owner-level judgement calls made by
the implementing agent, with options, choice, reason and how to reverse).

### 3.1 Tool surface (Q1)

| Tool | Command equivalent | Inputs | Writes |
| --- | --- | --- | --- |
| `render_review` | `chrona render-review --store-config` | `contextReference`, `storeConfig?`, `inline?` | no |
| `compare_baseline` | `chrona baseline-compare` | `baselineReference`, `candidateReference`, `storeConfig?` | no |

Both are closed objects. The narrowest useful set: every CLI option that could change what the bytes mean or lower
integrity (`--snapshot-root`, `--store-identity`, `--allow-missing-content-identity`) is absent; the three options that
only assert or add output (`--format`, `--reject-unused-closure-inputs`, `--emit-scene`) are left out of the first release
(2.4). Rejected alternative: mirror every option. It would add a way to name a Store root (3.3) and a switch that lowers
integrity for no use an agent has.

### 3.2 Inputs (Q2, Q3)

- `contextReference`, `baselineReference`, `candidateReference`: a workspace path (the shared guard: relative,
  `/`-separated, inside the workspace, an existing regular file, at most 2 MiB) to a resource-reference YAML, exactly the
  files the command line takes with `--context-reference`, `--baseline-reference` and `--candidate-reference`.
  Rejected alternatives: an inline object (a second input route with its own size rules; inline text belongs with
  [#815](https://github.com/tya5/chrona/issues/815)), and a bare id (the Store has no listing contract).
- `storeConfig`: a workspace path to a Store configuration; omitted is `.chrona/store.yaml` at the workspace root; no
  ancestor search and no working-directory lookup (as `check_command`, #813 design 3.2).
- `render_review` only: `inline` is `none` or `artifact` (default `artifact`).
- No input names a Store root, a snapshot root, a store identity, an output path or an integrity setting.

### 3.3 Containment (rows 5, 11)

Both tools open the configuration through `open_store_reader(config_path, contained_in=workspace_root)` (#813 R10: the
one entry for a workspace Store): every configured root resolves, symlinks followed, strictly inside the resolved
workspace, else the call is `failed` with `E_MCP_PATH_CONTAINMENT`, `sourceRef` `/storeConfig`, before any file is read
from a root. Inside a root, an address is held to the Store root by the reader with symlinks followed (`E_STORE_REFERENCE`),
unchanged. Reading is the only operation, so a failed check leaves nothing to undo. The check and the read are separate
steps, as for every tool (Spec 66 section 4 rule 6).

### 3.4 Integrity (row 6, Q4)

Integrity is the Store configuration's `integrity` for the Store the reference names, applied exactly as the command line
applies it with `--store-config`: `required` (the default) demands a `contentIdentity` on every reference the closure reads
and verifies it against the stored bytes; `optional` is the configuration owner's explicit setting (the halcyon example
corpus). No argument can lower it: the schemas are closed and there is no override; a test passes every spelling of an
override (`allowMissingContentIdentity`, `requireContentIdentity: false`, `integrity`, `snapshotRoot`, `storeIdentity`)
and gets a protocol error. A mismatch between a pinned identity and the stored bytes is `E_CONTENT_IDENTITY` in every mode.
Rejected alternative: have the tool refuse a Store whose configuration says `optional`. It would make the packaged example
corpus unusable through the tool and would not add safety against an agent that can edit the configuration (outside the
threat model, as in #813 3.9). Reversal: one check in the tool's store opener.

### 3.5 Results (Q5, Q6)

- `render_review` result: the envelope plus `format` (the Context's target: `svg`, `png`, `pdf`, `typst`, `tikz`),
  `contentIdentity` (`sha256:` of the artifact bytes the command line writes), `byteLength`, `inlined` and `warnings`
  (the render's warnings, as `render_draft` reports them). With `inline: artifact` an `svg` target travels as an embedded
  SVG resource (`chrona://render/<sha256>.svg`) and a `png` target as an image block; a target that has no inline form
  (`pdf`, `typst`, `tikz`) is not inlined (`inlined: false`) and the identity and length still describe it. A render
  that the use case rejects (an unschedulable Project) is `rejected`; a closure or Store failure is typed through the
  shared failure report, as for `render_draft`.
- `compare_baseline` result: the envelope plus `automationResult`, the Automation Result mapping
  (`chrona/automation-result/v0.2`) exactly as `chrona baseline-compare` writes it to `--result`; serialized with sorted
  keys it is byte-equal to that file. Accepted is `ok` (with `comparison`); rejected is `rejected` with one diagnostic per
  code of the result, component `operational`, `sourceRef` `/` and the engine's own message; `automationResult` is kept
  on a rejected result. (Recorded with S2: an earlier draft gave `E_BASELINE_REFERENCE` the pointer `/baselineReference`,
  but that code covers the baseline, its project and the candidate alike, so the honest source is the whole input.) The command line exits 2 for a rejected result; the
  tool reports `rejected` (understood and refused, Spec 66 section 3).
- Reader failures keep the codes and messages the command line gives them: the render closure reports a generic
  message for `E_STORE_REFERENCE`, `E_CONTENT_IDENTITY` and `E_CONTENT_IDENTITY_REQUIRED` (`usecases.diagnostic_messages`, not changed here); the
  comparison reports the engine's specific message. Better closure messages are a change to that shared table, not to the
  tools.
- A failure that is not a result of the engine (unreadable or oversized file, no or invalid Store configuration, an
  undeclared Store, a root outside the workspace) is `failed` through the shared failure report.

### 3.6 Shared code and import rules (Q7)

Two new modules; the command line moves onto them first (slice S1) with its bytes frozen by the characterization suite:

- `chrona.usecases.context_review`: `resolve_context_closure(reference, reader)` (the Context closure resolution) and
  `render_context_closure(closure, snapshot_root, *, reject_unused_inputs=False)` (builds the `RenderRequest` and calls
  `render_review`). They exist because the tool core may reach `presentation` only through a use case, and the CLI today
  calls `resolve_render_context` and `render_review` directly.
- `chrona.operational.store_reads`: `load_reference(path)` (the CLI's `load_yaml` of a reference file),
  `snapshot_reader_for(config, reference, *, allow_missing_content_identity=False)` (the reference's Store key must be
  declared, else `E_STORE_CONFIG_REQUIRED`; a `LocalSnapshotReader` with the configured integrity; the root) and
  `compare_store_baseline(config, baseline_reference, candidate_reference)`. It cannot be a use case because
  `operational` imports `usecases`; it cannot hold the closure because `operational` may not import `presentation`.

`tools/check_import_direction.py` gains `chrona.operational.store_reads` in the `modules` of `chrona.app.agent_` (one
more named module, with the reason in the commit); every other `operational` import from a tool, and every import from
the binding, still fails. Rejected alternatives: relax the package rule to all of `operational`; add `presentation` to
the tool core; inject the functions from the binding.

### 3.7 Tool-set version, annotations, descriptions (Q9)

`TOOL_SET_VERSION` becomes `chrona/agent-tools/v0.4` (two new tools, no change to an existing tool's schema; #782 D9).
Both tools are `readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false`; neither is
`mutating`, so the write flag never applies and a read-only server serves them. The registry lists them after
`list_presets` so the read-only tools stay together. The descriptions say what the tools are for and what they are not:
pinned evidence from a Store, not a draft; read-only; the Store roots must lie inside the workspace; a PNG preview of an
SVG Context is not offered.

### 3.8 Caps (Q8, row 12)

- Inputs: a reference file and a configuration are at most 2 MiB (the shared guard, `E_MCP_INPUT_TOO_LARGE`).
- Results: an inline SVG over 1 MiB and an inline PNG over 1.5 MiB are `E_MCP_RESULT_TOO_LARGE` (the `render_draft`
  limits, with a message that says to use `inline: none` or the command line, since a Context fixes its own viewport); a
  `compare_baseline` result whose Automation Result serializes to more than 1 MiB is `E_MCP_RESULT_TOO_LARGE` with the same
  advice. The diagnostics list keeps its 50-row cap.
- Store reads have no cap: an asset such as a CJK font is legitimately large, content identity binds the bytes, and the
  command line has none. Stated as a limit in the acceptance review: a YAML document inside the Store that expands
  without bound is as dangerous through the tool as through the command line.

### 3.9 Threat model

The reader is a local process the user started, driven by an agent that may or may not have a shell. Nothing is written,
so the guards protect disclosure and integrity of evidence, not the workspace.

| Threat | Guard | Result | Test |
| --- | --- | --- | --- |
| Path escape in a reference or `storeConfig` (`..`, absolute, backslash, drive, device name) | shared workspace guard | `failed`, `E_MCP_PATH_SYNTAX` | one per input, per shape |
| A reference or the configuration is a symlink out | shared guard, symlinks followed | `failed`, `E_MCP_PATH_CONTAINMENT` | one per input; skipped only where the OS cannot create a link |
| A configured root is absolute, uses `..` or is a symlink out | `open_store_reader(contained_in=)` | `failed`, `E_MCP_PATH_CONTAINMENT`; nothing outside is read | one per shape, with a file outside that would otherwise render |
| An address inside the Store is a link leaving the Store root | `LocalSnapshotReader` | typed `E_STORE_REFERENCE` | one |
| Tampered bytes behind a pinned reference | content identity | refused: `E_CONTENT_IDENTITY` from the render closure; `E_BASELINE_REFERENCE` with the mismatch in the engine's message from the comparison | one per tool |
| A `required` Store and a reference without an identity | integrity | refused: `E_CONTENT_IDENTITY_REQUIRED` from the render closure (as on the command line); `E_BASELINE_REFERENCE`, "has no contentIdentity", from the comparison; the same reference renders under `optional` | one per tool |
| An argument that lowers integrity or names a root | closed input schema | protocol error | one |
| Undeclared Store in the reference | `snapshot_reader_for` | `E_STORE_CONFIG_REQUIRED` | one |
| Write | none exists | the Store's every file and the workspace tree are byte-identical afterwards | one per tool |
| Oversized result | caps (3.8) | `E_MCP_RESULT_TOO_LARGE` | one per cap |
| Host paths in a result | scrubber | no host path | one |
| Edit of the Store configuration's `integrity` or the Store by an agent with its own file tools | none | out of the threat model | none (limit) |

A mutation check (a script that deletes each guard in turn and runs the guard's tests) is part of the implementation PR;
its output is recorded in the PR.

### 3.10 Determinism

A result is a pure function of the workspace and Store bytes, the arguments and the pinned renderer versions. The SVG
bytes equal those of `chrona render-review --output`; PNG bytes depend on the pinned rasterizer. No timestamp, process id
or host path enters a result; host paths are scrubbed as for every tool.

### 3.11 Documents that change (Q10, row 14)

Each statement changes in the code slice that makes it false:

- Spec 66: status line and "Owns" (version), section 1 ("every other tool writes nothing" stays true), section 2 (the
  version history, the table, "no Store-read tool and no `compare_baseline`", the annotations sentence, a new subsection 2.2
  for the two tools), section 3 (fields kept on a rejected result), section 4 (the workspace rules already cover Store
  roots; one clause), section 7 (`instructions`).
- `docs/guides/agent-interface.md`: the table, "there is no tool that reads a Store", a short section on the pinned-evidence
  tools, and the limits.
- `skills/chrona/SKILL.md` (at most 200 lines): two table rows (pinned to the registry through `EQUIVALENT_COMMANDS`) and
  the sentence "do not use them unless the user asks" becomes the teaching of the path: what a Context reference and a Store
  configuration are, when to use the tools (only when the user asks for pinned evidence), what integrity means, and what the
  result carries. No fenced shell command is added that the documented-command check would run without a fixture.
- `chrona mcp` help (and the generated `docs/guides/cli-reference.md`), `README.md` if it lists the tools, and the
  `INSTRUCTIONS` pair (under 1 KB, pinned; the new text is compressed to fit).
- The card `docs/guides/terse-plan.md` (120 lines, pinned by `tests/unit/chrona/terse/test_card.py`) does not mention the
  server, the Store or pinned evidence, so it does not change; the test stays as is.
- Tests that pin the version, the tool order and the table: `test_agent_tools.py`, `test_mcp_command.py`,
  `test_mcp_binding.py`, `test_chrona_skill_mcp_tools.py`.

### 3.12 Revert of this release

Remove the two `ToolSpec` entries and the `modules` entry, and set the version back; the shared modules are used by the CLI
and stay.

## 4. Architecture review

Reviewed against Spec 09 (layers), Spec 42 (Store integrity), Spec 66, the import-direction table, the CLI code of the two
commands, the #142 review (F2) and the #813 review (R2, R3, R10), and the adjacent open work ([#902](https://github.com/tya5/chrona/issues/902),
[#815](https://github.com/tya5/chrona/issues/815), #584 and #822 which touch annotation kinds and the deadline mark and
therefore not these files). Outcome: the design stands; findings S1 to S3 changed it (merged into section 3).

| # | Finding | Disposition |
| ---: | --- | --- |
| S1 | **The cycle in the issue body is real and has two halves.** Opening a configured Store is `operational`; resolving a Render Context is `presentation`; `operational` may not import `presentation` and `usecases` may not import `operational`. #813's single facade is not enough. | Two modules, one per half (3.6): the closure and render in `usecases.context_review`, the Store side in `operational.store_reads`; the tool core reaches both (one new named module edge). |
| S2 | **The CLI has two reader modes; only one is safe to expose.** `--snapshot-root` plus `--store-identity` names a Store root outside any configuration, and `--allow-missing-content-identity` lowers integrity. | Only the configuration mode exists in the tools (3.1, 3.4); the CLI keeps both. A test shows the tool schema has none of the spellings. |
| S3 | **`integrity: optional` is a legitimate configuration, so "cannot be lowered" must mean "by a tool input".** Refusing `optional` would break the packaged example corpus. | 3.4: the configuration's setting applies as on the command line; the acceptance review states it as a disclosure and a test shows a `required` Store refusing the example's unpinned references. |
| S4 | **One engine, two front ends.** The inline CLI code is the temptation to copy. | S1 moves the CLI onto the shared functions with its bytes frozen by the characterization suite (`tests/fixtures/cli_characterization`), then the tool core is added on top. |
| S5 | **Immutable Context target.** A Context fixes its format and viewport; copying `render_draft`'s `format` and PNG preview would be a lie. | 3.5: the tool reports the target and inlines only an SVG or a PNG target. |
| S6 | **No new Store resource.** The tools only read. | One test per tool shows the Store and the workspace tree byte-identical afterwards and no sibling file created. |
| S7 | **Information in results.** A Store diagnostic can carry an address or a configured path. | Host-path scrubbing runs over every message and the whole `automationResult`; a test puts the workspace path in a reference id and sees it scrubbed. |
| S8 | **Skill budget.** 175 of 200 lines; the card is at its pin of 120. | The skill gains a short section and two rows; the card is untouched; the tests that pin both stay as they are. |
| S9 | **Adjacent work.** #902 adds the write side of the same Store entry; #815 may add inline text. | `open_store_reader(contained_in=)` stays the one entry; the schemas are closed objects that can gain an inline sibling in a later version; no code is added to `failure_report.py` or `diagnostic_messages.py`. |

Conclusion: no layer breach remains after S1 and S2. Residual risks: a Store changed during a read (caught by the
identity check) and an unbounded YAML inside a Store (3.8), both disclosed in the acceptance review.

## 5. Implementation plan

Slices land as separate PRs, merged one at a time through the merge lock, each with `Refs #812` only. Gates for every
code slice: focused tests, `python conformance/run_conformance.py`, `python tools/check_import_direction.py`,
`python tools/check_documented_commands.py` where the grammar or the guides change, and the CI matrix. Derived evidence
(`docs/diagnostics/inventory.md`, generated output) is never edited by hand.

| Slice | Owner files | Change | Focused tests | Publication boundary |
| --- | --- | --- | --- | --- |
| S1 | `src/chrona/usecases/context_review.py` (new), `src/chrona/operational/store_reads.py` (new), `src/chrona/app/cli.py`, `tools/check_import_direction.py` | Move the store-config reader selection, the Context closure resolution, the render call and the baseline comparison of the two commands behind the shared functions; the CLI calls them. Add `chrona.operational.store_reads` to the tool core's `modules`. No behavior change. | `tests/unit/chrona/operational/test_store_reads.py` (declared and undeclared Store, integrity required and optional, comparison equals `compare_baseline`), `tests/unit/chrona/usecases/test_context_review.py`, the import rule accepts the new module and still rejects `operational.baselines` from a tool; the CLI characterization suite and `tests/cli` unchanged. | Behavior-preserving: CLI bytes identical. |
| S2 | `src/chrona/app/agent_tools.py`, `src/chrona/app/cli.py` (help), Spec 66, `skills/chrona/SKILL.md`, `docs/guides/agent-interface.md`, `README.md` if it lists tools, `mcp_server.py` (`INSTRUCTIONS`), generated CLI reference | The two tools, `v0.4`, `_open_contained_store` shared with the command tools, caps, the attachment, every document that was made stale. | `tests/unit/chrona/app/test_agent_store_reads.py`: one test per row of the threat model, byte equality with `chrona render-review` and `baseline-compare`, read-only proof, closed inputs, caps, annotations; `tests/mcp/test_mcp_binding.py` (the tools without the write flag, annotations equal the registry, instructions); `test_agent_tools.py`, `test_mcp_command.py`, the skill table test. Mutation check: a script deletes or weakens each guard (containment, both path guards, undeclared-Store check, integrity requirement, the result caps, the annotations, the shared functions' use by the CLI); each must fail a named test; output pasted in the PR. | Reads only; the default of `--allow-write` is unchanged. |
| S3 | `tests/mcp/test_mcp_stdio_e2e.py`, `docs/reviews/current/issue-812-mcp-store-read-tools-acceptance-review-2026-10-02.md` | The real server over stdio: both tools on a real Store with the write flag off, byte equality with the command line, escapes, a symlink, an outside root, tampered bytes. Then the literal acceptance review from a fresh read of the issue body and every comment. Merged in one PR (the owner asks for fewer, larger units). | The new stdio tests; `tools/check_issue_acceptance_reviews.py`. | Then the exact-main three-OS run on the review commit decides closing. |

Notes:

- Fixtures: the packaged example corpus (`initialize_project(..., example="halcyon-1")`) is the Store for `render_review`
  (it renders in seconds, and its `optional` integrity has a `required` twin by editing the configuration); a small Store
  built with `tests/support/store_workspace.py` is the Store for `compare_baseline` (capture a baseline with
  `apply_command`, write a changed Project as the candidate).
- Windows: link tests skip only when the OS refuses to create a symlink, as the existing tests do; path-escape tests use
  only strings and run everywhere.
- No `CHANGELOG.md` entry (the file records no MCP change so far).
- Acceptance map (rows of 1.1): 1, 2, 3, 9, 10 by S2 tests and S3; 4 by this record's publication before code; 5, 6, 11, 12
  by the threat-model tests; 7 by the registry test; 8 by the skill text and its pins; 13 by the PR evidence; 14 by the
  document changes of S2 and the unchanged card test.
