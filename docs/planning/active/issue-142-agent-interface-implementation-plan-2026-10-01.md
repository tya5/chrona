# Implementation Plan: Agent Interface, a Skill and an MCP Surface (#142)

**Status:** Proposed. Valid only for the design as reviewed; slices marked **needs lead** wait for the decisions in the [architecture review](../../reviews/current/issue-142-agent-interface-architecture-review-2026-10-01.md) (L1 to L5).
**Design:** [issue-142-agent-interface-design-2026-10-01.md](../../design/issue-142-agent-interface-design-2026-10-01.md). **Plan:** [issue-142-agent-interface-design-plan-2026-10-01.md](issue-142-agent-interface-design-plan-2026-10-01.md).
**Base:** `main` at `1185e229`. PR #424 (README) is open; S1 and S2 rebase on it.

## Rules for every slice

- One PR per slice, `Refs #142` only, no closing keyword in a title, body or commit.
  The issue is closed only by an acceptance review with a row per literal criterion
  (`docs/reviews/current/`), citing the three-OS run on the publishing commit.
- `tools/check_import_direction.py` stays green in every slice; a new module is
  placed in the package its imports allow, and the slice names which package.
- A PR does not edit derived documents (`docs/diagnostics/inventory.md`,
  `declared-value-inventory.md`, `vocabulary-inventory.md`, `gallery/presentation-coverage.md`,
  `examples/*/generated/*`); new `E_MCP_*` codes appear there through the derived sync.
- `python conformance/run_conformance.py` is run before a slice is accepted; code
  slices also run the focused tests named below. Do not duplicate the full pytest run
  locally.
- Update this plan in place when a slice finds a design problem; pause the slice and
  amend the design and review first (AGENTS.md, required sequence).

## Order and dependencies

```text
S0a --> S0b --> S3 --> S4 --> S5
S1  --> S2 ------------------> S5
                         S4 --> S6 (needs lead: L3, L4)     S7 (later)
```

S1 and S0a/S0b are independent and can run in parallel. The order confirms the
issue's (skill, then MCP) with one revision: S0 is a prerequisite refactor that the
issue did not anticipate (review F1, F2).

## S0a: shared use cases for validate, schedule and failure reporting

**Purpose.** Give validate, schedule and the exception-to-diagnostics ladder an
importable home so the CLI and any adapter share one implementation.

**Files.**
- New `src/chrona/usecases/project_checks.py`: `validate_project_file(path)` and
  `schedule_project_file(path)` returning typed outcomes (`diagnostics`, `placements`,
  `analysis`); they load through `core.validation.load_yaml`, call
  `core.validation.validate_project` and `scheduling.scheduler.schedule`, and keep
  `_schedule_payload`'s ordering. Package: `usecases` (allowed to import `core`,
  `scheduling`).
- New `src/chrona/usecases/failure_report.py`: `report_failure(exception)` returning
  `(status, diagnostics, exit_code)`, containing the body of `main()`'s `except`
  ladder and `CliFailure`, `_diagnostic` and the presentation-rejection shaping, moved
  without change of codes, messages, component names or key order.
- Edit `src/chrona/app/cli.py`: `main()` and the validate/schedule branches call the
  use cases and print exactly what they printed before.

**Tests (written first, green before and after).**
`tests/cli/test_cli_characterization.py`: through `main()` with a fixed
argument vector and a scratch directory, capture stdout, stderr and exit code for
about fifteen scenarios (valid project; each of the D1.2c codes: `E_SCHEMA`,
`E_REFERENCE`, `E_UNSUPPORTED_CYCLE` from `schedule`, `[]` from `validate` on a cycle;
`E_INPUT_IO`, `E_INPUT_YAML`, `E_COMMAND_SYNTAX`, `E_BUILTIN_PRESET_UNKNOWN`,
`E_RENDER_OUTPUT_EXTENSION`) and compare with golden text stored under
`tests/fixtures/cli_characterization/`. New unit tests for the two modules (typed
outcomes, ordering, no I/O beyond the named path). `tests/unit/chrona/usecases/`.

**Proof.** Characterization suite identical before and after; existing CLI tests
unchanged; `check_import_direction.py` green (no new edge); `check_module_reachability.py`
green; `conformance` green; no diff in any `examples/*/generated/*`.

**Must not.** Change a diagnostic code, message, key order, exit code or flag; add a
dependency; move anything out of `operational/`; make `validate` detect cycles; print
from a use case.

## S0b: the draft-render use case

**Purpose.** Lift the draft-render pipeline out of `app/cli.py`.

**Files.**
- New `src/chrona/usecases/draft_render.py`: a frozen `DraftRenderRequest`
  (project, actual, preset, view, theme, scheme, layout, viewport, locale, target kind,
  visual profile, typesetter identity, flags the CLI has today) and
  `render_draft(request) -> DraftRenderResult` (artifact bytes, media type, warning
  and info records, content identity). It owns the builtin-preset temporary copy
  (`_resolve_preset_argument`), the version-error rewrite for a stale copied preset,
  `resolve_draft_render`, and `usecases.render_review.render_review`. Failures are
  raised as the existing typed exceptions, translated by `failure_report`.
- Edit `src/chrona/app/cli.py`: `_run_draft_render` builds the request, calls the use
  case, writes the output file, emits warnings to stderr, and `--emit-scene` stays
  CLI-side.

**Tests.** Extend the characterization suite with draft-render scenarios (default
preset SVG and PNG bytes; `--preset editorial`; `--viewport`; a rejected project;
a stale preset copy; the rasterizer-unavailable case through a monkeypatched import);
unit tests on `render_draft` with a synthetic Project and no CLI.

**Proof.** SVG and PNG output **byte-identical** to the pre-slice CLI for every
scenario; `python tools/regenerate_public_examples.py --check --jobs 4` reports no
change; the import-direction check is green; a micro-benchmark shows no regression
beyond noise on the 24-object plan (about 4.8 s measured on the design date).

**Must not.** Change layout, Scene or renderer code; add a flag; read the host
clock or environment; make `usecases` import `app`.

## S1: the skill, with proof that it cannot rot

**Files.**
- New `skills/chrona/SKILL.md` (at most 200 lines), `skills/chrona/references/authoring-model.md`,
  `references/diagnostics.md`, `references/mermaid-or-chrona.md`, `skills/chrona/examples/launch.yaml`
  (a real plan: a gate, two scheduled tasks across a calendar exception, a deadline).
  Content as D1.2; the Mermaid comparison as D1.4; the diagnostics table as D1.2c.
- New `skills/__init__.py` (empty, not packaged).
- Edit `tools/check_documented_commands.py`: `documents()` also yields `skills/chrona/SKILL.md`
  and `skills/chrona/references/*.md`; the `execute()` fixture copies `skills/` beside
  `examples/`.
- New `tests/unit/chrona/skills/test_chrona_skill.py` (front matter, size, links, YAML fence
  equals the example file, preset ids equal `chrona preset list`),
  `test_chrona_skill_diagnostics.py` (every `E_/W_/I_` token is constructed in `src/chrona`;
  each reachable code is provoked through `chrona.app.cli.main`; an allowlist with a reason
  for the rest), and an addition to `tests/unit/tools/test_documented_commands.py` for the
  new document set.
- Edit `docs/guides/first-project.md` with one link to the skill (no command change).

**Proof.** `python tools/check_documented_commands.py --check --execute` runs the
skill's commands in the fixture and exits 0 (`rc=$?` checked directly); the new unit
tests pass; the example validates, schedules and renders; a deliberately broken command
in a scratch copy of the skill makes the check fail (recorded in the PR as a mutation
check); the skill's diagnostics table contains no code the inventory lacks. A short
manual scenario set (a four-task plan with a holiday, an accidental cycle, a preset
change) is run once with an agent and attached to the PR as evidence, non-gating.

**Must not.** Mention `chrona mcp`, any MCP tool or `chrona skill` (they do not exist
yet); describe or use any #148 syntax or `chrona compile`; restate a specification rule
instead of linking it; tell the agent to use `--system-fonts`, the immutable Context
path or `--allow-missing-content-identity`; add a wheel file or a CLI command.

## S2: delivery of the skill (**needs lead: L2**)

**Files.**
- Edit `pyproject.toml`: `force-include` `"skills/chrona" = "chrona/resources/skills/chrona"`.
- Edit `src/chrona/resources/__init__.py`: `skill_resource()` (packaged first, else the
  source tree), following `schema_resource`.
- New `src/chrona/usecases/skill_library.py`: `copy_skill(destination)` modelled on
  `preset_library.copy_builtin_preset` (empty or absent destination only; uses
  `core.store_address` for every member path).
- Edit `src/chrona/app/cli.py`: `chrona skill copy --output DIR`.
- Edit `docs/guides/` (a new `agent-interface.md`): the command, a refresh instruction,
  and a statement of what the skill is for; `docs/guides/cli-reference.md` regenerated by
  the tool; `tools/wheel_smoke.py` asserts the packaged skill exists and equals the
  source tree.
- Tests: `tests/unit/chrona/usecases/test_skill_library.py` (non-empty destination
  refused, traversal refused, output equals source tree byte for byte);
  `tests/integration/test_wheel_skill.py` (editable and wheel resolution);
  `tests/unit/tools/test_check_wheel_size.py` expectation unchanged.

**Proof.** `chrona skill copy --output <tmp>/skill` in a clean wheel install equals
`skills/chrona/`; the documented-surface gate passes with the guide; `check_wheel_size`
passes (budget 5 MB); `conformance` green.

**Must not.** Add a symlink; add a second copy of the skill under `src/`; overwrite an
existing directory; add network access; add a plugin manifest (separate, optional,
needs verification against the host's current rules).

## S3: the SDK-free tool core and its contract

**Files.**
- New `src/chrona/app/agent_workspace.py`: `WorkspaceScope` (resolve once; refuse a
  filesystem root; `resolve_path(value)` through `resolve_store_address(..., charset="file-name")`
  plus the reserved-device-name and `is_file()` checks; size cap; path scrubber).
- New `src/chrona/app/agent_tools.py`: `ToolSpec` registry for `validate_project`,
  `schedule_project`, `render_draft`, `list_presets` (schemas of D2.3, envelope,
  `status` mapping, dedupe, cap, scrub, fixed `E_TOOL_FAILURE` message).
  Handlers import `usecases` and `core` contract types only.
- Edit `src/chrona/app/cli.py`: `chrona mcp --list-tools` (prints the registry as JSON,
  needs no SDK; `chrona mcp` itself lands in S4). `--workspace` is accepted and
  validated here.
- Edit `tools/check_import_direction.py`: a module-prefix override table so
  `chrona.app.agent_*` and `chrona.app.mcp_server` may import only `usecases` and the
  named `core` modules; with its own unit test in `tests/unit/tools/`.
- New `docs/specification/66-agent-interface.md`: the normative tool and result
  contract, the workspace rules, determinism, and the versioned tool set
  `chrona/agent-tools/v0.1`. Linked from `docs/specification/README.md`.
- Tests under `tests/unit/chrona/app/`: path scoping (traversal, absolute, backslash,
  drive, colon, control character, reserved device name, symlink out of the workspace,
  directory, FIFO, oversize file, non-ASCII name accepted); schema validation of every
  result against the registry schemas with `jsonschema`; envelope for each scenario of
  the characterization suite; **determinism** (same call twice; from two working
  directories; no timestamp or host path in any result, scanned for the workspace
  path and the home directory); **cross-surface equality** (`render_draft` SVG bytes
  equal the CLI's file bytes; `schedule_project` equals `chrona schedule` JSON);
  no write to `sys.stdout`; no tool accepts an integrity override.

**Proof.** Tests above; import-direction green with the new override table
(fails when a handler imports `presentation`, demonstrated by a test); `chrona mcp
--list-tools` is documented in `docs/guides/agent-interface.md` and executed by
doc-check; `conformance` green.

**Must not.** Import the `mcp` package; write a file; read the Store or any path not
named by an input; add `--system-fonts`, `--font-metrics`, `--icon-catalog`, a Typst or
TikZ target, or any integrity opt-out; change a CLI result byte; add anything under
`schemas/` (the contract lives in Spec 66 plus the registry in this slice).

## S4: the SDK binding and the stdio server (**needs lead: L1**)

**Files.**
- Edit `pyproject.toml`: `[project.optional-dependencies] mcp = ["mcp>=2.2,<3"]` (value
  per L1).
- New `src/chrona/app/mcp_server.py`: registers each `ToolSpec` with the SDK, sets
  `isError` only for `failed`, builds content blocks (JSON text, optional PNG image,
  optional SVG embedded resource), serializes calls with a lock, logs to stderr only,
  provides `initialize` instructions and the two resources read from the packaged skill
  (the resources need S2; until then they are omitted and the instructions point to
  the guide), runs stdio.
- Edit `src/chrona/app/cli.py`: `chrona mcp` runs the server; missing SDK gives
  `E_MCP_UNAVAILABLE`, exit 2, with the install hint.
- CI: a dedicated lane `pip install -e '.[dev,render,mcp]' -e packages/chrona-fonts-noto-cjk`
  running `tests/mcp/`; the three-OS full matrix installs the extra and runs the same
  tests (catches the Windows `pywin32` path); PR shards stay without the extra.
- Tests in `tests/mcp/` (module-level `pytest.importorskip("mcp")`): a subprocess stdio
  session (`initialize`, `tools/list` equals the registry, each tool call); protocol
  errors for an unknown tool and bad arguments come from the SDK; `isError` mapping;
  image and SVG content blocks; stdout contains only protocol frames; an SDK
  floor-and-latest check; the cross-surface equality test repeated through the real
  transport.
- Docs: `docs/guides/agent-interface.md` gains host configuration snippets
  (`chrona mcp` and `python -m chrona mcp`, with `--workspace`), PNG needs
  `chrona[mcp,render]`, the limits (no cancellation, inline caps).

**Proof.** The lane is green on Ubuntu, macOS and Windows; `chrona mcp --list-tools`
works with the SDK uninstalled (checked in a clean venv in CI); a default
`pip install chrona` has no `mcp` module; import-direction green; `conformance` green;
a manual run against one real host recorded in the PR (a transcript: validate a plan,
fix a cycle, render, view the image).

**Must not.** Import the SDK anywhere but `mcp_server.py`; add an HTTP transport,
a listener, authentication or a background task; add a write path; widen any default
beyond the design; vendor or fork the SDK; change a tool schema without bumping the
tool-set version.

## S5: make skill and server say the same thing

**Files.** Edit `skills/chrona/SKILL.md` to add "if the chrona MCP server is
connected, prefer its tools; otherwise use the CLI" with a table mapping each tool to
its command (a test pins the table to the registry and to `chrona --help` surface);
`mcp_server.py` serves the resources from the packaged skill; README gains one short
pointer. Tests: the mapping table equals the registry; every tool name in the skill
exists; the doc-check run still passes.

**Proof.** The mapping test, doc-check and `conformance`.

**Must not.** Fork the skill text per surface; put the model or diagnostics table in a
second place.

## S6: store-based and mutating tools (**needs lead: L3, L4**)

Conditional on approval. Candidate tools: `render_review` (immutable Context via an
explicit `<workspace>/.chrona/store.yaml`), `compare_baseline`, `workspace_revision`,
`check_command`, `apply_command` and `apply_authoring_command` (write-gated, bound by
`confirm`), `init_project`. Prerequisites: the import-direction decision (explicit
override or relocation), the Store `root` containment rule and refusal code, `--allow-write`
with exclusive creation (`storage.publication.publish_exclusive`), tool annotations, and
a design correction recorded in the design and review before code (the Store and write
paths are new public behavior). Proof will include: a root outside the workspace is
refused; a stale `baseRevision` is rejected; a replayed command is idempotent; no tool
input can lower Store integrity; the write flag off gives `E_MCP_WRITE_DISABLED`.

**Must not.** Emulate `ai-command-proposal` or `authorization-decision`; write
without `--allow-write`; overwrite a file; read a Store outside the workspace.

## S7: later

Inline Project text for clients with no workspace (a private temporary directory,
builtin presets only); a one-pass SVG-plus-raster use case; optional plugin manifest
for the repository (after verifying the host's current manifest rules); `--font-metrics`
and `--icon-catalog` inputs through the guard; a `chrona compile` tool once #148 lands;
`sourceRange` in diagnostics once source positions exist. Each needs its own short design
note appended to this record.

## Acceptance map (for the later acceptance review)

| Issue #142 literal item | Expected disposition | Slice |
| --- | --- | --- |
| `chrona` Agent Skill with the authoring model, worked example, diagnostic codes, "do not hand-write SVG, do not use Mermaid when scheduling matters" | met after S1, S2 | S1, S2 |
| MCP server, one tool per use case | narrowed: `validate_project`, `schedule_project`, `render_draft`, `list_presets` | S3, S4 |
| `render_review` returning SVG and PNG | narrowed: `render_draft` returns PNG preview and SVG on request; immutable `render_review` deferred | S3, S4, S6 |
| `compare_baseline`, `apply_command` | deferred (review F2, F3) | S6 |
| Position against the default | met after S1 | S1 |
| Order #120, skill, MCP | met, with S0 inserted | S0, S1, S4 |

## Publication boundaries

S0a, S0b, S1, S3 and S4 each publish separately; S2 publishes after S1; S5 after S2 and
S4. Each slice's PR carries its focused-test output and, for code slices, the
conformance result. Archive this record and the review only after the acceptance review
and exact-main CI, per AGENTS.md.

## Progress

| Slice | State | Note |
| --- | --- | --- |
| S0 (S0a and S0b together) | Implemented in two PRs: the characterization suite (#783), then the extraction | See the deviations below. |
| S3 (tool core) | Implemented as the MCP slice 1 of 3: `agent_workspace.py`, `agent_tools.py`, the module rules in `check_import_direction.py`, Spec 66 | See the S3 deviations below. |
| S4 (binding) | Implemented as the MCP slice 2 of 3: `mcp_server.py`, `chrona mcp`, the `mcp` extra, the guide section, binding tests in `tests/mcp/`; then the real-stdio end-to-end test `tests/mcp/test_mcp_stdio_e2e.py` | See the S4 verification below. Both test modules skip with a reason without the extra, so they run only where it is installed: the CI install is a workflow-only PR (`conformance.yml`), published separately. |
| S5 (skill and server agree) | Implemented: a skill section and table for the four tools, one README pointer, `tests/unit/chrona/skills/test_chrona_skill_mcp_tools.py` pinning the table to the registry and to the CLI surface | The resources were served from the packaged skill already in S4, so S5 adds only the table and the test. |

S0 deviations from the plan text (no change of behavior; the CLI bytes are frozen by
`tests/cli/test_cli_characterization.py`, 110 invocations against
`tests/fixtures/cli_characterization/golden.json`):

- S0a and S0b landed as one slice, because the draft-render use case needs the failure
  report (`StableFailure`) and both must keep the order of failures the CLI had.
- `project_checks` exposes `validate_project_mapping` and `schedule_project_mapping` next to
  the `*_file` functions: the CLI also validates and schedules an immutable snapshot, which
  yields a mapping, not a path. The outcome types are `ProjectValidation` and `ProjectSchedule`
  (`payload()` keeps `_schedule_payload`'s key order).
- `report_failure(exception)` returns a frozen `FailureReport(status, diagnostics, exit_code)`
  with `payload()`; `rejection_report(diagnostics, component)` shapes Core diagnostics. It also
  maps `RenderRejected` and `RenderFailed`, which the CLI translated at each call site. The
  CLI's `CliFailure` is now `usecases.failure_report.StableFailure` (`CliFailure` stays an alias).
- `DraftRenderRequest` carries the viewport as the `WIDTHxHEIGHT` string and the typesetter as
  three strings, and `parse_viewport` and `typesetter_identity` run inside `render_draft` after
  the preset is resolved: this keeps the order in which several simultaneous input errors were
  reported. Output-suffix negotiation (`--format` against `-o`) and file writing stay in the CLI.
  `DraftRenderResult` wraps the `RenderedReview` (artifact bytes, media type, scene, warnings);
  `warning_payloads` returns the warning and info records the CLI prints to stderr. No separate
  content identity is added in S0.
- Not changed, tracked in #780 and #782: near-duplicate render rows, `E_BUILTIN_PRESET_UNKNOWN`
  without a message of its own, `validate` returning `[]` for a cycle. Observed and not yet
  tracked: the key order of `analysis.totalFloat` in `chrona schedule` output follows set
  iteration (hash-seed dependent), so two runs can differ; an MCP adapter must not pin it.

S3 deviations from the plan text (lead decisions L1 to L5 apply: read-only, stdio, four tools, SDK optional):

- The normative document is Spec 66 (`docs/specification/66-agent-interface.md`): number 65 went to the terse plan
  syntax (#148). The `chrona mcp --list-tools` flag, its guide text and its documented-command line move from S3 to S4
  with `chrona mcp` itself, so S3 touches neither `cli.py` nor the guides. Until S4 imports them, the two new modules are
  listed in `tools/staged_modules.txt`.
- `tools/check_import_direction.py` gets a module-prefix table (`MODULE_RULES`): `chrona.app.agent_*` and
  `chrona.app.mcp_server` may import `usecases`, `core.store_address`, `resources` (for `validator_for_schema`, the one
  validator factory a guard test requires) and one another only. It also enforces the SDK
  rule (`only chrona.app.mcp_server may import the mcp SDK`), so S4 needs no further change to the tool.
- A tool result mapping is sorted by key (`placements`, `totalFloat`, a warning's `detail`), not in Project object order as
  design D2.3c said: `totalFloat` is hash-seed dependent in the use case (#789) and the tool must not pin it. Sorting
  `placements` too keeps one rule; `criticalObjectIds` keeps the Project object order (a list).
- `E_RENDER_RASTERIZER_UNAVAILABLE` is `failed` in the tool (D2.3d) although `chrona render` exits 1 for it. A missing
  workspace file is `E_INPUT_IO` (the code the command uses), not a new `E_MCP_*` code. A render warning has no message
  today, so the tool reports `message: ""` and keeps the ledger fields in `detail`.
- Not offered, as designed: `--system-fonts`, `--font-metrics`, `--icon-catalog`, `--visual-profile`, typesetter targets,
  `pdf`, `--emit-scene`. The viewport pattern is the design's (3 to 5 digits per side); a very large PNG viewport is a
  local memory cost the first release does not cap.

S4 verification of the SDK (lead decision L1: verify before pinning). Checked on 2026-10-01 in throwaway virtual
environments, never in the shared one: PyPI has `mcp` 2.0.0, 2.0.1, 2.1.0, 2.1.1 and 2.2.0 (plus 2.0 pre-releases and the
1.x line). The design's description of the 2.x API is right (`FastMCP` is renamed `MCPServer`, and `mcp.server.fastmcp`
now raises on import), but the design did not name what the binding needs, which is:

- `mcp.server.Server(name, version=, instructions=, on_list_tools=, on_call_tool=, on_list_resources=,
  on_read_resource=)`, the low-level server with constructor-registered handlers. It is used instead of `MCPServer`
  because the tool core already owns the JSON input and output schemas (`MCPServer` derives a schema from a function
  signature) and the lowlevel server does not validate arguments, so the core's argument check is the only one.
- `mcp.server.stdio.stdio_server()` (while serving it points file descriptor 1 at standard error, so stray output
  cannot corrupt a frame), `mcp.types` (the mirror of `mcp_types`), `mcp.shared.exceptions.MCPError` for protocol errors.
- On the client side, `mcp.Client` (in process) and `mcp.client.stdio.stdio_client` with `mcp.ClientSession` (a
  subprocess). `Client(StdioServerParameters(...))` raises a `TypeError` on 2.0.0 and works on 2.1.1 and 2.2.0, so the
  end-to-end test uses `stdio_client` and `ClientSession`, which work on every 2.x release checked.
- Result of the check: the binding tests and a real stdio session (initialize, tools/list, a schedule call, a PNG
  render, the resource list, an unknown tool) pass on 2.0.0, 2.0.1, 2.1.0, 2.1.1 and 2.2.0. The extra is therefore
  `mcp>=2.0,<3`, not the design's `mcp>=2.2,<3`: no 2.2-only API is used, and a floor that was tested is better than a
  floor that was only named. The transitive set for 2.2.0 is pydantic, starlette, uvicorn, sse-starlette,
  `httpx2`, PyJWT with `cryptography`, `opentelemetry-api`, `python-multipart`, `jsonschema` and `mcp-types`
  (the design named `httpx`; 2.2 depends on `httpx2`), plus `pywin32` on Windows.
- Not verified here: a real agent host session (the plan's transcript requirement), and Windows (CI decides on the
  three-OS run).

Other S4 deviations: the two guide resources are served now (S2 is merged), so S5 only adds the skill's tool table;
`E_MCP_UNAVAILABLE` is `failed`, exit 2, from `chrona mcp` only; a missing packaged skill omits the resources and logs a
warning instead of failing the server.
